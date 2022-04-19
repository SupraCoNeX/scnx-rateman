# -*- coding: utf-8 -*-
r"""
Errors Module
-------------------
This module provides a collection of functions that categorize errors in
data files and processes data files to produce cleaner data files that can be
used for analysis.
"""

__all__ = [
    "process_line",
    "check_line_txs",
    "update_pckt_count_txs",
    "check_line_rcstats",
    "update_pckt_count_rcs",
    "check_line_rxs",
    "check_line_sta_add",
    "get_sta_info",
    "check_line_sta_remove",
    "check_line_group_idx",
    "get_group_idx_info",
    "check_line_probe",
]


def process_line(ap_handle, data_line):

    if data_line.find("group"):
        print(check_line_group_idx(data_line))
        print(data_line)
        if check_line_group_idx(data_line):
            group_idx, max_offset = get_group_idx_info(data_line)
            ap_handle.add_supp_rates(group_idx, max_offset)

    elif data_line.find("txs"):
        if check_line_txs(data_line):
            update_pckt_count_txs(data_line, ap_handle)

    elif data_line.find("stats"):
        if check_line_rcstats(data_line):
            update_pckt_count_rcs(data_line, ap_handle)

    elif data_line.find("rxs"):
        if check_line_rxs(data_line):
            pass

    elif data_line.find("sta;add;"):
        if check_line_sta_add(data_line):
            sta_info = get_sta_info(data_line)
            ap_handle.add_station(sta_info)

    elif data_line.find("sta;remove;"):
        if check_line_sta_remove(data_line):
            ap_handle.remove_station(sta_info)
        pass

    elif data_line.find("probe;"):
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
    """


    Parameters
    ----------
    data_line : TYPE
        DESCRIPTION.
    ap_handle : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """

    fields = data_line.split(sep=";")
    radio = fields[0]
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

    atmpts = [atmpts1, atmpts2, atmpts3, atmpts4]

    succ = [0, 0, 0, 0]

    suc_rate_ind = 3
    for atmpt_ind, atmpt in enumerate(atmpts):
        if atmpt == 0:
            suc_rate_ind = atmpt_ind - 1

    if suc_rate_ind < 0:
        suc_rate_ind = 0

    succ[suc_rate_ind] = num_ack

    rates = [rate_ind1, rate_ind2, rate_ind3, rate_ind4]

    line_dict = {}

    for rate_ind, rate in enumerate(rates):
        if rate != "ffff":
            if rate not in list(line_dict.keys()):
                line_dict[rate] = {}
            line_dict[rate]["attempts"] += atmpts[rate_ind]
            line_dict[rate]["success"] += succ[rate_ind]
            line_dict[rate]["timestamp"] = timestamp

    ap_handle.sta_list_active[radio][mac_addr].update_stats(line_dict)


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


def update_pckt_count_rcs(data_line, ap_handle):
    """


    Parameters
    ----------
    line : TYPE
        DESCRIPTION.
    rcstats : TYPE
        DESCRIPTION.

    Returns
    -------
    line_dict : TYPE
        DESCRIPTION.
    rcstats : TYPE
        DESCRIPTION.

    """

    fields = data_line.split(sep=";")
    radio = fields[0]
    timestamp = fields[1]
    mac_addr = fields[3]
    rate = fields[4]
    cur_succ = fields[7]
    cur_atmpts = fields[8]
    hist_succ = fields[9]
    hist_atmpts = fields[10]

    line_dict = {
        "timestamp": timestamp,
        "cur_attempts": int(cur_atmpts, 16),
        "cur_success": int(cur_succ, 16),
        "hist_attempts": int(hist_atmpts, 16),
        "hist_success": int(hist_succ, 16),
    }

    pass


def check_line_rxs(data_line):
    """


    Parameters
    ----------
    data_line : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    pass


def check_line_sta_add(data_line):
    """

    Parameters
    ----------
    line : str
        Single trace line. Expected to either contain 'txs' or 'rcs' trace
        information. Check if the line contains 'txs' or 'rcs' should be
        done prior to using this function.
    Returns
    -------
    valid_sta_add : bool
        True if number of fields in string line equals expected number of fields.
        False otherwise.
    """

    valid_sta_add = True

    return valid_sta_add


def get_sta_info(data_line):
    """


    Parameters
    ----------
    data_line : TYPE
        DESCRIPTION.

    Returns
    -------
    sta_info : TYPE
        DESCRIPTION.

    """

    sta_info = {}
    fields = data_line.split(sep=";")
    sta_info["radio"] = fields[0]
    sta_info["timestamp"] = fields[1]
    sta_info["mac_addr"] = fields[4]
    sta_info["sup_rates"] = ""

    return sta_info


def check_line_sta_remove(data_line):

    if data_line.find(";sta;remove"):
        return True
    else:
        return False


def check_line_group_idx(data_line):
    """


    Parameters
    ----------
    data_line : TYPE
        DESCRIPTION.

    Returns
    -------
    bool
        DESCRIPTION.

    """

    if data_line.find(";group;"):
        return True
    return False


def get_group_idx_info(data_line):
    """


    Parameters
    ----------
    data_line : TYPE
        DESCRIPTION.

    Returns
    -------
    group_idx : TYPE
        DESCRIPTION.
    max_offset : TYPE
        DESCRIPTION.

    """

    fields = data_line.split(";")
    print(data_line)
    group_idx = fields[3]
    offset = fields[4]

    max_offset = offset[:-1] + str(len(fields[9:]) - 1)

    return group_idx, max_offset


def check_line_probe(data_line):
    """


    Parameters
    ----------
    data_line : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    pass
