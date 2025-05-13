# 이 코드는 Dash + Flask 기반 앱을 Streamlit으로 변환한 버전입니다.
# 기능은 그대로 유지하며 Streamlit 문법에 맞게 재작성되었습니다.

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from collections import Counter
import base64
import html as html_utils
from datetime import datetime

# --- Pretendard 폰트는 웹에서 로딩하거나 Streamlit에서는 시스템 폰트로 대체 ---
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif;
    }
    </style>
""", unsafe_allow_html=True)

# --- 데이터 로딩 ---
def parse_number(x):
    x = str(x).strip().replace(',', '')
    if '만' in x:
        try:
            return int(float(x.replace('만', '')) * 10000)
        except:
            return None
    try:
        return int(x)
    except:
        return None

@st.cache_data

def load_data():
    rank_df = pd.read_excel("data/250512_250109-250512_전자담배_순위.xlsx")
    rank_df['날짜'] = pd.to_datetime(rank_df['날짜'], format="%Y%m%d")
    rank_df['날짜_str'] = rank_df['날짜'].dt.strftime('%Y-%m-%d')
    for col in ['가격', '리뷰수', '최근6개월내구매수', '찜수']:
        if col in rank_df.columns:
            rank_df[col] = rank_df[col].apply(parse_number)
    rank_df['최근 6개월 내 구매 수'] = rank_df['최근6개월내구매수'].fillna(0)
    rank_df['상품명'] = rank_df['제품명_new']

    product_df = pd.read_excel("data/250428_제품군_정리.xlsx")
    product_df = product_df.dropna(subset=['출시일', '카테고리', '제품명', '가격'])
    product_df['출시일'] = pd.to_datetime(product_df['출시일'], errors='coerce')

    search_df = pd.read_csv("data/160101-250331_네이버_통합_검색량.csv")
    search_df['날짜'] = pd.to_datetime(search_df['날짜'], errors='coerce').dt.normalize()
    search_df.dropna(subset=['카테고리1', '카테고리2', '키워드'], inplace=True)

    news_df = pd.read_csv("data/160101-250331_news.csv")
    news_df['일자'] = pd.to_datetime(news_df['일자'], errors='coerce').dt.normalize()
    news_df = news_df.dropna(subset=['일자', '제목'])
    news_df = news_df[news_df['제목'].str.contains('담배', na=False)]

    news_grouped = news_df.groupby('일자')['제목'].apply(lambda x: list(x.head(3))).reset_index()
    news_grouped.rename(columns={'일자': '날짜', '제목': '뉴스리스트'}, inplace=True)

    return rank_df, product_df, search_df, news_grouped

rank_df, product_df, search_df, news_grouped = load_data()

# --- UI 시작 ---
st.title("키워드 대시보드")

탭 = st.tabs(["제품별 순위", "전자담배 매장 지도", "뉴스 검색량"])

# --- 탭: 제품별 순위 ---
with 탭[0]:
    cat_option = st.selectbox("카테고리 선택", options=['전체'] + sorted(rank_df['카테고리'].dropna().unique()))
    if cat_option != '전체':
        filtered = rank_df[rank_df['카테고리'] == cat_option]
    else:
        filtered = rank_df

    fig = px.scatter(
        filtered,
        x='최근 6개월 내 구매 수',
        y='순위',
        size='최근 6개월 내 구매 수',
        color='상품명',
        text='상품명',
        animation_frame='날짜_str',
        height=600
    )
    fig.update_yaxes(autorange='reversed')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("제품명 키워드 빈도")
    word_freq_data = []
    for date, group in rank_df.groupby('날짜'):
        words = " ".join(group['제품명']).split()
        top_words = Counter(words).most_common(10)
        for word, count in top_words:
            word_freq_data.append({'날짜': date, '단어': word, '빈도수': count})
    word_df = pd.DataFrame(word_freq_data)
    fig2 = px.line(word_df, x='날짜', y='빈도수', color='단어', markers=True, height=600)
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("제품 종류별 빈도")
    cat_df = rank_df.groupby(['날짜', '카테고리']).size().reset_index(name='빈도수')
    fig3 = px.line(cat_df, x='날짜', y='빈도수', color='카테고리', markers=True, height=600)
    st.plotly_chart(fig3, use_container_width=True)

# --- 탭: 전자담배 매장 지도 ---
with 탭[1]:
    st.components.v1.html(open("data/assets/map.html", encoding='utf-8').read(), height=700)

# --- 탭: 뉴스 검색량 ---
with 탭[2]:
    cat1 = st.selectbox("카테고리1", sorted(search_df['카테고리1'].unique()))
    cat2_list = sorted(search_df[search_df['카테고리1'] == cat1]['카테고리2'].dropna().unique())
    cat2 = st.selectbox("카테고리2", cat2_list)

    keywords = sorted(search_df[(search_df['카테고리1'] == cat1) & (search_df['카테고리2'] == cat2)]['키워드'].unique())
    keyword = st.selectbox("키워드 선택", keywords)

    months = pd.date_range(search_df['날짜'].min(), search_df['날짜'].max(), freq='MS')
    month_start = st.selectbox("시작 월", [d.strftime('%Y-%m') for d in months])
    month_end = st.selectbox("종료 월", [d.strftime('%Y-%m') for d in months[::-1]])

    product_cat = st.selectbox("제품 카테고리", sorted(product_df['카테고리'].dropna().unique()))

    # --- 데이터 처리 및 그래프 ---
    start_month = pd.to_datetime(month_start)
    end_month = pd.to_datetime(month_end) + pd.offsets.MonthEnd(0)

    df = search_df[(search_df['날짜'] >= start_month) & (search_df['날짜'] <= end_month)]
    df = pd.merge(df, news_grouped, on='날짜', how='left')
    df['뉴스리스트'] = df['뉴스리스트'].apply(lambda x: x if isinstance(x, list) else [])
    df['뉴스요약'] = df['뉴스리스트'].apply(lambda lst: "<br>".join(lst[:3]) if lst else "뉴스 없음")

    df_kw = df[df['키워드'] == keyword].copy()
    df_kw['hovertext'] = df_kw.apply(
        lambda row: f"{row['날짜'].strftime('%Y-%m-%d')}<br>📊 검색량: {int(row['총 검색량']):,}회<br>📰 뉴스:<br>{row['뉴스요약']}", axis=1
    )

    pivot = df.pivot(index='날짜', columns='키워드', values='총 검색량').fillna(0)
    correlations = pivot.corrwith(pivot[keyword]).drop(labels=[keyword]).sort_values(ascending=False).head(5)

    top10 = df_kw.sort_values(by='총 검색량', ascending=False).head(10)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_kw['날짜'], y=df_kw['총 검색량'], mode='lines+markers',
                             name='검색량', hovertext=df_kw['hovertext'], hoverinfo='text'))
    fig.add_trace(go.Scatter(x=top10['날짜'], y=top10['총 검색량'], mode='markers+text',
                             name='상위 10일', text=top10['날짜'].dt.strftime('%Y-%m-%d'),
                             textposition='top center', marker=dict(color='red', size=10)))

    # 출시일 마커
    related_products = product_df[product_df['카테고리'] == product_cat]
    related_products = related_products[(related_products['출시일'] >= df_kw['날짜'].min()) & (related_products['출시일'] <= df_kw['날짜'].max())]
    if not related_products.empty:
        for _, row in related_products.iterrows():
            nearest_y = df_kw.loc[(df_kw['날짜'] - row['출시일']).abs().idxmin(), '총 검색량']
            fig.add_trace(go.Scatter(
                x=[row['출시일']], y=[nearest_y], mode='markers+text',
                name='출시 제품', text=[row['제품명']], textposition='bottom center',
                marker=dict(color='orange', size=12, symbol='star')
            ))

    st.plotly_chart(fig, use_container_width=True)

    # 상관계수 출력
    st.subheader("상관계수 Top 5 키워드")
    st.table(pd.DataFrame({"키워드": correlations.index, "상관계수": correlations.values.round(2)}))
