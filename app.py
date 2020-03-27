import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import logging
import sqlite3
from update_db import update_db
from pull_updated_data import pull_table

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

logger.info('INITIALIZE DB CONNECTION')
conn = sqlite3.connect('2019-nCoV-CDC.db')

# UPDATE DB
logger.info('UPDATE DATABASE W CDC DATA')
update_db(conn)

# PULL UPDATED DATA
cases_by_state_df = pull_table(conn, 'cdc_cases_by_state')
cases_by_report_date_df = pull_table(conn, 'cdc_cases_by_report_date')
cases_by_onset_date_df = pull_table(conn, 'cdc_cases_by_onset_date')

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

colors = {
    'background': '#111111',
    'text': '#7FDBFF'
}

app.layout = html.Div(children=[
    html.H1(children='Hello Dash',
            style={
                'textAlign': 'center',
                'color': colors['text']
            }
        ),

    html.Div(children='''
        Dash: A web application framework for Python.
    ''', style={'textAlign': 'center', 'color': colors['text']}),

    dcc.Graph(
        id='example-graph',
        figure={
            'data': [
                {'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'SF'},
                {'x': [1, 2, 3], 'y': [2, 4, 5], 'type': 'bar', 'name': u'Montréal'},
            ],
            'layout': {
                'title': 'Dash Data Visualization',
                'plot_bgcolor': colors['background'],
                'paper_bgcolor': colors['background'],
                'font': {'color': colors['text']}
            }
        }
    )
])

if __name__ == '__main__':
    app.run_server(debug=True)