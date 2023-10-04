# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

import asyncio
import re

from .station import Station
from .accesspoint import AccessPoint
from .exception import UnsupportedAPIVersionError, ParsingError

__all__ = ["process_api", "process_line", "process_header", "parse_sta"]

API_VERSION = (2, 9)


# utility function to parse signed integers from hex strings in two's complement format
def twos_complement(hexstr, bits):
    val = int(hexstr, 16)
    return val - (1 << bits) if val & (1 << (bits - 1)) else val


def parse_s16(s):
    return twos_complement(s, 16)


def parse_s32(s):
    return twos_complement(s, 32)


def check_orca_version(ap, version, line):
    if (
        (not re.fullmatch(r"\*;0;orca_version;[0-9a-f]+;[0-9a-f]+", line)) or
        version != API_VERSION
    ):
        raise UnsupportedAPIVersionError(ap, API_VERSION, version)


def process_api(ap, fields, line):
    if len(fields) < 5:
        return

    match fields[2]:
        case "orca_version":
            check_orca_version(ap, (int(fields[3], 16), int(fields[4], 16)), line)
        case "group":
            ap.add_supported_rates(*parse_group_info(fields))
        case "sample_table":
            ap.sample_table = fields[5:]
        case _:
            raise ParsingError(ap, f"Unknown line type '{fields[2]}'")


def parse_tpc_range_block(ap, blk: list) -> list:
    fields = blk.split(",")
    if len(fields) != 4:
        raise ParsingError(ap, f"Malformed TPC range block '{blk}'")

    start_idx = int(fields[0], 16)
    n_indeces = int(fields[1], 16)
    start_lvl = int(fields[2], 16)
    width = int(fields[3], 16)

    return [(start_lvl + idx) * width * .25 for idx in range(start_idx, start_idx + n_indeces + 1)]


def parse_tpc(ap: AccessPoint, cap: list) -> dict:
    if cap[0] == "not":
        return None

    tpc = {
        "type": cap[0],
        "regulatory_limit": cap[-1],
        "txpowers": []
    }

    n_ranges = int(cap[1], 16)
    ranges = cap[2:]

    if n_ranges != len(ranges):
        raise ParsingError(ap, f"Expected {n_ranges} tpc ranges but only {len(ranges)} were found")

    for blk in ranges:
        tpc["txpowers"] += parse_tpc_range_block(ap, blk)

    return tpc


def parse_features(ap: AccessPoint, features: list) -> dict:

    return {feature: setting for feature, setting in [f.split(",") for f in features]}


def process_phy_info(ap, fields):
    n_features = int(fields[6], 16)

    ap.add_radio(
        fields[0],             # radio
        fields[3],             # driver
        fields[4].split(","),  # interfaces
        fields[5].split(","),  # active monitor events
        parse_features(ap, fields[7:7 + n_features]),
        parse_tpc(ap, fields[7 + n_features:])  # tx power range blocks
    )


async def process_sta_info(ap, fields):
    # TODO: handle sta;update
    if fields[3] in ["add", "dump"]:
        sta = parse_sta(ap, fields)
        await ap.add_station(sta)

        if sta.rc_mode == "auto":
            await sta.start_rate_control("minstrel_ht_kernel_space", None)

    elif fields[3] == "remove":
        sta = ap.remove_station(mac=fields[4], radio=fields[0])
        if sta:
            await sta.stop_rate_control()


