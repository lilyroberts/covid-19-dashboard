import pandas as pd
import json
import sqlite3
import datetime as dt
import logging
from urllib.request import urlopen

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

CURRENT_DATE = dt.datetime.strftime(dt.datetime.now(), '%Y%m%d')


# FUNCTION TO PULL TABLE FROM DB
def pull_table(conn, name) -> pd.DataFrame:
    c = conn.cursor()
    c.execute("SELECT * FROM "+name+CURRENT_DATE)

    column_slice = {'cdc_cases_by_state': [0, 1, 2, 3, 4],
                    'cdc_cases_by_report_date': [1, 2],
                    'cdc_cases_by_onset_date': [1, 2]}

    column_map = {'cdc_cases_by_state': {0: 'state', 1: 'range', 2: 'n_cases', 3: 'community_spread', 4: 'url'},
                  'cdc_cases_by_report_date': {1: 'date', 2: 'n_cases'},
                  'cdc_cases_by_onset_date': {1: 'date', 2: 'n_cases'}}

    index_col = {'cdc_cases_by_state': 'state',
                 'cdc_cases_by_report_date': 'date',
                 'cdc_cases_by_onset_date': 'date'}

    df = pd.DataFrame(c.fetchall())[column_slice[name]].rename(columns=column_map[name]).set_index(index_col[name], drop=True)

    logger.info(str(len(df)) + " ROWS PULLED FROM "+name)

    return df


def get_counties_df() -> pd.DataFrame:
    logger.info('read data from source')
    counties_df = pd.read_csv('https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv',
                            dtype={'fips': 'str'})
    nyc_fips = ['36005', '36047', '36085', '36081', '36061']
    COLS = ['date', 'county', 'state', 'fips', 'cases', 'deaths']

    def add_nyc_fips(row):
        temp_df = pd.DataFrame(columns=COLS)
        for i in nyc_fips:
            s = pd.Series([row.date, row.county, row.state, i, row.cases, row.deaths],
                        index=COLS)
            temp_df = pd.concat([temp_df, pd.DataFrame(s).transpose()]).reset_index(drop=True)
        return temp_df

    logger.info('add nyc fips')
    nyc_counties_df = pd.DataFrame(columns=COLS)
    non_nyc_counties_df = counties_df[counties_df['county'] != 'New York City']
    for row in counties_df[counties_df['county'] == 'New York City'].itertuples():
        nyc_counties_df = pd.concat([nyc_counties_df, add_nyc_fips(row)]).reset_index(drop=True)

    counties_df = pd.concat([non_nyc_counties_df, nyc_counties_df])

    logger.info('calculate new cases')
    # calculate new cases per day
    counties_df = counties_df.sort_values(by='date', ascending=True)
    counties_df['cases_lagged'] = counties_df.groupby('fips')['cases'].shift(1)
    counties_df['new_cases'] = counties_df['cases'] - counties_df['cases_lagged']
    counties_df.loc[counties_df['new_cases'] < 0, 'new_cases'] = 0
    # counties_df['new_cases'] = counties_df['new_cases'].astype(np.longdouble)

    logger.info('calculate rolling mean')
    # calculate 7 day rolling mean of new cases
    newcases_rolling =  (
            counties_df
            .set_index(['fips','date'])
            .drop(['county', 'state'])
            .groupby('fips')
            .rolling(window=7)
            .mean()['new_cases']
            .rename('new_cases_rolling')
            .droplevel(0)
            )
    counties_df = counties_df.merge(
        pd.DataFrame(newcases_rolling),
        on=['fips', 'date'],
        how='left'
    )

    # read in population data
    dtypes={
        'state_fips': str,
        'county_fips': str,
        'fips': str,
        'state': str,
        'county': str,
        'popest': int
    }
    popest = pd.read_excel('popest2019_nyc.xlsx', dtype=dtypes)
    popest[popest['county_fips'] != "000"]
    popest = popest[['fips','popest']]

    # incorporate into dataset
    counties_df = counties_df.merge(
        popest,
        on='fips'
    )

    logger.info('calculate new cases per 100k')
    # calculate rolling new cases per 100k population
    counties_df['new_cases_per100k'] = (
        (counties_df['new_cases_rolling']/counties_df['popest']) * 100000
    )
    
    return counties_df

def make_current_counties_df(counties_df):
    logger.info('make current counties df')
    most_recent_date = pd.DataFrame(counties_df.groupby(['fips']).max()['date'])
    current_counties_df = counties_df.join(
        most_recent_date, 
        on='fips',
        how='inner', 
        rsuffix='_mostrecent'
    )
    current_counties_df = current_counties_df[
        current_counties_df['date'] == current_counties_df['date_mostrecent']
        ]
    current_counties_df = current_counties_df[counties_df.columns]
    return current_counties_df

def get_counties_geojson():
    url = 'https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json'
    with urlopen(url) as response:
        counties = json.load(response)
    return counties