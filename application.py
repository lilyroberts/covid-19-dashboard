import dash
from dash import dash_table
from dash import dcc
from dash import html
import plotly.graph_objects as go
import logging
import sqlite3
import datetime
import math
import pandas as pd
import numpy as np
from urllib.request import urlopen
import json

from update_db import update_db
from pull_updated_data import (
    get_counties_geojson,
    pull_table, 
    get_counties_df,
    make_current_counties_df,
    get_counties_geojson
)
from make_figures import (
    make_cases_by_state_chloropleth,
    make_cases_by_county_chloropleth,
    make_cases_by_date_bar
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

logger.info('INITIALIZE DB CONNECTION')
conn = sqlite3.connect('2019-nCoV-CDC.db')

# constants
STATE_COL_MAP = {
    'state': {'name': 'Jurisdiction', 'id': 'state'},
    'range': {'name': 'Range Confirmed Cases', 'id': 'range'},
    'n_cases': {'name': 'N Confirmed Cases', 'id': 'n_cases'},
    'community_spread': {'name': 'Community Spread', 'id': 'community_spread'}
}

STATE_COLS = ['state','n_cases','range','community_spread']

# UPDATE DB
logger.info('UPDATE DATABASE W CDC DATA')
update_db(conn)

# PULL UPDATED DATA
cases_by_state_df = (
    pull_table(conn, 'cdc_cases_by_state')
        .sort_values('n_cases',ascending=False)
        .dropna().reset_index(drop=False)[STATE_COLS]
)
cases_by_report_date_df = pull_table(conn, 'cdc_cases_by_report_date').transpose()
cases_by_onset_date_df = pull_table(conn, 'cdc_cases_by_onset_date').transpose()

# show data tables
# make bar chart Plotly figures
logger.info('cases by report date figure')
cases_by_report_date_bar = make_cases_by_date_bar(cases_by_report_date_df)

logger.info('cases by onset date figure')
cases_by_onset_date_bar = make_cases_by_date_bar(cases_by_onset_date_df)

logger.info('make cases by state chloropleth')
cases_by_state_chloropleth = make_cases_by_state_chloropleth(cases_by_state_df)

logger.info('cases by county')
counties_df = get_counties_df()
current_counties_df = make_current_counties_df(counties_df)

counties = get_counties_geojson()

cases_by_county_chloropleth = make_cases_by_county_chloropleth(counties_df, current_counties_df, counties)

display_counties_df = current_counties_df[['date','county','state','new_cases_per100k','deaths']] \
                        .drop_duplicates() \
                        .set_index('date') \
                        .sort_values('new_cases_per100k', ascending=False)


#######################
### CREATE DASH APP ###
#######################
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
application = app.server

colors = {
    'background': '#011f4b',
    'text': '#ffffff'
}

logger.info('create app layout')
app.layout = html.Div(children=[
    html.H1(children='COVID-19 Dashboard',
            style={
                'textAlign': 'center',
                'color': colors['text'],
                'font':'Helvetica',
                'font-weight':'bold'
            }
            ),

    html.Div(children=html.P(['Tracking the 2019 novel coronavirus pandemic.',
                     html.Br(),
                     'Created by Lily Roberts',
                     html.Br(),
                     'Project repository: ',
                     html.A('https://github.com/lilyroberts/SARS-CoV-2-Analysis',
                            href='https://github.com/lilyroberts/SARS-CoV-2-Analysis',
                            target='_blank'),
                     html.Br(),
                     html.A('Donate to the Food Bank for New York City',
                            href='https://secure3.convio.net/fbnyc/site/Donation2?df_id=9776&mfc_pref=T&9776.donation=form1&multiply=10&commas=yes',
                            target='_blank'),
                     html.Br()]),
             style={'textAlign': 'center', 'color': colors['text'], 'backgroundColor': colors['background'],
                'font':'Helvetica', 'display':'block'}),

    # dcc.Graph(
    #     id='cases-by-state-table',
    #     figure=cases_by_state_table
    # ),

    # dcc.Graph(
    #     id='cases-by-report-date-table',
    #     figure=cases_by_report_date_table
    # ),
    html.Div(children = [
        html.H4(children='Reported Cases by US County',
                style={
                    'textAlign': 'center',
                    'color': colors['text'],
                    'font': 'Helvetica'
                }
                ),

        html.Div(children=[
            dcc.Graph(id='cases_by_county_chloropleth',
                    figure=cases_by_county_chloropleth)
            ],
            style={'width': '50%', 'display': 'inline-block'}
        ),

        html.Div(children = [
            dash_table.DataTable(id='cases-by-county-dash-table',
                                columns=[{"name": i, "id": i} for i in display_counties_df.columns],
                                data=display_counties_df.to_dict('records'),
                                style_cell={'textAlign': 'left'},
                                style_table={'overflowX': 'scroll',
                                            'overflowY':'scroll',
                                            'maxHeight':'500px',
                                            'backgroundColor': colors['background'],
                                            'color': colors['background']},
                                style_header={'backgroundColor': '#b3cde0',
                                            'fontWeight': 'bold',
                                            'textAlign': 'center'})#,

            # html.Caption('Data from New York Times - Updated at '
            #             + str(datetime.datetime.strftime(datetime.datetime.now(),
            #                                             '%Y-%m-%d %I:%M:%S %p' + ' ET')),
            #             style={'font': 'Helvetica',
            #                     'font-style':'italic',
            #                     'font-weight':'light',
            #                     'white-space': 'nowrap',
            #                     'overflowY': 'hidden',
            #                     'color': colors['text']})#,
            ],
            style={'width': '50%', 'display': 'inline-block'}
        )
    ],
    className = 'double-graph'),
    html.Br(),

    html.H4(children='Reported Cases by US State/Territory',
            style={
                'textAlign': 'center',
                'color': colors['text'],
                'font':'Helvetica'
            }
            ),

    html.Br(),

    dcc.Graph(id='cases-by-state-chloropleth',
              figure=cases_by_state_chloropleth,
              style={'textAlign': 'center'}),

    html.Br(),

    dash_table.DataTable(id='cases-by-state-dash-table',
                         columns=[{"name": STATE_COL_MAP.get(i).get('name'),
                                   "id": STATE_COL_MAP.get(i).get('id')}
                                  for i in STATE_COLS],
                         data=cases_by_state_df.to_dict('records'),
                         style_table={'overflowX': 'scroll',
                                      'backgroundColor':colors['background'],
                                      'overflowY':'scroll',
                                      'maxHeight':'330px'},
                         style_cell={'textAlign':'left'},
                         style_header={'backgroundColor':'#b3cde0',
                                       'fontWeight':'bold',
                                       'textAlign':'center'}),

    html.Caption('Data from CDC.gov - Updated at '
                 + str(datetime.datetime.strftime(datetime.datetime.now(),
                                                  '%Y-%m-%d %I:%M:%S %p' + ' ET')),
                 style={'font': 'Helvetica',
                        'font-style':'italic',
                        'font-weight':'light',
                        'white-space': 'nowrap',
                        'overflow': 'hidden',
                        'color': colors['text']}),

    html.H4(children='Total Confirmed Cases of SARS-CoV-2 in United States',
            style={
                'textAlign': 'center',
                'color': colors['text'],
                'font':'Helvetica'
            }
            ),

    dcc.Graph(id='cases-by-report-date-bar',
              figure=cases_by_report_date_bar),

    html.Br(),

    html.Div(children='scroll >>>',
             style={'textAlign': 'right',
                    'color':'#b3cde0',
                    'font': 'Helvetica',
                    'font-style':'italic'}),

    dash_table.DataTable(id='cases_by_report_date_table',
                         columns=[{"name": str(i)[:11], "id": i} for i in cases_by_report_date_df.columns],
                         data=cases_by_report_date_df.to_dict('records'),
                         style_cell={'textAlign': 'left'},
                         style_table={'overflowX': 'scroll',
                                      'backgroundColor': colors['background'],
                                      'color':colors['background']},
                         style_header={'backgroundColor': '#b3cde0',
                                       'fontWeight': 'bold',
                                       'textAlign': 'center'}
                         ),

    html.Caption('Data from CDC.gov - Updated at '
                 + str(datetime.datetime.strftime(datetime.datetime.now(),
                                                  '%Y-%m-%d %I:%M:%S %p' + ' ET')),
                 style={'font': 'Helvetica',
                        'font-style': 'italic',
                        'font-weight': 'light',
                        'white-space': 'nowrap',
                        'overflow': 'hidden',
                        'color': colors['text']}),

    html.H4(children='Count of Cases in United States by Onset Date',
            style={
                'textAlign': 'center',
                'color': colors['text'],
                'font':'Helvetica'
            }
            ),

    dcc.Graph(id='cases-by-onset-date-bar',
              figure=cases_by_onset_date_bar),

    html.Br(),

    html.Div(children='scroll >>>',
             style={'textAlign': 'right',
                    'color': '#b3cde0',
                    'font': 'Helvetica',
                    'font-style': 'italic'}),

    dash_table.DataTable(id='cases_by_onset_date_table',
                         columns=[{"name": str(i)[:11], "id": i} for i in cases_by_onset_date_df.columns],
                         data=cases_by_onset_date_df.to_dict('records'),
                         style_table={'overflowX': 'scroll'},
                         style_cell={'textAlign': 'left'},
                         style_header={'backgroundColor': '#b3cde0',
                                       'fontWeight': 'bold',
                                       'font':'Helvetica',
                                       'textAlign': 'center'}
                         ),
    html.Caption('Data from CDC.gov - Updated at '
                 + str(datetime.datetime.strftime(datetime.datetime.now(),
                                                    '%Y-%m-%d %I:%M:%S %p' + ' ET')),
                 style={'font': 'Helvetica',
                        'font-style': 'italic',
                        'font-weight': 'light',
                        'white-space': 'nowrap',
                        'overflow': 'hidden',
                        'color': colors['text']})
    ],
    style=dict(padding='0%',
               margin='auto',
               backgroundColor=colors['background']))

if __name__ == '__main__':
    app.run_server(debug=False, port=8080)
