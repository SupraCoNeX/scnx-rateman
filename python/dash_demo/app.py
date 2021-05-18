import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from ratemanager import read_stats_txs_csv

csv_file = "../demo/collected_data/data_AP1.csv"
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

fig = go.Figure(go.Scatter(x=df.index, y=df.rates))

# Edit the layout
fig.update_layout(title='Rate Index at timestamp',
                   xaxis_title='Timestamp in s',
                   yaxis_title='Rate Index')

fig2 = go.Figure(go.Scatter(x=df2.index, y=df2.avg_tp))

# Edit the layout
fig2.update_layout(title='Average Throughput at timestamp',
                   xaxis_title='Timestamp in s',
                   yaxis_title='Average throughput in Hex')
app.layout = html.Div(children=[
    html.H1(children='Example Plots'),

    # html.Div(children='''
    #     Example plot with rate index on the y-axis and timestamps on x-axis.
    # '''),

    dcc.Graph(
        id='example-graph',
        figure=fig
    ),

    # html.Div(children='''
    #     Example plot with average throughout on the y-axis and timestamps on
    #           x-axis.
    # '''),

    dcc.Graph(
        id='example-graph2',
        figure=fig2
    )
])

if __name__ == '__main__':
    app.run_server(debug=True)
