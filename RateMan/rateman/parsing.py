# -*- coding: utf-8 -*-

import logging
import station

__all__ = [
    "process_line",
    "update_pckt_count_txs",
    "update_pckt_count_rcs",
    "check_line_sta_add",
    "parse_sta",
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
        if fields[3] in ["add", "dump"]:
            ap.add_station(parse_sta(ap, fields))
    elif fields[2] == "sta" and fields[3] == "remove" and len(fields) == 8:
        ap.remove_station(fields[4], fields[0])

def update_pckt_count_txs(ap, fields):
    radio = fields[0]
    mac_addr = fields[3]

    try:
        sta = ap.stations()[mac_addr]
    except KeyError:
        return

    timestamp = fields[1]
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
    rates = [f"0{rate}" if len(rate) == 1 else rate for rate in rates]
    info = {}

    for rate_ind, rate in enumerate(rates):
        if rate != "ffff":
            if rate not in info:
                info[rate] = {}
                if sta.check_rate_entry(rate):
                    info[rate]["attempts"] = sta.get_attempts(rate)
                    info[rate]["success"] = sta.get_successes(rate)
                else:
                    info[rate]["attempts"] = 0
                    info[rate]["success"] = 0

            info[rate]["attempts"] += atmpts[rate_ind]
            info[rate]["success"] += succ[rate_ind]

    sta.update_stats(timestamp, info)

def update_pckt_count_rcs(ap, fields):
    # TODO: what about this?
    pass
    # radio = fields[0]
    # timestamp = fields[1]
    # mac_addr = fields[3]

    # sta = ap.get_sta(mac_addr, radio)
    # if not sta:
    #     logging.warn(f"Unexpected rc stats for unknown MAC {mac_addr}")
    #     return
    
    # sta.update_stats(
    #     timestamp,
    #     {
    #         fields[4]: {
    #             "cur_attempts": int(fields[8], 16),
    #             "cur_success": int(fields[7], 16),
    #             "hist_attempts": int(fields[10], 16),
    #             "hist_success": int(fields[9], 16),
    #         }
    #     }
    # )

def parse_sta(ap, fields):
    supp_rates = []
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
                supp_rates += [f"{offset[:-1]}{i}" for i in range(no_supp_rates)]

    sta = station.Station(fields[0], fields[4], supp_rates, fields[1])

    return sta

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
