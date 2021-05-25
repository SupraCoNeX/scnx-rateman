import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dash.dependencies import Input, Output, State

from ratemanager import read_stats_txs_csv

csv_file = "../demo/collected_data/data_AP2.csv"
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(children=[
    html.H1(children='Example Plots'),

    dcc.Input(id='input-1-state', type='text', value=csv_file),
    html.Button(id='load-button-state', n_clicks=0, children='Load CSV file'),
    html.Div(id='output-state'),

    dcc.Graph(id='rate-graph'),

    dcc.Graph(id='throughput-graph')
])

@app.callback(Output('rate-graph', 'figure'),
              Output('throughput-graph', 'figure'),
              Output('output-state', 'children'),
              Input('load-button-state', 'n_clicks'),
              State('input-1-state', 'value'))
def update_output(n_clicks, filename):
    try:
        df, df2 = read_stats_txs_csv(filename, shifttime=True)
    except pd.errors.EmptyDataError:
        output_text = 'Dataframe is empty. Please load another csv file.'
        fig = go.Figure()
        fig2 = go.Figure()
        return fig, fig2, output_text
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
                        yaxis_title='Average throughput in bit/s??')
        return fig, fig2, output_text

if __name__ == '__main__':
    app.run_server(debug=False)
