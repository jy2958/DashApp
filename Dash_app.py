import pandas as pd
import numpy as np
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import plotly.express as px
import datetime
from tools import calculate_performance,calculate_and_export_cumulative_return_probabilities
# Load Inputs1: trading log with preds and value_position
# Load Inputs2: execution log
# Load Inputs3: index for benchmark
# Load Inputs4: index components stock codes and names

df_inputs=pd.read_csv('df_log_periods_w_latest.csv')
df_transactions=pd.read_csv('df_transactions_latest.csv')
df_price_800=pd.read_csv('df_price_800_latest.csv',index_col=0)
df_index_components_uni=pd.read_csv('df_index_components_uni_latest.csv')
df_inputs['date']=pd.to_datetime(df_inputs['date'])
df_transactions['date']=pd.to_datetime(df_transactions['date'])
df_price_800.index=pd.to_datetime(df_price_800.index)

# Data Prep
sum_value = df_inputs.groupby('date').sum()
sum_value2 = pd.merge(sum_value, df_price_800, left_index=True, right_index=True)
sum_value2['price_zz800_adj'] = sum_value2['price_zz800_adj'] / sum_value2['price_zz800_adj'].tolist()[0]
sum_value2['price_zz800_adj'] = sum_value2['price_zz800_adj'] * 10000
sum_value2 = sum_value2.rename(columns={'value_position': 'Portfolio',
                                        'price_zz800_adj': 'Index'})
sum_value2.index.name = 'Date'
daily_portfolio_value = sum_value2[['Portfolio', 'Index']].reset_index()


# Dash Url: http://127.0.0.1:8050/
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("指数增强策略-表现分析", style={'textAlign': 'center'}),
    html.Div([
        dcc.DatePickerRange(
            id='date-picker-range',
            start_date=datetime.datetime(2020, 1, 1),
            end_date=datetime.datetime(2024, 4, 10),
            display_format='YYYY-MM-DD',
            start_date_placeholder_text='开始日期',
            end_date_placeholder_text='结束日期'
        ),
        html.Div([
            html.Label('无风险利率:'),
            dcc.Input(id='risk-free-rate-input', type='number', value=0.02, step=0.001, style={'margin-left': '10px'})
        ], style={'margin-top': '20px'}),
    ], style={'margin': '20px', 'textAlign': 'center'}),

    # 定义Tabs
    dcc.Tabs(id="tabs-styled-with-inline", value='tab-1', children=[
        dcc.Tab(label='净值', value='tab-1'),
        dcc.Tab(label='基础指标', value='tab-2'),
        #dcc.Tab(label='超额表现', value='tab-3'),
        dcc.Tab(label='净胜率', value='tab-4'),
        dcc.Tab(label='持仓股票P&L', value='tab-5'),  # 新的选项卡
        dcc.Tab(label='持仓板块P&L', value='tab-6'),  # 新的选项卡
    ], style={'width': '100%', 'font-size': '20px'}),

    html.Div(id='tabs-content-inline')
])

