import base64
import io

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

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(
    children=[
        html.H1(children="Example Plots"),
        html.Div(id="output-state"),
        dcc.Graph(id="graph", figure=go.Figure()),
        dcc.Interval(
            id="interval-component", interval=1 * 1000, n_intervals=0  # in milliseconds
        ),
        # dcc.Store inside the app that stores the intermediate value
        dcc.Store(id="traces-to-plot"),
        html.Div(children="Select AP list:"),
        dcc.Upload(
            id="select-aplist",
            children=html.Div(["Drag and Drop or ", html.A("Select Files")]),
            style={
                "width": "100%",
                "height": "60px",
                "lineHeight": "60px",
                "borderWidth": "1px",
                "borderStyle": "dashed",
                "borderRadius": "5px",
                "textAlign": "center",
                "margin": "10px",
            },
        ),
        html.Div(children="Select AP to plot:", id="test-id"),
        dcc.Dropdown(
            options=[],
            value=[],
            multi=True,
            id="traces-dropdown",
        ),
    ]
)


@app.callback(Output("traces-dropdown", "options"), Input("select-aplist", "contents"))
def select_aplist(contents):
    if contents is not None:
        _, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)
        # Assume that the user uploaded a CSV file
        ap_list_df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
        options = []
        for _, row in ap_list_df.iterrows():
            options.append(
                {
                    "label": "{} - {}".format(row["APID"], row["IPADD"]),
                    "value": row["APID"],
                }
            )
        return options
    else:
        return []


@app.callback(Output("traces-to-plot", "data"), Input("traces-dropdown", "value"))
def update_traces_to_plot(value):
    return value


@app.callback(
    Output("graph", "figure"),
    Input("interval-component", "n_intervals"),
    Input("traces-dropdown", "value"),
)
def liveplot(n, dd_val, t_interval=20):
    if not dd_val:
        return go.Figure()
    dfs, df2s = [], []
    for apid in dd_val:
        d1, d2 = read_stats_txs_csv(
            "collected_data/data_{}.csv".format(apid), shifttime=True
        )
        dfs.append(d1)
        df2s.append(d2)

    # Collect some data
    end_list = []
    start_list = []
    for df, df2 in zip(dfs, df2s):
        if df.empty:
            s1 = 0
            e1 = 0
        else:
            s1 = df.index[0]
            e1 = df.index[-1]
        if df2.empty:
            s2 = 0
            e2 = 0
        else:
            s2 = df.index[0]
            e2 = df.index[-1]
        end_list.extend([e1, e2])
        start_list.extend([s1, s2])

    t_end = np.amax(end_list)
    t_start = np.amin(start_list)
    t_help = t_end - t_interval
    if t_start < t_help:
        t_start = t_help

    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("Rate Index vs Time", "Average Throughput vs Time"),
        shared_xaxes=True,
    )
    for df, df2 in zip(dfs, df2s):
        fig.add_trace(
            go.Scatter(x=df[df.index > t_start].index, y=df[df.index > t_start].rates),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df2[df2.index > t_start].index, y=df2[df2.index > t_start].avg_tp
            ),
            row=2,
            col=1,
        )
    fig.update_layout(showlegend=False)
    return fig


if __name__ == "__main__":
    app.run_server(debug=False)
