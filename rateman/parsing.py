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
import re

from .station import Station
from .exception import UnsupportedAPIVersionError, ParsingError

__all__ = ["process_api", "process_line", "process_header", "parse_sta"]

API_VERSION = 2


# utility function to parse signed integers from hex strings in two's complement format
def twos_complement(hexstr, bits):
    val = int(hexstr, 16)
    return val - (1 << bits) if val & (1 << (bits - 1)) else val


parse_s16 = lambda s: twos_complement(s, 16)
parse_s32 = lambda s: twos_complement(s, 32)


def check_orca_version(ap, v: int):
    if v != API_VERSION:
        raise UnsupportedAPIVersionError(ap, API_VERSION, v)


def process_api(ap, fields):
    if len(fields) < 4:
        return

    match fields[2]:
        case "orca_version":
            check_orca_version(ap, int(fields[3]))
        case "group":
            ap.add_supp_rates(*parse_group_info(fields))
        case "sample_table":
            ap.sample_table = fields[5:]


def parse_tpc_range_block(blk: list) -> list:
    fields = blk.split(",")
    if len(fields) != 4:
        raise ParsingError(ap, f"Malformed TPC range block '{blk}'")

    start_idx = int(fields[0], 16)
    n_indeces = int(fields[1], 16)
    start_lvl = int(fields[2], 16)
    width = int(fields[3], 16)

    return [(start_lvl + idx) * width * .25 for idx in range(start_idx, start_idx + n_indeces + 1)]


def parse_tpc(cap: list) -> dict:
    if cap[0] == "NA":
        return None

    tpc = {
        "type": cap[0],
        "txpowers": []
    }

    n_ranges = int(cap[1], 16)
    ranges = cap[2:]

    if n_ranges != len(ranges):
        raise ParsingError(ap, f"Expected {n_ranges} tpc ranges but only {len(ranges)} were found")

    for blk in ranges:
        tpc["txpowers"] += parse_tpc_range_block(blk)

    return tpc


def process_phy_info(ap, fields):
    radio = fields[0]
    driver = fields[3]
    ifaces = fields[4].split(",")

    ap.add_radio(fields[0], fields[3], fields[4].split(","), parse_tpc(fields[5:]))

    return True


async def process_sta_info(ap, fields):
    # TODO: handle sta;update
    if fields[3] in ["add", "dump"]:
        sta = parse_sta(ap, fields)
        ap.add_station(sta)

        if sta.rc_mode == "auto":
            await sta.start_rate_control("minstrel_ht_kernel_space", {})

    elif fields[3] == "remove":
        sta = ap.remove_station(mac=fields[4], radio=fields[0])
        if sta:
            await sta.stop_rate_control()


async def process_header(ap):
    async for line in ap.api_info():
        fields = line.split(";")
        if fields[0] == "*":
            if fields[2] == "#error":
                ap.handle_error(fields[3])
            process_api(ap, fields)
        elif "0;add" in line:
            process_phy_info(ap, fields)
        else:
            await process_sta_info(ap, fields)


def parse_group_info(fields):
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

async def process_line(ap, line):
    fields = validate_line(ap, line)

    if not fields:
        return None

    match fields[2]:
        case "txs":
            update_rate_stats(ap, fields)
        case "rxs":
            sta = ap.get_sta(fields[3], radio=fields[0])
            if sta:
                sta.update_rssi(
                    int(fields[1], 16),
                    parse_s32(fields[4]),
                    [parse_s32(r) for r in fields[5:]],
                )
        case "sta":
            # TODO: handle sta;update
            if fields[3] in ["add", "dump"]:
                ap.add_station(parse_sta(ap, fields))
            elif fields[3] == "remove":
                sta = ap.remove_station(mac=fields[4], radio=fields[0])
                if sta:
                    await sta.stop_rate_control()

    return fields

COMMANDS = [
    "start",
    "stop",
    "set_rates",
    "set_power",
    "set_rates_power",
    "reset_stats",
    "rc_mode",
    "tpc_mode",
    "set_probe"
]

PHY_REGEX = r"[-a-z0-9]+"
TIMESTAMP_REGEX = r"[0-9a-f]{16}"
MACADDR_REGEX = r"[0-9a-f]{2}(:[0-9a-f]{2}){5}"

def base_regex(line_type: str) -> str:
    return ";".join([PHY_REGEX, TIMESTAMP_REGEX, line_type, MACADDR_REGEX])

