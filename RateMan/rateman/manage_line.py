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
    "check_line_txs",
    "check_line_rcstats",
    "check_timestamp",
    "obtain_data_flags",
]


def process_line(ap_handle, data_line):

    param_column = 22

    if data_line.find("txs") == param_column:
        if check_line_txs(data_line):
            update_pckt_count_txs(data_line, ap_handle)

    elif data_line.find("stats") == param_column:
        if check_line_rcstats(data_line):
            update_pckt_count_rcs(data_line, ap_handle)

    elif data_line.find("rxs") == param_column:
        if check_line_rxs(data_line):
            pass

    elif data_line.find("sta;add;") == param_column:
        if check_line_sta_add(data_line):
            update_ap_info(data_line, ap_handle)

    elif data_line.find("sta;remove;") == param_column:
        if check_line_sta_remove(data_line):
            update_ap_info(data_line, ap_handle)

    elif data_line.find("probe;") == param_column:
        if check_line_probe(data_line):
            pass


def check_line_txs(line: str):
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

    exp_num_fields = 15
    num_elem = 2
    fields = line.split(sep=";")

    valid_txs = False

    if (
        line.find("*") == -1
        and line.find("txs") != -1
        and exp_num_fields == len(fields)
    ):
        for ii in range(7, 11, 1):
            if len(fields[ii].split(",")) == num_elem:
                valid_txs = True

    return valid_txs


def update_pckt_count_txs(data_line, ap_handle):

    fields = data_line.split(sep=";")
    radio_txs = fields[0]
    timestamp = fields[1]
    mac_addr = fields[3]
    num_frames = int(fields[4], 16)
    num_ack = int(fields[5], 16)
    probe_flag = int(fields[6], 16)
    rate_ind1 = fields[7]
    rate_ind2 = fields[9]
    rate_ind3 = fields[11]
    rate_ind4 = fields[13]

    count1 = int(fields[8], 16)
    count2 = int(fields[10], 16)
    count3 = int(fields[12], 16)
    count4 = int(fields[14], 16)

    atmpts1 = num_frames * count1
    atmpts2 = num_frames * count2
    atmpts3 = num_frames * count3
    atmpts4 = num_frames * count4

    atmpts = np.array([atmpts1, atmpts2, atmpts3, atmpts4])

    succ = np.array([0, 0, 0, 0])

    try:
        suc_rate_ind = np.where(atmpts == 0)[0][0] - 1
    except:
        suc_rate_ind = 3
    if suc_rate_ind < 0:
        suc_rate_ind = 0

    succ[suc_rate_ind] = num_ack

    rates = np.array([rate_ind1, rate_ind2, rate_ind3, rate_ind4])

    line_dict = {}

    for rate in rates:
        rateind = np.where(rates == rate)[0]
        if rate != "ffff":
            line_dict[rate] = {}
            line_dict[rate]["attempts"] = np.sum(atmpts[rateind])
            line_dict[rate]["success"] = np.sum(succ[rateind])

    ap_handle.sta_list_active[mac_addr].update_stats(line_dict)


def check_line_rcstats(line: str):
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

    exp_num_fields = 11
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