@app.callback(
    Output('tabs-content-inline', 'children'),
    [Input('tabs-styled-with-inline', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('risk-free-rate-input', 'value')]
)
def render_content(tab, start_date, end_date, risk_free_rate):
    df_filtered = daily_portfolio_value[(daily_portfolio_value['Date'] >= start_date) & (daily_portfolio_value['Date'] <= end_date)]
    df_filtered2 = df_filtered.copy()
    perf = calculate_performance(df_filtered2, risk_free_rate)
    df_filtered2 = df_filtered.copy()
    perf2 = calculate_and_export_cumulative_return_probabilities(df_filtered2)
    df_filtered3 = df_filtered.copy()
    df_filtered3['Portfolio_CumReturns'] = df_filtered3['Portfolio'] / df_filtered3['Portfolio'].tolist()[0]
    df_filtered3['Index_CumReturns'] = df_filtered3['Index'] / df_filtered3['Index'].tolist()[0]
    df_filtered3['Excess_CumReturns'] = df_filtered3['Portfolio_CumReturns'] - df_filtered3['Index_CumReturns']

    df_base_performance = pd.DataFrame(perf[:2], index=['Portfolio', 'ZZ800']).reset_index().round(2)
    df_excess_performance = pd.DataFrame(perf[2], index=['Excess']).reset_index().round(2)
    df_win_rates = perf2.round(2)

    df_transactions_filtered=df_transactions[(df_transactions['Side'] != 'Hold')
                                            &(df_transactions['date'] >= start_date) 
                                             &(df_transactions['date'] <= end_date)].copy()
    
    date_trans_first=df_transactions_filtered['date'].min().strftime('%Y-%m-%d')
    df_transactions_filtered=df_transactions_filtered[~((df_transactions_filtered['date']==date_trans_first)
                        &(df_transactions_filtered['Side']=='Sell'))]
    date_trans_last=df_transactions_filtered['date'].max().strftime('%Y-%m-%d')
    df_transactions_filtered=df_transactions_filtered[~((df_transactions_filtered['date']==date_trans_last)
                            &(df_transactions_filtered['Side']=='Buy'))]
    
#     # 按照股票代码进行分组
#     grouped = df_transactions_filtered.groupby('code')
#     # 对每个分组应用筛选函数
#     df_transactions_filtered = grouped.apply(filter_transactions)

    df_transactions_filtered = df_transactions_filtered.reset_index(drop=True)
    df_pnl_filtered = df_transactions_filtered.groupby('code')['PNL'].sum().reset_index()
    df_transactions_filtered_execute=df_transactions_filtered.groupby('code')['Buy','Sell'].sum().reset_index()
    df_pnl_filtered = df_pnl_filtered.sort_values(by='PNL', ascending=False).reset_index(drop=1).reset_index()  # 按照 PNL 从大到小排序
    df_pnl_filtered = pd.merge(df_pnl_filtered,
                               df_index_components_uni,
                             on=['code'],how='left')
    df_pnl_filtered = pd.merge(df_pnl_filtered,
                               df_transactions_filtered_execute,
                             on=['code'],how='left')
    
    df_pnl_filtered['PNL'] = [round(i,0) for i in df_pnl_filtered['PNL']]
    
    df_pnl_filtered_sector=df_pnl_filtered.groupby('sector').sum()[['PNL']].reset_index()
    
    # 板块PNL
    df_pnl_filtered_sector2=df_pnl_filtered_sector.copy()
    df_sum1=pd.DataFrame(df_pnl_filtered_sector.sum()).T
    df_sum1.sector='总计'
    df_pnl_filtered_sector2=pd.concat([df_pnl_filtered_sector,df_sum1])
    df_pnl_filtered_sector2['PNL%']=(df_pnl_filtered_sector2['PNL']/df_sum1['PNL'][0])*100
    df_pnl_filtered_sector2['PNL%']=[round(i,2) for i in df_pnl_filtered_sector2['PNL%']]
    df_pnl_filtered_sector2
    
    # 板块 capital & count(累计买入资金和交易次数)
    df_transactions_filtered2=pd.merge(df_transactions_filtered,
                                   df_index_components_uni,
                                 on=['code'],how='left')
    df_capital_sector=df_transactions_filtered2.groupby(['sector','Side']).sum()[['Buy','Sell','value_position']].reset_index()
    df_capital_sector['Buy']=df_capital_sector['Buy']+df_capital_sector['Sell']
    del df_capital_sector['Sell']
    df_capital_sector.columns=['Sector','Action','Count','Capital']
    df_capital_sector['CapPerAction']=df_capital_sector['Capital']/df_capital_sector['Count']
    df_capital_sector['Cap%']=(df_capital_sector['Capital']/df_capital_sector['Capital'].sum())*100
    df_capital_sector['Cap%']=[round(i,1) for i in df_capital_sector['Cap%']]
    if tab == 'tab-1':
        return dcc.Graph(
            figure={
                'data': [
                    go.Scatter(x=df_filtered3['Date'], y=df_filtered3['Portfolio_CumReturns'], mode='lines',
                               name='Portfolio'),
                    go.Scatter(x=df_filtered3['Date'], y=df_filtered3['Index_CumReturns'], mode='lines', name='Index'),
                    go.Scatter(x=df_filtered3['Date'], y=df_filtered3['Excess_CumReturns'], mode='lines', name='Excess')
                ],
                'layout': go.Layout(title='策略/指数/超额 收益率', xaxis={'title': 'Date'},
                                    yaxis={'title': '净值收益率'})
            }
        )
    elif tab == 'tab-2':
        table1=dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in df_base_performance.columns],
            data=df_base_performance.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data={'whiteSpace': 'normal', 'height': 'auto'})
        
        table2=dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in df_excess_performance.columns],
            data=df_excess_performance.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data={'whiteSpace': 'normal', 'height': 'auto'})
        
        return html.Div([html.H2("策略和指数表现"),table1,
                        html.H2("超额表现"),table2])
            
    elif tab == 'tab-4':
        return dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in df_win_rates.columns],
            data=df_win_rates.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data={'whiteSpace': 'normal', 'height': 'auto'}
        )
    
    elif tab == 'tab-5':
        return dash_table.DataTable(  # 新的 DataTable 显示持仓股票 PNL
            id='table-pnl',
            columns=[{"name": i, "id": i} for i in df_pnl_filtered.columns],
            data=df_pnl_filtered.to_dict('records'),
            sort_action='native',  # 可以点击表头进行排序
            style_table={'overflowX': 'auto'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data={'whiteSpace': 'normal', 'height': 'auto'}
        )
    
    elif tab == 'tab-6':
        #板块累计盈亏图
        bar_fig = px.bar(df_pnl_filtered_sector.sort_values('PNL',ascending=0), x='sector', y='PNL', labels={'PNL': 'PNL'}, title='板块盈亏分析')
        bar_fig.update_xaxes(title='板块')
        bar_fig.update_yaxes(title='元')
     
        # 板块累计盈亏表格
        table1 = dash_table.DataTable(
            id='table-pnl2',
            columns=[{"name": i, "id": i} for i in df_pnl_filtered_sector2.columns],
            data=df_pnl_filtered_sector2.to_dict('records'),
            sort_action='native',
            style_table={'overflowX': 'auto'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data={'whiteSpace': 'normal', 'height': 'auto'}
        )
        #'板块累计交易资金和次数',
        table2 = dash_table.DataTable(
            id='table-pnl3',
            columns=[{"name": i, "id": i} for i in df_capital_sector.columns],
            data=df_capital_sector.to_dict('records'),       
            filter_action="native",
            sort_action='native',
            sort_mode="multi",
            style_table={'overflowX': 'auto'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data={'whiteSpace': 'normal', 'height': 'auto'} 
        )
        
        #板块累计交易资金(仅买入)占比',
        df_capital_sector_buy=df_capital_sector[df_capital_sector['Action']=='Buy']
        pie_chart = dcc.Graph(
            id='pie-chart',
            figure={
                'data': [
                    go.Pie(labels=df_capital_sector_buy['Sector'], values=df_capital_sector_buy['Cap%'])
                ],
                'layout': go.Layout(title='板块累计交易资金(仅买入)占比')
            }
        )

        return html.Div([html.H2("板块累计盈亏-图"),
                         dcc.Graph(figure=bar_fig), 
                         html.H2("板块累计盈亏-表"),
                         table1,
                         html.H2("板块累计交易资金和次数"),
                         table2,
                        pie_chart])

if __name__ == '__main__':
    #app.run_server(debug=True)
    app.run_server(debug=False, port=8080)

server = app.server
