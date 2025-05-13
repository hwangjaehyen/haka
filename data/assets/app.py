from flask import Flask
from dash import Dash, dcc, html, Input, Output, State, dash_table
from collections import Counter
import pandas as pd
import plotly.graph_objs as go
import base64
import html as html_utils
import os
import plotly.express as px

# --- 폰트 경로 설정 (Pretendard 폰트 경로를 CSS로 직접 삽입) ---
font_path = "C:/Users/user/AppData/Local/Microsoft/Windows/Fonts/Pretendard-Regular.otf"

# --- 데이터 로딩 및 전처리 ---
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

rank_df = pd.read_excel(r"C:/Users/user/workspace/keyword/data/250512_250109-250512_전자담배_순위.xlsx")
rank_df['날짜'] = pd.to_datetime(rank_df['날짜'], format="%Y%m%d")
rank_df['날짜_str'] = rank_df['날짜'].dt.strftime('%Y-%m-%d')
for col in ['가격', '리뷰수', '최근6개월내구매수', '찜수']:
    if col in rank_df.columns:
        rank_df[col] = rank_df[col].apply(parse_number)

rank_df['최근 6개월 내 구매 수'] = rank_df['최근6개월내구매수'].fillna(0)
rank_df['상품명'] = rank_df['제품명_new']

product_df = pd.read_excel(r"C:/Users/user/workspace/keyword/data/250428_제품군_정리.xlsx")
product_df = product_df.dropna(subset=['출시일', '카테고리', '제품명', '가격'])
product_df['출시일'] = pd.to_datetime(product_df['출시일'], errors='coerce')

search_df = pd.read_csv(r"C:/Users/user/workspace/keyword/data/160101-250331_네이버_통합_검색량.csv")
search_df['날짜'] = pd.to_datetime(search_df['날짜'], errors='coerce').dt.normalize()
search_df.dropna(subset=['카테고리1', '카테고리2', '키워드'], inplace=True)

news_df = pd.read_csv(r"C:/Users/user/workspace/keyword/data/160101-250331_news.csv")
news_df['일자'] = pd.to_datetime(news_df['일자'], errors='coerce').dt.normalize()
news_df = news_df.dropna(subset=['일자', '제목'])
news_df = news_df[news_df['제목'].str.contains('담배', na=False)]

news_grouped = news_df.groupby('일자')['제목'].apply(lambda x: list(x.head(3))).reset_index()
news_grouped.rename(columns={'일자': '날짜', '제목': '뉴스리스트'}, inplace=True)

month_range = pd.date_range(
    search_df['날짜'].min().replace(day=1),
    search_df['날짜'].max().replace(day=1),
    freq='MS'
)
month_options = [{'label': d.strftime('%Y-%m'), 'value': d.strftime('%Y-%m')} for d in month_range]

server = Flask(__name__)
app = Dash(__name__, server=server, suppress_callback_exceptions=True)
app.title = "키워드 대시보드"

cat1_options = sorted(search_df['카테고리1'].unique())

# --- 이미지 인코딩 ---
def encode_image(image_file):
    with open(image_file, 'rb') as f:
        encoded = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{encoded}"

image_path = r"C:/Users/user/workspace/keyword/data/haka.png"
encoded_image = encode_image(image_path)

# --- 스타일 정의 ---
app.index_string = f"""
<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        {{%favicon%}}
        {{%css%}}
        <style>
        @font-face {{
            font-family: 'Pretendard';
            src: url('file:///{font_path.replace(os.sep, "/")}') format('opentype');
        }}
        body {{
            font-family: 'Pretendard', sans-serif;
        }}
        </style>
    </head>
    <body>
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>
"""

# --- 탭 스타일 ---
tab_style = {
    'padding': '15px 40px', 'fontSize': '16px', 'fontWeight': 'bold', 'backgroundColor': 'white',
    'color': '#444', 'border': 'none'
}
selected_tab_style = {
    'padding': '15px 40px', 'fontSize': '16px', 'color': '#00ACA3', 'fontWeight': 'bold', 'border': 'none',
    'borderBottom': '2px solid #00ACA3'
}

