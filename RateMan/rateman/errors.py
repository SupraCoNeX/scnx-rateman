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
import linecache

__all__ = [
    "get_error_stats",
    "flag_error_in_data",
    "obtain_data_flags",
    "check_trace_txs",
    "check_trace_rcs",
    "check_timestamp",
]


def _skip_ap_info_lines(df):
    """Return dataframe without the ap_info lines."""

    ap_info_len = df.loc[df["timestamp2"] == "group"].index[-1]
    phy_len = df["phy_nr"].unique().size
    df_data = df.iloc[ap_info_len + phy_len :]
    return df_data


def _interpolate_error_timestamps(timestamps, ns=False, error_interval=1000):
    """Interpolate error timestamp.
    # TODO: Improve timestamp interpolation
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
                for c in range(1, counter + 1):
                    ts[i - c] = int(t) - c
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
                for j in range(1, counter + 1):
                    ts[i - j] = int(t) - j
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
                    for j in range(1, counter + 1):
                        ts[i - j] = int(t) - j
                    running_flag = True
                    last_valid = i
                    counter = 0
                    ts_errors.append(False)
                elif 0 <= diff <= error_interval:
                    ts.append(int(t))
                    step_width = diff / (counter + 1)
                    for j in range(1, counter + 1):
                        ts[i - j] = int(int(t) - j * step_width)
                    running_flag = True
                    last_valid = i
                    counter = 0
                    ts_errors.append(False)
        elif pd.notna(t) and t.isnumeric():
            if ns:
                ts.append(int(t))
                step_width = (int(t) - int(timestamps.iloc[last_valid])) / (counter + 1)
                for j in range(1, counter + 1):
                    ts[i - j] = int(int(t) - j * step_width)
                counter = 0
                last_valid = i
                ts_errors.append(False)
            elif (
                np.abs(int(t) - int(timestamps.iloc[last_valid])) <= error_interval
                and not ns
            ):
                ts.append(int(t))
                step_width = (int(t) - int(timestamps.iloc[last_valid])) / (counter + 1)
                for j in range(1, counter + 1):
                    ts[i - j] = int(int(t) - j * step_width)
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
    # TODO: Check if it really does what it should
    ts = [
        datetime.fromtimestamp(float(str(i1) + "." + str(i2)))
        for i1, i2 in df_error.index
    ]
    return ts


def _get_missing_rate_errors(df):
    """Return a pandas series with missing rate errors of the txs dataframe."""
    txs_columns = [
        "phy_nr",
        "type",
        "macaddr",
        "num_frames",
        "num_acked",
        "probe",
        "rate_count1",
        "rate_count2",
        "rate_count3",
        "rate_count4",
    ]
    # Check if the given dateframe is a txs dataframe.
    if (df.columns == txs_columns).all():
        res = (df.loc[:, "rate_count1":] == "0,0").all(axis="columns")
    else:
        raise ValueError
    return res


def _get_invalid_type_errors(df):
    """Returns a list with bool values for invalid types in trace lines."""
    valid_types = ["txs", "stats", "group", "sta", "rates", "probe"]
    hlp = df["type"] in valid_types
    return hlp


def get_error_stats(df_error):
    """Get error statistics of txs and stats data, e.g. number of trace lines,
    number of timestamp error lines, number of parsing error lines.
    """

    lines = df_error.shape[0]
    lines_timestamp_error = np.sum(df_error.timestamp_error)
    lines_parsing_error = np.sum(df_error.parsing_error)

    return lines, lines_timestamp_error, lines_parsing_error


def flag_error_in_data(stats_df):
    """
    Identify different errors in provided data in the form of dataframe.

    Parameters
    ----------
    stats_df : pandas dataframe
        txs dataframe or rcs dataframe.

    Returns
    -------
    df_data : TYPE
        DESCRIPTION.

    """

    # add error flags

    # Find timestamp errors
    ts_new, ts_error = _interpolate_error_timestamps(stats_df.timestamp_ns)

    stats_df.loc[:, "timestamp_ns"] = ts_new
    stats_df.loc[ts_error, "timestamp_error"] = True

    # ts_new2, ts_error2 = _interpolate_error_timestamps(stats_df.timestamp2, True)
    # stats_df.loc[:, 'timestamp2'] = ts_new2
    # stats_df.loc[ts_error2, 'timestamp_error'] = True
    # stats_df = stats_df.set_index(["timestamp", "timestamp2"])

    return stats_df


def check_trace_txs(line: str):
    """
    Check if a given txs trace data line contains the expected number of
    data fields.

    Parameters
    ----------
    line : str
        Single trace line. Expected to either contain 'txs' or 'rcs' trace
        information. Check if the line contains 'txs' or 'rcs' should be
        done prior to using this function.

    Returns
    -------
    valid_txs : bool
        True if number of fields in string line equals expected number of fields.
        False otherwise.

    """

    exp_num_fields = 12
    num_elem = 2
    fields = line.split(sep=";")

    valid_txs = False

    if (
        line.find("*") == -1
        and line.find("txs") != -1
        and exp_num_fields == len(fields)
    ):
        for ii in range(8, 12, 1):
            if len(fields[ii].split(",")) == num_elem:
                valid_txs = True

    return valid_txs


def check_trace_rcs(line: str):
    """
    Check if a given txs trace data line contains the expected number of
    data fields.

    Parameters
    ----------
    line : str
        Single trace line. Expected to either contain 'txs' or 'rcs' trace
        information. Check if the line contains 'txs' or 'rcs' should be
        done prior to using this function.

    Returns
    -------
    valid_txs : bool
        True if number of fields in string line equals expected number of fields.
        False otherwise.

    """

    exp_num_fields = 12
    fields = line.split(sep=";")
    if (
        line.find("*") == -1
        and line.find("stats") != -1
        and exp_num_fields == len(fields)
    ):

        valid_rcs = True
    else:
        valid_rcs = False

    return valid_rcs


def check_timestamp(line: str, latest_timestamp: int):
    """
    Add docum

    Parameters
    ----------
    line : str
        DESCRIPTION.
    latest_timestamp : int
        DESCRIPTION.

    Returns
    -------
    valid_timestamp : TYPE
        DESCRIPTION.

    """
    fields = line.split(sep=";")
    if int(fields[1] + fields[2]) > latest_timestamp:
        valid_timestamp = True
    else:
        valid_timestamp = False

    return valid_timestamp


def obtain_data_flags(filename: dir):
    """
    Obtain dataframe with flags denoting validity lines in a given data file.
    A line is termed valid if it contains 'txs' or 'rcs' informations, contains
    expected number of data fields, and has a timestamp greater than the
    previous valid line.

    Parameters
    ----------
    filename : dir
        File path of collected data.

    Returns
    -------
    stat_df : pandas.dataframe
        Dataframe with fields denoting if a give line is a statistical trace
        i.e. containing 'txs' or 'rcs' information , if it contains the expected
        number of fields, and has a valid timestamp.

    """

    latest_timestamp = 0

    num_lines = sum(1 for line in open(filename, mode="r"))
    stat_array = np.empty((num_lines, 3), dtype=int)

    for ii in range(num_lines):
        line = linecache.getline(filename, ii)

        if check_trace_txs(line) or check_trace_rcs(line):
            stats_field = 1
            valid_trace_flag = 1
        else:
            stats_field = 0
            valid_trace_flag = 0

        if stats_field == 1 and check_timestamp(line, latest_timestamp):
            timestamp_flag = 1
            latest_timestamp = int(line.split(sep=";")[1] + line.split(sep=";")[2])
        else:
            timestamp_flag = 0

        stat_array[ii, :] = [stats_field, valid_trace_flag, timestamp_flag]

    stat_df = pd.DataFrame(
        stat_array,
        columns=[
            "stats_field",
            "num_fields_flag",
            "timestamp_flag",
        ],
    )

    return stat_df
