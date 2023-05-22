# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Parsing Rate Control API Output Lines
-------------------------------------

This is the main processing module that provides functions to asynchronously 
monitor network status and set rates.

"""
import asyncio
from .station import Station

__all__ = ["process_api", "process_line", "process_header", "parse_sta"]


# utility function to parse signed integers from hex strings in two's complement format
def twos_complement(hexstr, bits):
    val = int(hexstr, 16)
    return val - (1 << bits) if val & (1 << (bits - 1)) else val


parse_s16 = lambda s: twos_complement(s, 16)
parse_s32 = lambda s: twos_complement(s, 32)


def process_api(ap, fields):
    if len(fields) < 4:
        return

    line_type = fields[2]

    if line_type == "group":
        group_ind, group_info = parse_group_info(fields)
        ap.add_supp_rates(group_ind, group_info)
    elif line_type == "sample_table":
        ap.sample_table = fields[5:]


async def process_header(ap):
    try:
        async for data in ap:
            try:
                line = data.decode("utf-8").rstrip()
                fields = line.split(";")
                if fields[0] == "*":
                    if fields[2] == "#error":
                        ap.handle_error(fields[3])
                    process_api(ap, fields)
                elif "0;add" in line:
                    process_phy_info(ap, fields)
                else:
                    return
            except (UnicodeError, ValueError):
                continue
    except (IOError, ConnectionError):
        ap.connected = False
        ap._logger.error(f"Disconnected from {ap.name}: {e}")
    except (asyncio.CancelledError, TimeoutError):
        return


async def get_next_line(ap, timeout):
    data = await asyncio.wait_for(await anext(ap), timeout=timeout)

    if data == "":
        ap.connected = False
        self._logger.error(f"Disconnected from {ap.name}")
        return None

    return data.decode("utf-8").rstrip()


def parse_group_info(fields):
    """
    Obtain maximum offset for a given MCS rate group available for an AP.

    Parameters
    ----------
    fields : list
                                    Fields obtained by spliting a data line received from the AP
                                    over the Rate Control API.

    Returns
    -------
    group_idx : str
                                    Index of MCS rate group.
    max_offset : str
                                    Maximum allowable offset - determines which rates are available
                                    in the group for the AP.

    """
    fields = list(filter(None, fields))
    group_ind = fields[3]

    airtimes_hex = fields[9:]
    rate_offsets = [str(ii) for ii in range(len(airtimes_hex))]
    rate_inds = list(map(lambda jj: group_ind + jj, rate_offsets))
    airtimes_ns = [int(ii, 16) for ii in airtimes_hex]

    group_info = {
        "rate_inds": rate_inds,
        "airtimes_ns": airtimes_ns,
        "type": fields[5],
        "nss": fields[6],
        "bandwidth": fields[7],
        "guard_interval": fields[8],
    }

    return group_ind, group_info


def process_phy_info(ap, fields):
    ap.add_radio(fields[0], fields[3])
    if len(fields) > 4:
        for iface in fields[4].split(","):
            ap.add_interface(fields[0], iface)

    return True


def process_line(ap, line):
    """

    Execute respective functions based on the trace line received from the AP.

    Parameters
    ----------
    ap : AccessPoint object

    line : str
                                    Trace line.

    """

    fields = validate_line(ap, line)

    if not fields:
        return None, None

    line_type = fields[2]

    if line_type == "txs":
        update_pckt_count_txs(ap, fields)
    elif line_type == "rxs":
        sta = ap.get_sta(fields[3], radio=fields[0])
        if sta:
            sta.update_rssi(
                int(fields[1], 16),
                parse_s32(fields[4]),
                [parse_s32(r) for r in fields[5:]],
            )

    return line_type, fields


def validate_line(ap, line):
    fields = line.split(";")

    if len(fields) < 3:
        return None

    # ensure monotonic timestamps
    if not ap.update_timestamp(fields[1]):
        return None

    try:
        return VALIDATORS[fields[2]](fields)
    except KeyError:
        return None


def validate_txs(fields):
    if len(fields) != 15:
        return None

    # TODO: more validation of rate indeces?
    return fields


def validate_rxs(fields):
    if len(fields) != 9:
        return None

    # TODO: more validation?
    return fields


def validate_rc_stats(fields):
    if len(fields) != 11:
        return None

    # TODO: more validation?
    return fields


def validate_sta(fields):
    if not (len(fields) == 8 and fields[3] == "remove") and not (
        len(fields) == 49 and fields[3] in ["add", "dump"]
    ):
        return None

    # TODO: more validation?
    return fields


def validate_best_rates(fields):
    if len(fields) != 9:
        return None

    # TODO: more validation?
    return fields

def validate_sample_rates(fields):
    if len(fields) != 19:
        return None

    # TODO: more validation?
    return fields



VALIDATORS = {
    "txs": validate_txs,
    "stats": validate_rc_stats,
    "rxs": validate_rxs,
    "sta": validate_sta,
    "best_rates": validate_best_rates,
    "sample_rates": validate_sample_rates
}


def update_pckt_count_txs(ap, fields):
    """
    Update packet transmission attempt and success counts for a given station.

    Parameters
    ----------
    ap : AccessPoint object

    fields : list
                                    Fields obtained by spliting a data line received from the AP
                                    over the Rate Control API .

    """
    radio = fields[0]
    mac_addr = fields[3]

    try:
        sta = ap.get_stations(radio)[mac_addr]
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
            info[rate]["timestamp"] = timestamp

    sta.update_stats(timestamp, info)

    if num_frames > 1:
        sta.ampdu_enabled = True

    sta.ampdu_len += num_frames
    sta.ampdu_packets += 1


def parse_sta(ap, fields, logger):
    """


    Parameters
    ----------
    ap : Object
                                    Object of rateman.AccessPoint class over which the station is associated.
    fields : list
                                    Fields contained with line separated by ';' and containing 'sta;add'
                                    or 'sta;dump' strings.

    Returns
    -------
    sta : Object
                                    Object of rateman.Station class created after a station connects to a
                                    give AP.

    """
    supported_rates = []
    airtimes_ns = []
    radio = fields[0]
    timestamp = fields[1]
    mac_addr = fields[4]
    mcs_groups = fields[7:]
    overhead_mcs = int(fields[5], 16)
    overhead_legacy = int(fields[6], 16)

    for i, grp_idx in enumerate(ap.supported_rates):
        mask = int(mcs_groups[i], 16)
        for ofs in range(10):
            if mask & (1 << ofs):
                supported_rates.append(f"{grp_idx}{ofs}")
                airtimes_ns.append(ap.supported_rates[grp_idx]["airtimes_ns"][ofs])

    sta = Station(
        ap,
        radio,
        timestamp,
        mac_addr,
        supported_rates,
        airtimes_ns,
        overhead_mcs,
        overhead_legacy,
        logger=logger
    )

    return sta
