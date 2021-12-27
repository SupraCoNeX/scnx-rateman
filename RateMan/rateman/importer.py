# -*- coding: utf-8 -*-
r"""
Importer Module
-------------------

This module provides a collection of functions to import collected data.
>TODO: extend description

"""

import io
from pathlib import Path
import pandas as pd
import linecache
import numpy as np
from .errors import *


__all__ = ["obtain_txs_df", "obtain_rcs_df", "obtain_timestamps_df", "obtain_rates", "obtain_file_start", "obtain_file_end"]


class DebugException(Exception):
    pass


def obtain_file_start(filename: str) -> int:
    """
    Obtain the starting line number for txs information in a given file.

    Parameters
    ----------
    filename : str
        Directory location of data file.

    Returns
    -------
    txs_line_start : int

    """
    num_lines = sum(1 for line in open(filename, mode="r"))

    txs_line_start = 0

    for ii in range(num_lines):
        line = linecache.getline(filename, ii)
        if check_trace_rcs(line) and ii != num_lines:
            next_line = linecache.getline(filename, ii + 1)
            if check_trace_txs(next_line):
                txs_line_start = ii + 1
                break

    return txs_line_start


def obtain_file_end(filename: str) -> int:
    """
    Obtain the end line number for txs information in a given file. We
    consider statistical data only until this line.

    Parameters
    ----------
    filename : str
        Directory location of data file.


    Returns
    -------
    txs_line_end: int

    """
    num_lines = sum(1 for line in open(filename, mode="r"))

    txs_line_end = num_lines

    for ii in range(num_lines, -1, -1):
        line = linecache.getline(filename, ii)
        if check_trace_txs(line) and ii != 1:
            previous_line = linecache.getline(filename, ii - 1)
            if check_trace_rcs(previous_line):
                txs_line_end = ii - 1
                break

    return txs_line_end





def _obtain_valid_txs_line_ind(filename: dir):

    num_lines = sum(1 for line in open(filename, mode="r"))
    valid_line_ind = []

    for ii in range(num_lines):
        line = linecache.getline(filename, ii)

        if check_trace_txs(line):
            valid_line_ind.append(ii)

    return valid_line_ind


def _obtain_valid_rcs_line_ind(filename: dir):

    num_lines = sum(1 for line in open(filename, mode="r"))
    valid_line_ind = []

    for ii in range(num_lines):
        line = linecache.getline(filename, ii)

        if check_trace_rcs(line):
            valid_line_ind.append(ii)

    return valid_line_ind


def _obtain_valid_group_line_ind(filename: dir):

    num_lines = sum(1 for line in open(filename, mode="r"))
    valid_line_ind = []

    for ii in range(num_lines):
        line = linecache.getline(filename, ii)
        fields = line.split(sep=";")
        if line.find("*;0;group;") != -1:
            valid_line_ind.append(ii)

    return valid_line_ind


def _obtain_valid_stat_line_ind(filename: dir):
    """


    Parameters
    ----------
    filename : dir
        DESCRIPTION.

    Returns
    -------
    valid_line_ind : TYPE
        DESCRIPTION.

    """

    num_lines = sum(1 for line in open(filename, mode="r"))
    valid_line_ind = []

    for ii in range(num_lines):
        line = linecache.getline(filename, ii)

        if check_trace_txs or check_trace_rcs:
            valid_line_ind.append(ii)

    return valid_line_ind


