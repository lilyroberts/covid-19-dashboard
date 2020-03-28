import pandas as pd
import json
import sqlite3
import datetime as dt
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

CURRENT_DATE = dt.datetime.strftime(dt.datetime.now(), '%Y%m%d')


# FUNCTION TO PULL TABLE FROM DB
def pull_table(conn, name):
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