async def process_header(ap):
    async for line in ap.api_info():
        if line.startswith("*;0;#"):
            continue
        elif line.startswith("*;0;"):
            process_api(ap, line.split(";"), line)
        elif "0;add;" in line:
            process_phy_info(ap, line.split(";"))
        elif "0;sta;add;" in line:
            await process_sta_info(ap, line.split(";"))


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
            if sta and fields[1] != "7f":
                sta.update_rssi(
                    int(fields[1], 16),
                    parse_s32(fields[4]),
                    [parse_s32(r) for r in fields[5:]],
                )
        case "sta":
            # TODO: handle sta;update
            if fields[3] in ["add", "dump"]:
                await ap.add_station(parse_sta(ap, fields))
            elif fields[3] == "remove":
                sta = await ap.remove_station(mac=fields[4], radio=fields[0])
                if sta:
                    await sta.stop_rate_control()
        case "#error":
            ap.handle_error(fields[3])

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
RESET_STATS_REGEX = re.compile(base_regex("reset_stats"))
RC_MODE_REGEX = re.compile(base_regex("rc_mode")+ r"(;[0-9a-f]+){1}")
BEST_RATES_REGEX = re.compile(base_regex("best_rates") + r"(;[0-9a-f]{1,3}){5}")
SAMPLE_RATES_REGEX = re.compile(base_regex("sample_rates") + r"(;[0-9a-f]{1,3}){15}")
STA_ADD_REGEX = re.compile(
    base_regex("sta;add") + ";" + PHY_REGEX + r"(;(manual|auto)){2}(;[0-9a-f]{1,3}){44}"
)
STA_UPDATE_REGEX = re.compile(
    base_regex("sta;update") + ";" + PHY_REGEX + r"(;(manual|auto)){2}(;[0-9a-f]{1,3}){44}"
)
STA_REMOVE_REGEX = re.compile(base_regex("sta;remove") + r";.*")
CMD_ECHO_REGEX = re.compile(
    ";".join([PHY_REGEX, TIMESTAMP_REGEX]) + ";(" + "|".join(COMMANDS) + ");.*"
)
ERROR_REGEX = re.compile(r"\*;0;#error;.*")


def validate_line(ap, line: str) -> list:
    fields = line.split(";")

    if len(fields) < 3:
        return None

    # ensure monotonic timestamps
    if not ap.update_timestamp(fields[1]) and fields[2] != "reset_stats":
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

def validate_reset_stats(line: str, fields: list) -> list:
    return fields if RESET_STATS_REGEX.fullmatch(line) else None

def validate_rc_mode(line: str, fields: list) -> list:
    return fields if RC_MODE_REGEX.fullmatch(line) else None



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


def validate_error(line: str, fields: list) -> list:
    return fields if ERROR_REGEX.fullmatch(line) else None


VALIDATORS = {
    "txs": validate_txs,
    "stats": validate_stats,
    "rxs": validate_rxs,
    "sta": validate_sta,
    "best_rates": validate_best_rates,
    "sample_rates": validate_sample_rates,
    "reset_stats": validate_reset_stats,
    "rc_mode": validate_rc_mode,
    "#error": validate_error
}


def update_rate_stats(ap, fields: list) -> None:
    sta = ap.get_sta(fields[3], radio=fields[0])
    supported_txpowers = ap.txpowers(sta.radio)
    if not sta:
        return

    timestamp = int(fields[1], 16)
    num_frames = int(fields[4], 16)
    num_ack = int(fields[5], 16)
    mrr = [tuple(s.split(",")) for s in fields[7:]]
    rates = [r if r != "" else None for (r, _, _) in mrr]
    counts = [int(c, 16) if c != "" else None for (_, c, _) in mrr]
    ind_txpwr = [int(str(int(t, 16)), 16) if t != "" else None for (_, _, t) in mrr]
    txpowers = [supported_txpowers[ind] if ind else None for ind in ind_txpwr]

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
    rates = [f"0{rate}" if (rate and len(rate) == 1) else rate for rate in rates]

    for i, rate in enumerate(rates):
        if not rate:
            break
        sta.update_rate_stats(timestamp, rate, txpowers[i], attempts[i], succ[i])

    sta.update_ampdu(num_frames)


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
    update_freq = int(fields[10], 16)
    sample_freq = int(fields[11], 16)
    mcs_groups = fields[12:]

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
        update_freq,
        sample_freq,
        tpc_mode,
        supported_rates,
        airtimes_ns,
        overhead_mcs,
        overhead_legacy,
        logger=ap.logger
    )