# --- 앱 레이아웃 ---
app.layout = html.Div([
    html.Div([
        html.Img(src=encoded_image, style={'height': '40px', 'marginRight': '12px'}),
        html.Div([
            dcc.Tabs(id='tabs', value='news', children=[
                dcc.Tab(label='제품별 순위', value='ranking', style=tab_style, selected_style=selected_tab_style),
                dcc.Tab(label='전자담배 매장 지도', value='map', style=tab_style, selected_style=selected_tab_style),
                dcc.Tab(label='뉴스 검색량', value='news', style=tab_style, selected_style=selected_tab_style),
            ], style={'width': '100%'})
        ], style={'flexGrow': 1})
    ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'start', 'marginBottom': '10px'}),

    html.Div(id='tab-content')
])

@app.callback(Output('tab-content', 'children'), Input('tabs', 'value'))
def render_tab(tab):
    if tab == 'news':
        return html.Div([
            dcc.Tabs(id='cat1-tabs', value=cat1_options[0], children=[
                dcc.Tab(label=c1, value=c1, style=tab_style, selected_style=selected_tab_style)
                for c1 in cat1_options
            ]),
            html.Div(id='cat2-tabs-container'),

            html.Div([
                html.Div([
                    html.Label("시작월", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(id='month-start', options=month_options, value=month_options[0]['value'],
                                 clearable=False, style={'width': '100%'})
                ], style={'display': 'inline-block', 'width': '45%', 'paddingRight': '10px'}),
                html.Div([
                    html.Label("종료월", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(id='month-end', options=month_options, value=month_options[-1]['value'],
                                 clearable=False, style={'width': '100%'})
                ], style={'display': 'inline-block', 'width': '45%'})
            ], style={'textAlign': 'center', 'marginBottom': '20px'}),

            html.Div([
                html.Label("키워드 선택", style={'fontWeight': 'bold', 'fontSize': '16px'}),
                dcc.Dropdown(id='keyword-dropdown', options=[], value=None, clearable=False,
                             style={'width': '40%', 'margin': '0 auto', 'textAlign': 'center'})
            ], style={'textAlign': 'center', 'marginBottom': '20px'}),
            html.Div([
                html.Label("카테고리별 출시일 표시", style={'fontWeight': 'bold', 'fontSize': '16px'})
            ], style={'textAlign': 'center', 'marginBottom': '10px'}),

            dcc.Dropdown(
                id='product-category-dropdown',
                options=[{'label': c, 'value': c} for c in sorted(product_df['카테고리'].dropna().unique())],
                value=None,
                clearable=True,
                style={'width': '40%', 'margin': '0 auto', 'textAlign': 'center'}
            ),
            html.Div([
                html.Div([
                    dcc.Graph(id='search-volume-graph', config={'displayModeBar': False}, style={'height': '600px'})
                ], style={'width': '100%', 'display': 'inline-block'}),
                
                html.Div(id='correlation-output', style={'width': '100%', 'marginTop': '20px'})
            ])

        ])
    
    elif tab == 'map':
        return html.Div([
            html.Iframe(src='/assets/map.html', style={'width': '100%', 'height': '85vh', 'border': 'none'})
        ])
    
    elif tab == 'ranking':
        cat_options = rank_df['카테고리'].dropna().unique()
        cat_dropdown = dcc.Dropdown(
            id='ranking-category-dropdown',
            options=[{'label': '전체', 'value': '전체'}] + [{'label': c, 'value': c} for c in cat_options],
            value='전체',
            clearable=False,
            style={'width': '300px'}
        )

        return html.Div([
            html.H3("네이버 상위 40위 제품 기준", style={'textAlign': 'center'}),
            html.H4("제품별 순위 변화 및 최근 6개월 내 판매량", style={'textAlign': 'center'}),
            html.Div(cat_dropdown, style={'width': '300px', 'margin': '0 auto 20px auto'}),

            dcc.Loading(dcc.Graph(id='ranking-bubble-graph', config={'displayModeBar': False})),

            html.Hr(),
            html.H4("제품명 키워드 빈도", style={'textAlign': 'center'}),
            dcc.Loading(dcc.Graph(id='ranking-word-graph', config={'displayModeBar': False})),

            html.Hr(),
            html.H4("제품 종류별 빈도", style={'textAlign': 'center'}),
            dcc.Loading(dcc.Graph(id='ranking-category-graph', config={'displayModeBar': False}))
        ])


@app.callback(
    Output('ranking-bubble-graph', 'figure'),
    Input('ranking-category-dropdown', 'value')
)
def update_ranking_bubble(selected_category):
    df = rank_df if selected_category == '전체' else rank_df[rank_df['카테고리'] == selected_category]
    fig = px.scatter(
        df,
        x='최근 6개월 내 구매 수',
        y='순위',
        size='최근 6개월 내 구매 수',
        color='상품명',
        text='상품명',
        animation_frame='날짜_str',
        height=600
    )
    fig.update_yaxes(autorange='reversed')
    fig.update_layout(xaxis_title='최근 6개월 내 구매 수', yaxis_title='순위', xaxis_tickformat='%Y-%m-%d')
    return fig

@app.callback(
    Output('ranking-word-graph', 'figure'),
    Input('tabs', 'value')  # 탭 진입시 렌더링
)
def update_word_graph(tab):
    if tab != 'ranking': return go.Figure()
    word_freq_data = []
    for date, group in rank_df.groupby('날짜'):
        words = " ".join(group['제품명']).split()
        top_words = Counter(words).most_common(10)
        for word, count in top_words:
            word_freq_data.append({'날짜': date, '단어': word, '빈도수': count})
    word_df = pd.DataFrame(word_freq_data)
    fig = px.line(word_df, x='날짜', y='빈도수', color='단어', markers=True, height=600)
    fig.update_layout(xaxis_title='날짜', yaxis_title='빈도수', xaxis_tickformat='%Y-%m-%d')
    return fig

@app.callback(
    Output('ranking-category-graph', 'figure'),
    Input('tabs', 'value')
)
def update_category_graph(tab):
    if tab != 'ranking': return go.Figure()
    cat_df = rank_df.groupby(['날짜', '카테고리']).size().reset_index(name='빈도수')
    fig = px.line(cat_df, x='날짜', y='빈도수', color='카테고리', markers=True, height=600)
    fig.update_layout(xaxis_title='날짜', yaxis_title='빈도수', xaxis_tickformat='%Y-%m-%d')
    return fig

@app.callback(
    Output('cat2-tabs-container', 'children'),
    Input('cat1-tabs', 'value')
)
def update_cat2_tabs(cat1):
    cat2s = sorted(search_df[search_df['카테고리1'] == cat1]['카테고리2'].dropna().unique())
    return dcc.Tabs(id='cat2-tabs', value=cat2s[0], children=[
        dcc.Tab(label=c2, value=c2, style=tab_style, selected_style=selected_tab_style) for c2 in cat2s
    ])

@app.callback(
    Output('keyword-dropdown', 'options'),
    Output('keyword-dropdown', 'value'),
    Input('cat1-tabs', 'value'),
    Input('cat2-tabs', 'value')
)
def update_keyword_dropdown(cat1, cat2):
    keywords = sorted(search_df[(search_df['카테고리1'] == cat1) & (search_df['카테고리2'] == cat2)]['키워드'].unique())
    options = [{'label': k, 'value': k} for k in keywords]
    return options, (keywords[0] if keywords else None)

@app.callback(
    Output('search-volume-graph', 'figure'),
    Output('correlation-output', 'children'),
    Input('cat1-tabs', 'value'),
    Input('cat2-tabs', 'value'),
    Input('month-start', 'value'),
    Input('month-end', 'value'),
    Input('keyword-dropdown', 'value'),
    Input('product-category-dropdown', 'value')  

)
def update_graph(cat1, cat2, month_start, month_end, keyword, product_cat):
    if not keyword:
        return go.Figure(), html.Div()

    keyword_escaped = html_utils.escape(keyword)
    if '<' in keyword and '>' in keyword:
        title_label = f"<span style='color:#00ACA3'>&lt;{keyword.split('<')[1].split('>')[0]}&gt;</span>"
    else:
        title_label = keyword_escaped

    start_month = pd.to_datetime(month_start)
    end_month = pd.to_datetime(month_end) + pd.offsets.MonthEnd(0)

    df = search_df[(search_df['날짜'] >= start_month) & (search_df['날짜'] <= end_month)]
    df = pd.merge(df, news_grouped, on='날짜', how='left')
    df['뉴스리스트'] = df['뉴스리스트'].apply(lambda x: x if isinstance(x, list) else [])
    df['뉴스요약'] = df['뉴스리스트'].apply(lambda lst: "<br>".join(lst[:3]) if lst else "뉴스 없음")

    df_kw = df[df['키워드'] == keyword].copy()
    df_kw['hovertext'] = df_kw.apply(
        lambda row: f"{row['날짜'].strftime('%Y-%m-%d')}<br>📊 검색량: {int(row['총 검색량']):,}회<br>📰 뉴스:<br>{row['뉴스요약']}",
        axis=1
    )

    if df_kw.empty:
        return go.Figure(), html.Div()

    pivot = df.pivot(index='날짜', columns='키워드', values='총 검색량').fillna(0)
    correlations = pivot.corrwith(pivot[keyword]).drop(labels=[keyword]).sort_values(ascending=False).head(5)

    corr_table = html.Table([
        html.Thead(html.Tr([html.Th("키워드"), html.Th("상관계수")])),
        *[html.Tr([
            html.Td(k, style={'border': '1px solid black'}),
            html.Td(f"{v:.2f}", style={'border': '1px solid black'})
        ]) for k, v in correlations.items()]
    ], style={'margin': 'auto', 'border': '1px solid black', 'borderCollapse': 'collapse', 'textAlign': 'center'})

    top10 = df_kw.sort_values(by='총 검색량', ascending=False).head(10)
    avg = df_kw['총 검색량'].mean()

    fig = go.Figure()

    # 검색량 라인
    fig.add_trace(go.Scatter(
        x=df_kw['날짜'], y=df_kw['총 검색량'], mode='lines+markers',
        name='검색량', hovertext=df_kw['hovertext'], hoverinfo='text',
        marker=dict(color='#00ACA3', line=dict(width=1, color='#00ACA3'))
    ))

    # 상위 10일 마커
    fig.add_trace(go.Scatter(
        x=top10['날짜'], y=top10['총 검색량'], mode='markers+text',
        name='상위 10일', text=top10['날짜'].dt.strftime('%Y-%m-%d'),
        textposition='top center', marker=dict(color='red', size=10, symbol='diamond'),
        hoverinfo='skip'
    ))

    # 출시일 기준 제품 정보 추가
    related_products = product_df[product_df['카테고리'] == product_cat].dropna(subset=['출시일'])
    # 검색량 범위에 맞게 출시일 필터링
    related_products = related_products[(related_products['출시일'] >= df_kw['날짜'].min()) &(related_products['출시일'] <= df_kw['날짜'].max())]
    if not related_products.empty:
        release_x = []
        release_y = []
        release_text = []
        release_hover = []

        for _, row in related_products.iterrows():
            release_date = row['출시일']
            # 가장 가까운 날짜의 검색량 가져오기
            nearest_idx = (df_kw['날짜'] - release_date).abs().idxmin()
            nearest_y = df_kw.loc[nearest_idx, '총 검색량']

            release_x.append(release_date)
            release_y.append(nearest_y)
            release_text.append(row['제품명'])
            release_hover.append(f"{row['제품명']}<br>{int(row['가격']):,}원")

        fig.add_trace(go.Scatter(
            x=release_x,
            y=release_y,
            mode='markers+text',
            name='출시 제품',
            text=release_text,
            textposition='bottom center',
            hovertext=release_hover,
            hoverinfo='text',
            marker=dict(color='orange', size=12, symbol='star')
        ))

    return fig, html.Div([
        html.H4("상관계수 Top 5 키워드", style={'textAlign': 'center'}),
        corr_table
    ])

# 실행
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=False)
