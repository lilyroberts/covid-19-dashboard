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
from update_db import update_db
from pull_updated_data import pull_table
from urllib.request import urlopen
import json

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def make_cases_by_state_chloropleth(cases_by_state_df):
    # create state name abbreviation mapping from file
    mapping_dict = pd.read_csv('state_abbrev_mapping.csv',index_col='state_name').to_dict(orient='index')
    cases_by_state_df['state_abbrev'] = [mapping_dict.get(i)['state_abbrev']
                                        for i in cases_by_state_df.reset_index().dropna().state.values]

    logger.info('create cases by state chloropleth')
    # create chloropleth figure
    cases_by_state_chloropleth = go.Figure(data=go.Choropleth(
                                                locations=cases_by_state_df['state_abbrev'],
                                                z=cases_by_state_df['n_cases'],
                                                locationmode='USA-states',
                                                colorscale='Reds',
                                                colorbar_title='N Confirmed Cases'
                                                )
                                        )

    cases_by_state_chloropleth.update_layout(geo_scope='usa',
                                            title={'text':'Total Confirmed Cases of SARS-CoV-2 by U.S. State',
                                                    'xanchor': 'center',
                                                    'x':0.5,
                                                    'yanchor': 'top'})

    return cases_by_state_chloropleth


def make_cases_by_county_chloropleth(
    counties_df, 
    current_counties_df, 
    counties
    ):

    logger.info('cases by county chloropleth')
    days = counties_df.date.sort_values().unique()
    days = days[-7:]
    logger.info('fig data')
    fig_data = go.Choroplethmapbox(
                geojson=counties,
                z=np.log(current_counties_df.new_cases_per100k),
                locations=current_counties_df.fips,
                colorbar_title='log(N Cases per 100k population)',
                colorbar_title_side='right',
                colorscale='Reds',
                marker_opacity=0.5, marker_line_width=0,
                text=(current_counties_df.county + ' County, ' + current_counties_df.state),
                customdata=round(current_counties_df.new_cases_per100k,1),
                hovertemplate="%{text}<br>Cases per 100k: %{customdata}",
                name=""
            )

    logger.info('fig layout')
    fig_layout = go.Layout(mapbox_style="carto-positron",
                        mapbox_zoom=2, 
                        mapbox_center={"lat": 37.0902, "lon": -95.7129},
                        margin={"r": 0, "t": 0, "l": 0, "b": 0},
                        autosize=True,
                        title_text="log(N) Confirmed Cases/100k of COVID-19 by U.S. County",
                        titlefont_color='#011f4b',
                        title_x=0.5,
                        title_y=0.985,
                        height=500)


    logger.info('updatemenus')
    fig_layout["updatemenus"] = [dict(type="buttons",
                                    buttons=[dict(label="Play",
                                                    method="animate",
                                                    args=[None,
                                                        dict(frame=dict(duration=1000,
                                                                        redraw=True),
                                                            fromcurrent=True)]),
                                            dict(label="Pause",
                                                    method="animate",
                                                    args=[[None],
                                                        dict(frame=dict(duration=0,
                                                                        redraw=True),
                                                            mode="immediate")])],
                                    direction="left",
                                    pad={"r": 10, "t": 35},
                                    showactive=False,
                                    x=0.1,
                                    xanchor="right",
                                    y=0,
                                    yanchor="top")]

    logger.info('sliders')
    sliders_dict = dict(active=len(days) - 1,
                        visible=True,
                        yanchor="top",
                        xanchor="left",
                        currentvalue=dict(font=dict(size=14),
                                        prefix="Date: ",
                                        visible=True,
                                        xanchor="right"),
                        pad=dict(b=10,
                                t=10),
                        len=0.875,
                        x=0.125,
                        y=0,
                        steps=[])

    logger.info('frames')
    fig_frames = []
    for day in days:
        logger.info(f'frame {day}')
        plot_df = counties_df[counties_df.date == day]
        frame = go.Frame(data=[go.Choroplethmapbox(geojson=counties,
                                                locations=plot_df.fips,
                                                z=np.log(plot_df.new_cases_per100k),
                                                name="",
                                                text=(current_counties_df.county + ' County, ' + current_counties_df.state),
                                                customdata=round(current_counties_df.new_cases_per100k,1),
                                                hovertemplate="%{text}<br>%{customdata}")],
                        name=day)
        fig_frames.append(frame)

        slider_step = dict(args=[[day],
                                dict(mode="immediate",
                                    frame=dict(duration=300,
                                                redraw=True))],
                        method="animate",
                        label=day)
        sliders_dict["steps"].append(slider_step)

    fig_layout.update(sliders=[sliders_dict])

    logger.info('make cases by county chloropleth')
    cases_by_county_chloropleth = \
        go.Figure(
            data=fig_data,
            layout=fig_layout,
            frames=fig_frames
        )
    cases_by_county_chloropleth.update_yaxes(automargin=True)

    return cases_by_county_chloropleth


def make_cases_by_date_bar(cases_by_date_df):
    x = cases_by_date_df.transpose().reset_index().date
    y = cases_by_date_df.transpose().n_cases
    return go.Figure([go.Bar(x=x, y=y)])