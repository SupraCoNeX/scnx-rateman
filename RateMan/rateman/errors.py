# -*- coding: utf-8 -*-
r"""
Errors Module
-------------------

This module provides a collection of functions that categorize errors in
data files and processes data files to produce cleaner data files that can be
used for analysis. 

"""
import pandas as pd
import numpy as np
import datetime
from pandas.io.parsers import read_csv


__all__ = ["get_error_stats", "flag_error_in_data"]


def _skip_ap_info_lines(df):
    """Return dataframe without the ap_info lines."""
    
    ap_info_len = df.loc[df['timestamp2'] == 'group'].index[-1]
    phy_len = df['phy_nr'].unique().size
    df_data = df.iloc[ap_info_len+phy_len:]
    return df_data

def _interpolate_error_timestamps(timestamps, ns=False, error_interval=1000):
    """Interpolate error timestamp.
    #TODO: Improve timestamp interpolation
    """
    ts = []
    ts_errors = []
    first_entry = True
    running_flag = False
    last_valid = 0
    counter = 0
    timestamps = timestamps.astype(str)
    
    for i, t in enumerate(timestamps):
        # Special case: 1st entry
        # Wait until receiving a valid timestamp but could be not correct
        # Therefore, there is the `running_flag` which should detect the wrong
        # first timestamp
        if first_entry:
            if pd.notna(t) and t.isnumeric():
                ts.append(int(t))
                for c in range(1, counter+1):
                    ts[i-c] = int(t)-c
                first_entry = False
                last_valid = i
                counter = 0
                ts_errors.append(False)
            else:
                ts.append(pd.NA)
                counter += 1
                ts_errors.append(True)
        elif not running_flag and pd.notna(t) and t.isnumeric():
            diff = int(t) - int(timestamps.iloc[last_valid])
            if ns:
                ts.append(int(t))
                for j in range(1, counter+1):
                    ts[i-j] = int(t)-j
                counter = 0
                last_valid = i
                ts_errors.append(False)
            else:
                if diff < 0:
                    ts.append(pd.NA)
                    counter += 1
                    ts_errors.append(True)
                elif diff > error_interval:
                    ts.append(int(t))
                    for j in range(1, counter+1):
                        ts[i-j] = int(t)-j
                    running_flag = True
                    last_valid = i
                    counter = 0
                    ts_errors.append(False)
                elif 0 <= diff <= error_interval:
                    ts.append(int(t))
                    step_width = diff/(counter+1)
                    for j in range(1, counter+1):
                        ts[i-j] = int(int(t) - j * step_width)
                    running_flag = True
                    last_valid = i
                    counter = 0
                    ts_errors.append(False)
        elif pd.notna(t) and t.isnumeric():
            if ns:
                ts.append(int(t))
                step_width = (int(t) - int(timestamps.iloc[last_valid])) / (counter + 1)
                for j in range(1, counter+1):
                    ts[i-j] = int(int(t) - j * step_width)
                counter = 0
                last_valid = i
                ts_errors.append(False)
            elif np.abs(int(t) - int(timestamps.iloc[last_valid])) <= error_interval and not ns:
                ts.append(int(t))
                step_width = (int(t) - int(timestamps.iloc[last_valid])) / (counter + 1)
                for j in range(1, counter+1):
                    ts[i-j] = int(int(t) - j * step_width)
                last_valid = i
                counter = 0
                ts_errors.append(False)
            else:
                ts.append(pd.NA)
                counter += 1
                ts_errors.append(True)
        else:
            ts.append(pd.NA)
            counter += 1
            ts_errors.append(True)
    return ts, ts_errors

def _get_timestamp_errors(df_error):
    """Find errors in timestamps and flag them."""
    #TODO: Check if it really does what it should
    ts = [
        datetime.fromtimestamp(
            float(str(i1)+"."+str(i2))
        ) for i1, i2 in df_error.index
    ]
    return ts

def _get_missing_rate_errors(df):
    """Return a pandas series with missing rate errors of the txs dataframe.
    """
    txs_columns = [
        'phy_nr',
        'type',
        'macaddr',
        'num_frames',
        'num_acked',
        'probe',
        'rate_count1',
        'rate_count2',
        'rate_count3',
        'rate_count4'
    ]
    # Check if the given dateframe is a txs dataframe.
    if (df.columns == txs_columns).all():
        res = (df.loc[:, 'rate_count1':] == '0,0').all(axis='columns')
    else:
        raise ValueError
    return res

def _get_invalid_type_errors(df):
    """Returns a list with bool values for invalid types in trace lines."""
    valid_types = [
        'txs',
        'stats',
        'group',
        'sta',
        'rates',
        'probe'
    
    ]
    hlp = df['type'] in valid_types 
    return hlp


def get_error_stats(df_error):
    """Get error statistics of txs and stats data, e.g. number of trace lines,
    number of timestamp error lines, number of parsing error lines.
    """
    
    lines = df_error.shape[0]
    lines_timestamp_error = np.sum(df_error.timestamp_error)
    lines_parsing_error = np.sum(df_error.parsing_error)
    
    
    return lines, lines_timestamp_error, lines_parsing_error

def flag_error_in_data(file):
    
    """Flag error lines in traces. There are timestamp errors and parsing errors
    if they are not timestamp errors.
    """
    df = read_csv(file, sep=';', names=range(14))
    df.columns = [
        "phy_nr",
        "timestamp",
        "timestamp2",
        "type",
        "macaddr",
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        "parsing_error",
        "timestamp_error",
    ]
    # Skip ap_info lines
    df_data = _skip_ap_info_lines(df)
    
    # Find timestamp errors
    ts_new, ts_error = _interpolate_error_timestamps(df_data.timestamp)
    
    df_data.loc[:, 'timestamp'] = ts_new
    df_data.loc[ts_error, 'timestamp_error'] = True
    
    ts_new2, ts_error2 = _interpolate_error_timestamps(df_data.timestamp2, True)
    df_data.loc[:, 'timestamp2'] = ts_new2
    df_data.loc[ts_error2, 'timestamp_error'] = True
    df_data = df_data.set_index(["timestamp", "timestamp2"])
    
    return df_data
