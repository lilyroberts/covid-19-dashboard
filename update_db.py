# IMPORT NECESSARY PACKAGES
import pandas as pd
import numpy as np
import requests
import json
import datetime as dt
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

logger.info('SET ENVIRONMENT VARIABLES')

# ENVIRONMENT VARIABLES
CASES_BY_STATE_URL = 'https://www.cdc.gov/coronavirus/2019-ncov/map-cases-us.json'
CASES_BY_REPORT_DATE_URL = 'https://www.cdc.gov/coronavirus/2019-ncov/cases-updates/total-cases-onset.json'
CASES_BY_ONSET_DATE_URL = 'https://www.cdc.gov/coronavirus/2019-ncov/cases-updates/us-cases-epi-chart.json'
CURRENT_DATE = dt.datetime.strftime(dt.datetime.now(), '%Y%m%d')

# CREDENTIALS IF NEEDED
credentials_json_path = "secrets/credentials.json"
credentials = json.load(open(credentials_json_path))
MONGODB_USERNAME = credentials["mongodb_username"]
MONGODB_PASSWORD = credentials["mongodb_password"]


def update_db(conn):

    c = conn.cursor()

    # GET UPDATED DATA FROM CDC
    logger.info('GET UPDATED DATA FROM CDC.GOV')
    cases_by_state_response = requests.get(CASES_BY_STATE_URL)
    cases_by_report_date_response = requests.get(CASES_BY_REPORT_DATE_URL)
    cases_by_onset_date_response = requests.get(CASES_BY_ONSET_DATE_URL)

    # DECODE JSON AND PULL OUT DATA
    logger.info('DECODE AND FORMAT DATA')
    cases_by_state = json.loads(cases_by_state_response.text)['data']
    cases_by_report_date = json.loads(cases_by_report_date_response.text)['data']['columns']
    cases_by_onset_date = json.loads(cases_by_onset_date_response.text)['data']['columns']

    # CAST INTO DATAFRAMES / CLEAN / ORGANIZE
    cases_by_state_df = pd.DataFrame(cases_by_state)
    cases_by_state_df = cases_by_state_df.rename(columns={'Community Transmission�': 'community_transmission',
                                                          'Jurisdiction': 'state',
                                                          'Cases Reported': 'n_cases',
                                                          'Range': 'range',
                                                          'URL': 'url'})
    cases_by_state_df = cases_by_state_df.set_index(['state'])
    cases_by_state_df.loc[(cases_by_state_df['n_cases'] == 'None'), 'n_cases'] = np.nan
    cases_by_state_df['n_cases'] = cases_by_state_df['n_cases'].astype(float)

    cases_by_report_date_df = pd.DataFrame(cases_by_report_date)
    cases_by_report_date_df = cases_by_report_date_df.set_index(cases_by_report_date_df[0], drop=True)
    cases_by_report_date_df = cases_by_report_date_df.iloc[:, 1:] \
                                                     .transpose() \
                                                     .rename(columns={'x': 'date',  # ERROR IN CDC DATA HANDLED
                                                                      'data1': 'n_cases',
                                                                      'datat1': 'n_cases'}) \
                                                     .reset_index(drop=True)
    cases_by_report_date_df['date'] = pd.to_datetime(cases_by_report_date_df['date'])
    cases_by_report_date_df['n_cases'] = cases_by_report_date_df['n_cases'].astype(int)

    cases_by_onset_date_df = pd.DataFrame(cases_by_onset_date)
    cases_by_onset_date_df = cases_by_onset_date_df.set_index(cases_by_onset_date_df[0], drop=True)
    cases_by_onset_date_df = cases_by_onset_date_df.iloc[:, 1:] \
                                                     .transpose() \
                                                     .rename(columns={'x': 'date',  # ERROR IN CDC DATA HANDLED
                                                                      'data1': 'n_cases',
                                                                      'datat1': 'n_cases'}) \
                                                     .reset_index(drop=True)
    cases_by_onset_date_df['date'] = pd.to_datetime(cases_by_onset_date_df['date'])
    cases_by_onset_date_df['n_cases'] = cases_by_onset_date_df['n_cases'].astype(int)

    # ADD OR UPDATE DATA INTO SQL DB
    logger.info('INSERT UPDATED DATA INTO DB')
    cases_by_state_df.to_sql(name='cdc_cases_by_state'+CURRENT_DATE, con=conn, if_exists='replace')
    cases_by_report_date_df.to_sql(name='cdc_cases_by_report_date'+CURRENT_DATE, con=conn, if_exists='replace')
    cases_by_onset_date_df.to_sql(name='cdc_cases_by_onset_date'+CURRENT_DATE, con=conn, if_exists='replace')

    # pull nrows for logging and error checking
    # by state
    c.execute("SELECT * FROM cdc_cases_by_state"+CURRENT_DATE)
    cases_by_state_nrows = len(pd.DataFrame(c.fetchall()))
    logger.info(str(cases_by_state_nrows) + " ROWS PERSISTED TO cdc_cases_by_state"+CURRENT_DATE)

    # by report date
    c.execute("SELECT * FROM cdc_cases_by_report_date"+CURRENT_DATE)
    cases_by_report_date_nrows = len(pd.DataFrame(c.fetchall()))
    logger.info(str(cases_by_report_date_nrows) + " ROWS PERSISTED TO cdc_cases_by_report_date"+CURRENT_DATE)

    # by onset date
    c.execute("SELECT * FROM cdc_cases_by_onset_date"+CURRENT_DATE)
    cases_by_onset_date_nrows = len(pd.DataFrame(c.fetchall()))
    logger.info(str(cases_by_onset_date_nrows) + " ROWS PERSISTED TO cdc_cases_by_onset_date"+CURRENT_DATE)

    return