TXS_REGEX = re.compile(
    base_regex("txs") + r"(;[0-9a-f]{1,2}){2};[01](;[0-9a-f]{0,4}(,[0-9a-f]{0,4}){2}){4}"
)
RXS_REGEX = re.compile(base_regex("rxs") + r"(;[0-9a-f]{0,8}){5}")
STATS_REGEX = re.compile(base_regex("stats") + r"(;[0-9a-f]+){7}")
BEST_RATES_REGEX = re.compile(base_regex("best_rates") + r"(;[0-9a-f]{1,3}){5}")
SAMPLE_RATES_REGEX = re.compile(base_regex("sample_rates") + r"(;[0-9a-f]{1,3}){15}")
STA_ADD_REGEX = re.compile(
    base_regex("sta;add") + ";" + PHY_REGEX + r"(;(manual|auto)){2}(;[0-9a-f]{1,3}){44}"
)
STA_UPDATE_REGEX = re.compile(
    base_regex("sta;update") + ";" + PHY_REGEX + r"(;(manual|auto)){2}(;[0-9a-f]{1,3}){44}"
)
STA_REMOVE_REGEX = re.compile(base_regex("sta;remove") + r";.*")
CMD_ECHO_REGEX = re.compile(";".join([PHY_REGEX, TIMESTAMP_REGEX]) + ";(" + "|".join(COMMANDS) + ");.*")

def validate_line(ap, line: str) -> list:
    fields = line.split(";")

    if len(fields) < 3:
        return None

    # ensure monotonic timestamps
    if not ap.update_timestamp(fields[1]):
        return None

    try:
        return VALIDATORS[fields[2]](line, fields)
    except KeyError:
        return fields if CMD_ECHO_REGEX.fullmatch(line) else None

def validate_txs(line: str, fields: list) -> list:
    return fields if TXS_REGEX.fullmatch(line) else None

def validate_rxs(line: str, fields: list) -> list:
    return fields if RXS_REGEX.fullmatch(line) else None

def validate_stats(line: str, fields: list) -> list:
    return fields if STATS_REGEX.fullmatch(line) else None

def validate_sta(line: str, fields: list) -> list:
    match fields[3]:
        case "add":
            return fields if STA_ADD_REGEX.fullmatch(line) else None
        case "update":
            return fields if STA_UPDATE_REGEX.fullmatch(line) else None
        case "remove":
            return fields if STA_REMOVE_REGEX.fullmatch(line) else None
        case _:
            return None

def validate_best_rates(line: str, fields: list) -> list:
    return fields if BEST_RATES_REGEX.fullmatch(line) else None

def validate_sample_rates(line: str, fields: list) -> list:
    return fields if SAMPLE_RATES_REGEX.fullmatch(line) else None

VALIDATORS = {
    "txs": validate_txs,
    "stats": validate_stats,
    "rxs": validate_rxs,
    "sta": validate_sta,
    "best_rates": validate_best_rates,
    "sample_rates": validate_sample_rates
}

def update_rate_stats(ap, fields: list) -> None:
    sta = ap.get_sta(fields[3], radio=fields[0])
    if not sta:
        return

    timestamp = int(fields[1], 16)
    num_frames = int(fields[4], 16)
    num_ack = int(fields[5], 16)
    mrr = [tuple(s.split(",")) for s in fields[7:]]
    rates = [r if r != "" else None for (r,_,_) in mrr]
    counts = [int(c, 16) if c != "" else None for (_,c,_) in mrr]
    txpwr = [int(t, 16) if t != "" else None for (_,_,t) in mrr]

    attempts = [(num_frames * c) if c else 0 for c in counts]

    suc_rate_ind = 3
    for i, atmpt in enumerate(attempts):
        if atmpt == 0:
            suc_rate_ind = i - 1
            break

    if suc_rate_ind < 0:
        suc_rate_ind = 0

    succ = [0, 0, 0, 0]
    succ[suc_rate_ind] = num_ack
    rates = [f"0{rate}" if rate and (len(rate) == 1) else rate for rate in rates]
    info = {}

    for i, rate in enumerate(rates):
        if not rate:
            break

        sta.update_rate_stats(timestamp, rate, txpwr[i], attempts[i], succ[i])

    if num_frames > 1:
        sta.ampdu_enabled = True

    sta.ampdu_len += num_frames
    sta.ampdu_packets += 1


def parse_sta(ap, fields: list):
    supported_rates = []
    airtimes_ns = []
    radio = fields[0]
    timestamp = int(fields[1], 16)
    mac = fields[4]
    iface = fields[5]
    rc_mode = fields[6]
    tpc_mode = fields[7]
    overhead_mcs = int(fields[8], 16)
    overhead_legacy = int(fields[9], 16)
    mcs_groups = fields[10:]

    for i, grp_idx in enumerate(ap.supported_rates):
        mask = int(mcs_groups[i], 16)
        for ofs in range(10):
            if mask & (1 << ofs):
                supported_rates.append(f"{grp_idx}{ofs}")
                airtimes_ns.append(ap.supported_rates[grp_idx]["airtimes_ns"][ofs])

    return Station(
        mac,
        ap,
        radio,
        iface,
        timestamp,
        rc_mode,
        tpc_mode,
        supported_rates,
        airtimes_ns,
        overhead_mcs,
        overhead_legacy,
        logger=ap.logger
    )
