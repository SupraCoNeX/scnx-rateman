import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from ratemanager import read_stats_txs_csv

csv_file = "/home/martin/Projects/supraconex/SupraCoNeX_rate-power-control-API/python/data/txsData_AP1.csv"
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# assume you have a "long-form" data frame
# see https://plotly.com/python/px-arguments/ for more options
# df = pd.DataFrame({
#     "Fruit": ["Apples", "Oranges", "Bananas", "Apples", "Oranges", "Bananas"],
#     "Amount": [4, 1, 2, 2, 4, 5],
#     "City": ["SF", "SF", "SF", "Montreal", "Montreal", "Montreal"]
# })

# fig = px.bar(df, x="Fruit", y="Amount", color="City", barmode="group")

df, df2 = read_stats_txs_csv(csv_file)

fig = go.Figure(data=go.Scatter(x=df.index, y=df.rates))

app.layout = html.Div(children=[
    html.H1(children='Example Plot'),

    html.Div(children='''
        Example plot of rate index at timestamp.
    '''),

    dcc.Graph(
        id='example-graph',
        figure=fig
    )
])

if __name__ == '__main__':
    app.run_server(debug=True)
