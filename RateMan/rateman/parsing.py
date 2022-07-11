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
    "update_pckt_count_txs",
    "update_pckt_count_rcs",
    "check_line_sta_add",
    "get_sta_info",
    "get_group_idx_info",
]

def process_api(ap, fields):
    if len(fields) < 4:
        return

    line_type = fields[2]

    if line_type == "group":
        # process_rate_group(ap, fields) TODO
        pass

def parse_group(fields):
    group_idx = fields[3]
    max_offset = offset[:-1] + str(len(fields[9:]) - 1)

    return group_idx, max_offset

def process_line(ap, line):
    fields = line.rstrip("\n").split(";")

    if len(fields) < 3:
        return

    if line[0] == "*":
        process_api(ap, fields)
        return

    if fields[1] == "0" and len(fields) == 3 and fields[2] == "add":
        ap.add_phy(fields[0])
        return

    if fields[2] == "group" and len(fields) == 19:
        idx, max_offset = parse_group(fields)
        ap.add_supp_rates(idx, max_offset)
    elif fields[2] == "txs" and len(fields) == 15:
        update_pckt_count_txs(ap, fields)
    elif fields[2] == "stats" and len(fields) == 11:
        update_pckt_count_rcs(ap, fields)
    elif fields[2] == "rxs" and len(fields) == 9:
        # TODO
        pass
    elif fields[2] == "sta" and len(fields) == 49:
        sta_info = get_sta_info(ap, fields)
        if fields[3] == "add":
            ap.add_station(sta_info)
        elif fields[3] == "remove":
            ap.remove_station(sta_info)

def update_pckt_count_txs(ap, fields):
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
            break

    if suc_rate_ind < 0:
        suc_rate_ind = 0

    succ[suc_rate_ind] = num_ack
    rates = [rate_ind1, rate_ind2, rate_ind3, rate_ind4]
    rates = ["0" + rate if len(rate) == 1 else rate for rate in rates]
    line_dict = {}
    sta_obj = ap.sta_list_active[radio][mac_addr]

    for rate_ind, rate in enumerate(rates):
        if rate != "ffff":
            if rate not in list(line_dict.keys()):
                line_dict[rate] = {}
                if sta_obj.check_rate_entry(rate):
                    line_dict[rate]["attempts"] = sta_obj.get_attempts(rate)
                    line_dict[rate]["success"] = sta_obj.get_successes(rate)
                else:
                    line_dict[rate]["attempts"] = 0
                    line_dict[rate]["success"] = 0

            line_dict[rate]["attempts"] += atmpts[rate_ind]
            line_dict[rate]["success"] += succ[rate_ind]
            line_dict[rate]["timestamp"] = timestamp

    ap.sta_list_active[radio][mac_addr].update_stats(line_dict)

def update_pckt_count_rcs(ap, fields):
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

    # TODO

def get_sta_info(ap, fields):
    sta_info = {
        "radio": fields[0],
        "timestamp" : fields[1],
        "mac_addr" : fields[4],
        "supp_rates": []
    }

    rates_flag = fields[7:]

    for i, (groupIdx, max_offset) in enumerate(ap.supp_rates.items()):
        # Only works for all masks with ff at the end, eg. 1ff, 3ff, ff
        if "ff" in rates_flag[i]:
            dec_mask = int(rates_flag[i], base=16)
            bin_mask = str(bin(dec_mask))[2:]
            no_supp_rates = bin_mask.count("1")
            offset = groupIdx + "0"
            no_rates = int(max_offset[-1]) + 1

            # Making sure no of 1s in bit mask isn't greater than rates in that group index
            if no_supp_rates <= no_rates:
                sta_info["supp_rates"] += [
                    offset[:-1] + str(i) for i in range(no_supp_rates)
                ]

    return sta_info

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
    fields = list(filter(None, fields))
    group_idx = fields[3]
    offset = fields[4]

    max_offset = offset[:-1] + str(len(fields[9:]) - 1)

    return group_idx, max_offset