def obtain_txs_df(filename: str):
    """


    Parameters
    ----------
    filename : str
        DESCRIPTION.

    Returns
    -------
    txs_df : TYPE
        DESCRIPTION.

    """

    valid_line_ind = _obtain_valid_txs_line_ind(filename)
    txs_array = np.empty((len(valid_line_ind), 15), dtype="<U21")

    for ii in range(len(valid_line_ind)):
        line = linecache.getline(filename, valid_line_ind[ii])

        fields = line.split(sep=";")

        timestamp_ns = int(fields[1] + fields[2])
        mac_addr = fields[4]
        num_frames = int(fields[5], 16)
        num_ack = int(fields[6], 16)
        probe = fields[7]
        rate_ind1 = fields[8].split(sep=",")[0]
        rate_ind2 = fields[9].split(sep=",")[0]
        rate_ind3 = fields[10].split(sep=",")[0]
        rate_ind4 = fields[11].split(sep=",")[0]

        count1 = int(fields[8].split(sep=",")[1], 16)
        count2 = int(fields[9].split(sep=",")[1], 16)
        count3 = int(fields[10].split(sep=",")[1], 16)
        count4 = int(fields[11].strip().split(sep=",")[1], 16)

        attempts = sum(num_frames * list(map(int, [count1, count2, count3, count4])))

        txs_array[ii, :] = [
            timestamp_ns,
            mac_addr,
            num_frames,
            num_ack,
            probe,
            rate_ind1,
            count1,
            rate_ind2,
            count2,
            rate_ind3,
            count3,
            rate_ind4,
            count4,
            attempts,
            num_ack,
        ]

    txs_df = pd.DataFrame(
        txs_array,
        columns=[
            "timestamp_ns",
            "mac_addr",
            "num_frames",
            "num_ack",
            "probe",
            "rate_ind1",
            "count1",
            "rate_ind2",
            "count2",
            "rate_ind3",
            "count3",
            "rate_ind4",
            "count4",
            "attempts",
            "success",
        ],
    )

    return txs_df


def obtain_rcs_df(filename: str):
    """


    Parameters
    ----------
    filename : str
        DESCRIPTION.

    Returns
    -------
    rcs_df : TYPE
        DESCRIPTION.

    """

    valid_line_ind = _obtain_valid_rcs_line_ind(filename)

    rcs_array = np.empty((len(valid_line_ind), 10), dtype="<U21")

    for ii in range(len(valid_line_ind)):
        line = linecache.getline(filename, valid_line_ind[ii])

        fields = line.split(sep=";")

        phy = fields[0]
        timestamp_ns = int(fields[1] + fields[2])
        mac_addr = fields[4]
        rate = fields[5]
        avg_prob = fields[6]
        avg_tp = fields[7]
        cur_success = fields[8]
        cur_attempts = fields[9]
        hist_success = fields[10]
        hist_attempts = fields[11]

        rcs_array[ii, :] = [
            phy,
            timestamp_ns,
            mac_addr,
            rate,
            avg_prob,
            avg_tp,
            cur_success,
            cur_attempts,
            hist_success,
            hist_attempts,
        ]

    rcs_df = pd.DataFrame(
        rcs_array,
        columns=[
            "phy",
            "timestamp_ns",
            "mac_addr",
            "rate",
            "avg_prob",
            "avg_tp",
            "cur_success",
            "cur_attempts",
            "hist_success",
            "hist_attempts",
        ],
    )

    return rcs_df


def obtain_timestamps_df(filename: str):
    """


    Parameters
    ----------
    filename : str
        DESCRIPTION.

    Returns
    -------
    timestamp_df : TYPE
        DESCRIPTION.

    """
    
    traceline_start = obtain_file_start(filename)
    traceline_end = obtain_file_end(filename)
    timestamps = []
    
    for ii in range(traceline_start, traceline_end + 1, 1):
        line = linecache.getline(filename, ii)
        
        if check_trace_txs(line) or check_trace_rcs(line):
            fields = line.split(sep=";")    
            timestamp = int(fields[1],16)
            timestamps.append(timestamp)

    return timestamps


def obtain_rates(filename: str):
    """


    Parameters
    ----------
    filename : str
        DESCRIPTION.

    Returns
    -------
    None.

    """

    valid_line_ind = _obtain_valid_group_line_ind(filename)

    rates = []

    for ii in range(len(valid_line_ind)):
        line = linecache.getline(filename, valid_line_ind[ii])
        fields = line.split(sep=";")
        rate_index = fields[3]
        rate_airtimes = fields[9].strip("\n").split(",")
        for jj in range(len(rate_airtimes)):
            if rate_index == "0":
                cur_rate = str(jj)
            else:
                cur_rate = rate_index + str(jj)
            if cur_rate not in rates:
                rates.append(cur_rate)

    return np.array(rates)
