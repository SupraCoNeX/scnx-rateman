import base64

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dash.dependencies import Input, Output, State

from ratemanager import read_stats_txs_csv

#TODO: Wrap multiple plots into a plot with subplots.

csv_file = "../demo/collected_data/data_AP2.csv"
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(children=[
    html.H1(children='Example Plots'),
    
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        accept='.csv, text/plain, application/vnd.ms-excel, text/csv',
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
    ),
    html.Div(id='output-state'),

    dcc.Graph(id='rate-graph'),

    dcc.Graph(id='throughput-graph'),
])

@app.callback(Output('rate-graph', 'figure'),
              Output('throughput-graph', 'figure'),
              Output('output-state', 'children'),
              Input('upload-data', 'contents'))
def update_output(contents):
    if contents is not None:
        _, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        try:
            df, df2 = read_stats_txs_csv(decoded, shifttime=True, bin_enc=True)
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
                            yaxis_title='Average throughput in bit/s')
            return fig, fig2, output_text

if __name__ == '__main__':
    app.run_server(debug=False)
