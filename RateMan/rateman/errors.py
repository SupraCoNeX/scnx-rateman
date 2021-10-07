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
import linecache

__all__ = [
    "check_trace_txs",
    "check_trace_rcs",
    "check_timestamp",
    "obtain_data_flags"
]


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
