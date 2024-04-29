# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

import re
import array
from .station import Station
from .exception import UnsupportedAPIVersionError, ParsingError
from .c_parsing import parse_txs
from .rate_info import *

__all__ = ["process_api", "process_line", "process_header", "parse_sta", "rate_group_and_offset"]

API_VERSION = (2, 1)


def vstr(v):
    return f"{v[0]}.{v[1]}.{v[2]}"


# utility function to parse signed integers from hex strings in two's complement format
def twos_complement(hexstr, bitwidth):
    val = int(hexstr, 16)
    return val - (1 << bitwidth) if val & (1 << (bitwidth - 1)) else val


def parse_s8(s):
    return twos_complement(s, 8)


def parse_s16(s):
    return twos_complement(s, 16)


def parse_s32(s):
    return twos_complement(s, 32)


def check_orca_version(ap, version):
    if version != API_VERSION:
        if version[0] > API_VERSION[0]:
            raise UnsupportedAPIVersionError(ap, API_VERSION, version)
        elif version[1] > API_VERSION[1]:
            ap.logger.warning(
                f"{ap}: ORCA API version is newer than rateman's "
                f"({vstr(version)} vs {vstr(API_VERSION)}). Some features may not be supported."
            )


def process_api(ap, fields, line):
    if len(fields) < 5:
        return

    match fields[2]:
        case "orca_version":
            version = (int(fields[3], 16), int(fields[4], 16), int(fields[5], 16))
            check_orca_version(ap, version)
            ap._api_version = version
        case "group":
            ap.add_group_rate_info(*parse_group_info(fields))
        case "sample_table":
            ap.sample_table = fields[5:]
        case _:
            raise ParsingError(ap, f"Unknown line type '{fields[2]}'")


def parse_tpc_range_block(ap, blk: str) -> list:
    fields = blk.split(",")
    if len(fields) != 4:
        raise ParsingError(ap, f"Malformed TPC range block '{blk}'")

    start_idx = int(fields[0], 16)
    n_indices = int(fields[1], 16)
    start_lvl = parse_s8(fields[2])
    width = parse_s8(fields[3])

    return [
        (start_lvl * 0.25) + (idx * width * 0.25) for idx in range(start_idx, start_idx + n_indices)
    ]


def parse_tpc(ap: "AccessPoint", cap: list) -> dict:
    if len(cap) < 3:
        return None
    elif cap[2] == "not":
        return None

    tpc = {"type": cap[0], "regulatory_limit": cap[-1], "txpowers": []}

    n_ranges = int(cap[1], 16)
    ranges = cap[2:-1]

    if n_ranges != len(ranges):
        raise ParsingError(ap, f"Expected {n_ranges} tpc ranges but {len(ranges)} were found")

    for blk in ranges:
        tpc["txpowers"] += parse_tpc_range_block(ap, blk)

    return tpc


def parse_features(ap: "AccessPoint", features: list) -> dict:
    return {feature: setting for feature, setting in [f.split(",") for f in features]}


def process_phy_info(ap, fields):
    n_features = int(fields[6], 16) if fields[6] else 0

    ap.add_radio(
        fields[0],  # radio
        fields[3],  # driver
        [i for i in fields[4].split(",") if i],  # interfaces
        [e for e in fields[5].split(",") if e],  # active monitor events
        parse_features(ap, fields[7 : 7 + n_features]),
        parse_tpc(ap, fields[7 + n_features :]),  # tx power range blocks
    )


async def process_sta_info(ap, fields):
    match fields[3]:
        case "add" | "dump":
            sta = parse_sta(ap, fields)
            await ap.add_station(sta)

            if sta.rc_mode == "auto":
                await sta.start_rate_control("minstrel_ht_kernel_space", None)

        case "remove":
            sta = await ap.remove_station(mac=fields[4], radio=fields[0])

        case "update":
            sta = parse_sta(ap, fields)
            await ap.update_station(sta)


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


