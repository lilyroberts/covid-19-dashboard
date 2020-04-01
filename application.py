import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import logging
import sqlite3
import datetime
import pandas as pd
from update_db import update_db
from pull_updated_data import pull_table
from urllib.request import urlopen
import json

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

logger.info('INITIALIZE DB CONNECTION')
conn = sqlite3.connect('2019-nCoV-CDC.db')

# UPDATE DB
logger.info('UPDATE DATABASE W CDC DATA')
update_db(conn)

# PULL UPDATED DATA
state_cols = ['state','n_cases','range','community_spread']
cases_by_state_df = pull_table(conn, 'cdc_cases_by_state')\
    .sort_values('n_cases',ascending=False)\
    .dropna().reset_index(drop=False)[state_cols]
cases_by_report_date_df = pull_table(conn, 'cdc_cases_by_report_date').transpose()
cases_by_onset_date_df = pull_table(conn, 'cdc_cases_by_onset_date').transpose()

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
application = app.server

colors = {
    'background': '#011f4b',
    'text': '#ffffff'
}

# show data tables
# make bar chart Plotly figures

cases_by_report_date_bar = go.Figure([go.Bar(x=cases_by_report_date_df.transpose().reset_index().date,
                                             y=cases_by_report_date_df.transpose().n_cases)])

cases_by_onset_date_bar = go.Figure([go.Bar(x=cases_by_onset_date_df.transpose().reset_index().date,
                                            y=cases_by_onset_date_df.transpose().n_cases)])

state_col_map = dict(state=dict(name='Jurisdiction', id='state'),
                     range=dict(name='Range Confirmed Cases', id='range'),
                     n_cases=dict(name='N Confirmed Cases', id='n_cases'),
                     community_spread=dict(name='Community Spread', id='community_spread'))

# create state name abbreviation mapping from file
mapping_dict = pd.read_csv('state_abbrev_mapping.csv',index_col='state_name').to_dict(orient='index')
cases_by_state_df['state_abbrev'] = [mapping_dict.get(i)['state_abbrev']
                                     for i in cases_by_state_df.reset_index().dropna().state.values]

# create chloropleth figure
cases_by_state_chloropleth = go.Figure(data=go.Choropleth(
                                            locations=cases_by_state_df['state_abbrev'],
                                            z=cases_by_state_df['n_cases'],
                                            locationmode='USA-states',
                                            colorscale='Reds',
                                            colorbar_title='N Confirmed Cases',
                                            )
                                      )

cases_by_state_chloropleth.update_layout(geo_scope='usa',
                                         title={'text':'Total Confirmed Cases of SARS-CoV-2 by U.S. State',
                                                'xanchor': 'center',
                                                'x':0.5,
                                                'yanchor': 'top'})

counties_df = pd.read_csv('https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv',
                          dtype={'fips':'str'})
counties_df.loc[:,'fips'] = counties_df.dropna(axis=0)

with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
    counties = json.load(response)

most_recent_date = pd.DataFrame(counties_df.groupby(['fips']).max()['date']).to_dict()['date']

current_counties_df = counties_df[counties_df.apply(lambda row: True if (row['date'] == most_recent_date.get(row['fips'])) else False,
                              axis=1)]

cases_by_county_chloropleth = \
                    go.Figure(data=go.Choroplethmapbox(
                        geojson=counties,
                        z=current_counties_df.cases,
                        locations=current_counties_df.fips,
                        colorscale='Reds',
                        zmin=0, zmax=12,
                        marker_opacity=0.5, marker_line_width=0))

cases_by_county_chloropleth.update_layout(mapbox_style="carto-positron",
                                          mapbox_zoom=3, mapbox_center={"lat": 37.0902, "lon": -95.7129})

cases_by_county_chloropleth.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

app.layout = html.Div(children=[
    html.H1(children='SARS-CoV-2',
            style={
                'textAlign': 'center',
                'color': colors['text'],
                'font':'Helvetica',
                'font-weight':'bold'
            }
            ),

    html.Div(children=html.P(['Tracking the 2019 novel coronavirus pandemic.',
                     html.Br(),
                     'Created by Lily Slomski Roberts',
                     html.Br(),
                     'Project repository: ',
                     html.A('https://github.com/queerpolymath/SARS-CoV-2-Analysis',
                            href='https://github.com/queerpolymath/SARS-CoV-2-Analysis',
                            target='_blank'),
                     html.Br(),
                     html.A('Donate to the Food Bank for New York City',
                            href='https://secure3.convio.net/fbnyc/site/Donation2?df_id=9776&mfc_pref=T&9776.donation=form1&multiply=10&commas=yes',
                            target='_blank'),
                     ' ; give to mutual aid orgs ; support each other. :)',
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

    html.H4(children='Reported Cases by US County',
            style={
                'textAlign': 'center',
                'color': colors['text'],
                'font': 'Helvetica'
            }
            ),

    dcc.Graph(id='cases_by_county_chloropleth',
              figure=cases_by_county_chloropleth),

    html.Caption('Data from New York Times - Updated at ' + str(datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(hours=4.0),
                                                                                    '%Y-%m-%d %I:%M:%S %p' + ' ET')),
                 style={'font': 'Helvetica',
                        'font-style':'italic',
                        'font-weight':'light',
                        'white-space': 'nowrap',
                        'overflow': 'hidden',
                        'color': colors['text']}),

    html.H4(children='Reported Cases by US State/Territory',
            style={
                'textAlign': 'center',
                'color': colors['text'],
                'font':'Helvetica'
            }
            ),
    dash_table.DataTable(id='cases-by-state-dash-table',
                         columns=[{"name": state_col_map.get(i).get('name'),
                                   "id": state_col_map.get(i).get('id')}
                                  for i in state_cols],
                         data=cases_by_state_df.to_dict('records'),
                         style_table={'overflowX': 'scroll',
                                      'backgroundColor':colors['background'],
                                      'overflowY':'scroll',
                                      'maxHeight':'330px'},
                         style_cell={'textAlign':'left'},
                         style_header={'backgroundColor':'#b3cde0',
                                       'fontWeight':'bold',
                                       'textAlign':'center'}),

    html.Br(),

    dcc.Graph(id='cases-by-state-chloropleth',
              figure=cases_by_state_chloropleth,
              style={'textAlign': 'center'}),

    html.Caption('Data from CDC.gov - Updated at ' + str(datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(hours=4.0),
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

    html.Caption('Data from CDC.gov - Updated at ' + str(datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(hours=4.0),
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
    html.Caption('Data from CDC.gov - Updated at ' + str(datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(hours=4.0),
                                                                                    '%Y-%m-%d %I:%M:%S %p' + ' ET')),
                 style={'font': 'Helvetica',
                        'font-style': 'italic',
                        'font-weight': 'light',
                        'white-space': 'nowrap',
                        'overflow': 'hidden',
                        'color': colors['text']})
    ],
    style=dict(padding='10%',
               margin='auto',
               backgroundColor=colors['background']))

if __name__ == '__main__':
    application.run_server(debug=False, port=8080)
