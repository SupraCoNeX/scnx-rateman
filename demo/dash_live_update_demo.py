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
import pandas as pd
import numpy as np

from ratemanager import read_stats_txs_csv

#TODO: Wrap multiple plots into a plot with subplots.
#TODO: Fix Rate Index Axis order.

csv_file = "../demo/collected_data/data_AP2.csv"
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

try:
    df, df2 = read_stats_txs_csv(csv_file, shifttime=True)
except pd.errors.EmptyDataError:
    output_text = 'Dataframe is empty. Please load another csv file.'
    fig = go.Figure()
    fig2 = go.Figure()
else:
    output_text = 'Data was successfully loaded.'
    fig = go.Figure(go.Scatter(x=df.index, y=df.rates))

    # Edit the layout
    fig.update_layout(title='Rate Index at Time',
                    xaxis_title='Time in s',
                    yaxis_title='Rate Index')

    fig2 = go.Figure(go.Scatter(x=df2.index, y=df2.avg_tp))

    # Edit the layout
    fig2.update_layout(title='Average Throughput at Time',
                    xaxis_title='Time in s',
                    yaxis_title='Average throughput in bit/s')

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(children=[
    html.H1(children='Example Plots'),
    
    html.Div(id='output-state'),

    dcc.Graph(id='rate-graph', figure=fig),

    dcc.Graph(id='throughput-graph', figure=fig2),
    dcc.Interval(
            id='interval-component',
            interval=1*1000, # in milliseconds
            n_intervals=0
    ),
])

@app.callback(Output('rate-graph', 'figure'),
              Output('throughput-graph', 'figure'),
              Input('interval-component', 'n_intervals'))
def liveplot(n, t_interval=20):
    df, df2 = read_stats_txs_csv(csv_file, shifttime=True)
    
    # Collect some data
    t_end = np.amax([df.index[-1], df2.index[-1]])
    t_start = df.index[0]
    t_help = t_end - t_interval
    if t_start < t_help:
        t_start = t_help

    fig = go.Figure(
        go.Scatter(x=df[df.index > t_start].index, y=df[df.index > t_start].rates)
    )

    # Edit the layout
    fig.update_layout(title='Rate Index at Time',
                    xaxis_title='Time in s',
                    yaxis_title='Rate Index')

    fig2 = go.Figure(
        go.Scatter(x=df2[df2.index > t_start].index, y=df2[df2.index > t_start].avg_tp)
    )

    # Edit the layout
    fig2.update_layout(title='Average Throughput at Time',
                    xaxis_title='Time in s',
                    yaxis_title='Average throughput in bit/s')
    return fig, fig2

if __name__ == '__main__':
    app.run_server(debug=False)