async def process_line(ap, line):
    # FIXME: This is where the AP's raw data callbacks should be called

    if (result := parse_txs(line)) is not None:
        update_rate_stats_from_txs(ap, *result)
        return None

    elif fields := validate_line(ap, line.decode("utf-8").rstrip()):
        match fields[2]:
            case "rxs":
                sta = ap.get_sta(fields[3], radio=fields[0])
                if sta and fields[1] != "7f":
                    sta.update_rssi(
                        int(fields[1], 16),
                        parse_s8(fields[4]),
                        [parse_s8(r) for r in fields[5:]],
                    )
            case "sta":
                await process_sta_info(ap, fields)
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
    "set_probe",
]

PHY_REGEX = r"[-a-z0-9]+"
TIMESTAMP_REGEX = r"[0-9a-f]{16}"
MACADDR_REGEX = r"[0-9a-f]{2}(:[0-9a-f]{2}){5}"


def base_regex(line_type: str) -> str:
    return ";".join([PHY_REGEX, TIMESTAMP_REGEX, line_type, MACADDR_REGEX])


RXS_REGEX = re.compile(base_regex("rxs") + r"(;[0-9a-f]{0,8}){5}")
STATS_REGEX = re.compile(base_regex("stats") + r";[0-9a-f]{1,3}" + r"(;[0-9a-f]++){6}")
RESET_STATS_REGEX = re.compile(base_regex("reset_stats"))
RC_MODE_REGEX = re.compile(base_regex("rc_mode") + r"(;[0-9a-f]+){1}")
BEST_RATES_REGEX = re.compile(base_regex("best_rates") + r"(;[0-9a-f]{1,3}){5}")
SAMPLE_RATES_REGEX = re.compile(base_regex("sample_rates") + r"(;[0-9a-f]{1,3}){15}")
STA_INFO_REGEX = r"(;(manual|auto)){2}(;[0-9a-f]{1,3}){46}"
STA_ADD_REGEX = re.compile(base_regex("sta;add") + ";" + PHY_REGEX + STA_INFO_REGEX)
STA_UPDATE_REGEX = re.compile(base_regex("sta;update") + ";" + PHY_REGEX + STA_INFO_REGEX)
STA_REMOVE_REGEX = re.compile(base_regex("sta;remove") + r";.*+")
CMD_ECHO_REGEX = re.compile(
    ";".join([PHY_REGEX, TIMESTAMP_REGEX]) + ";(" + "|".join(COMMANDS) + ");.*+"
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
    "stats": validate_stats,
    "rxs": validate_rxs,
    "sta": validate_sta,
    "best_rates": validate_best_rates,
    "sample_rates": validate_sample_rates,
    "reset_stats": validate_reset_stats,
    "rc_mode": validate_rc_mode,
    "#error": validate_error,
}


def parse_mrr_stage(s):
    mrr_stage = s.split(",")
    rate = mrr_stage[0].zfill(2)
    count = int(mrr_stage[1], 16)
    txpwr_idx = int(mrr_stage[2], 16) if mrr_stage[2] else None

    return mrr_stage[0].zfill(2), int(mrr_stage[1], 16), txpwr_idx


def update_rate_stats_from_txs(
    ap,
    phy,
    timestamp,
    mac,
    num_frames,
    rates: array,
    txpwrs: array,
    attempts: array,
    successes: array,
) -> None:
    if (sta := ap.get_sta(mac, radio=phy)) is None:
        return

    sta.update_rate_stats(timestamp, rates, txpwrs, attempts, successes)
    sta.update_ampdu(num_frames)


def parse_sta(ap, fields: list):
    supported_rates = []
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

    for i, grp_idx in enumerate(ap._rate_info):
        mask = int(mcs_groups[i], 16)
        for ofs in range(10):
            if mask & (1 << ofs):
                supported_rates.append(i * 16 + ofs)

    return Station(
        mac,
        ap,
        radio,
        iface,
        timestamp,
        rc_mode,
        tpc_mode,
        update_freq,
        sample_freq,
        supported_rates,
        overhead_mcs,
        overhead_legacy,
        logger=ap.logger,
    )


def rate_group_and_offset(rate: int) -> tuple[int, int]:
    grp = rate // 16

    return grp, rate - grp * 16
