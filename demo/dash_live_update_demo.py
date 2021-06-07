# First version of liveplot
# -------------------------
# 1) New values of plots are not appended but the whole plot is generated.
#    This is not efficient!
# 2) Implement sliding window.

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from rateman import read_stats_txs_csv

#TODO: Wrap multiple plots into a plot with subplots.
#TODO: Fix Rate Index Axis order.

ap_list_csv = 'sample_ap_lists/ap_list_sample_1.csv'
csv_file = "collected_data/data_AP2.csv"
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


ap_list_df = pd.read_csv(ap_list_csv)
fig = go.Figure()

options = []
for index, row in ap_list_df.iterrows():
    options.append(
        {
            'label': '{} - {}'.format(row['APID'], row['IPADD']),
            'value': row['APID']
        }
    )

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(children=[
    html.H1(children='Example Plots'),
    
    html.Div(id='output-state'),

    dcc.Graph(id='graph', figure=fig),
    dcc.Interval(
            id='interval-component',
            interval=1*1000, # in milliseconds
            n_intervals=0
    ),
    # dcc.Store inside the app that stores the intermediate value
    dcc.Store(id='traces-to-plot'),

    dcc.Dropdown(
        options=options,
        value=[],
        multi=True,
        id='traces-dropdown',
    )  
])

@app.callback(Output('traces-to-plot', 'data'),
              Input('traces-dropdown', 'value'))
def update_traces_to_plot(value):
    return value # ist nicht notwendig

@app.callback(Output('graph', 'figure'),
              Input('interval-component', 'n_intervals'),
              Input('traces-dropdown', 'value'))
def liveplot(n, dd_val, t_interval=20):
    if not dd_val:
        return go.Figure()
    dfs, df2s = [], []
    for apid in dd_val:
        d1, d2 = read_stats_txs_csv("collected_data/data_{}.csv".format(apid), shifttime=True)
        dfs.append(d1)
        df2s.append(d2)
    
    # Collect some data
    end_list = []
    start_list = []
    for df, df2 in zip(dfs, df2s):
        end_list.extend([df.index[-1], df2.index[-1]])
        start_list.extend([df.index[0], df2.index[0]])

    t_end = np.amax(end_list)
    t_start = np.amin(start_list)
    t_help = t_end - t_interval
    if t_start < t_help:
        t_start = t_help

    fig = make_subplots(
        rows= 2, cols=1, subplot_titles=('Rate Index vs Time',
        'Average Throughput vs Time'), shared_xaxes=True,
    )
    for df, df2 in zip(dfs, df2s):
        fig.add_trace(
            go.Scatter(x=df[df.index > t_start].index, y=df[df.index > t_start].rates),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df2[df2.index > t_start].index, y=df2[df2.index > t_start].avg_tp), 
            row=2, col=1
        )

    # Edit the layout
    # fig.update_layout(title='Rate Index at Time',
    #                 xaxis_title='Time in s',
    #                 yaxis_title='Rate Index')
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
