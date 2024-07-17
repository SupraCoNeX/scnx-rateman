import linecache
import math

__all__ = ["get_rate_info", "parse_group_info"]

AVAILABLE_PARAMS = {
    "mcs": [
        "BPSK,1/2",
        "QPSK,1/2",
        "QPSK,3/4",
        "16-QAM,1/2",
        "16-QAM,3/4",
        "64-QAM,2/3",
        "64-QAM,3/4",
        "64-QAM,5/6",
        "256-QAM,3/4",
        "256-QAM,5/6",
        "1024-QAM,3/4",
        "1024-QAM,5/6",
    ],
    "bandwidth": ["20", "40", "80", "160"],  # MHz
    "guard_interval": {"LGI": 0.8e-6, "SGI": 0.4e-6},
    "max_nss": 8,
    "num_subcarriers": {
        "ht": {"20MHz": 52, "40MHz": 108, "80MHz": 234, "160MHz": 468},
        "vht": {"20MHz": 52, "40MHz": 108, "80MHz": 234, "160MHz": 468},
    },
    "num_codedbits_per_subcarrier_per_stream": {
        "BPSK": 1,
        "QPSK": 2,
        "16-QAM": 4,
        "64-QAM": 6,
        "256-QAM": 8,
    },
    "coding_rate": {"1/2": 1 / 2, "3/4": 3 / 4, "2/3": 2 / 3, "5/6": 5 / 6},
    "duration_ofdm": {"ht": 3.2e-6, "vht": 3.2e-6},
    "overhead_mcs": 108,
    "overhead_legacy": 60,
}


def get_rate_info(all_rate_info: dict, rate_idx: str) -> dict:
    if len(rate_idx) == 1:
        rate_group = "0"
        rate_idx = f"0{rate_idx}"
    elif len(rate_idx) == 2:
        rate_group = rate_idx[0]
    elif len(rate_idx) == 3:
        rate_group = rate_idx[:-1]

    rate_info = dict()
    mcs_offset = int(rate_idx[-1])
    rate_info["type"] = all_rate_info[rate_group]["type"]
    mcs = all_rate_info[rate_group]["mcs"][mcs_offset]
    rate_info["nss"] = all_rate_info[rate_group]["nss"]
    rate_info["bandwidth"] = all_rate_info[rate_group]["bandwidth"]
    rate_info["guard_interval"] = all_rate_info[rate_group]["guard_interval"]
    rate_info["guard_interval_microsec"] = all_rate_info[rate_group]["guard_interval_microsec"]
    rate_info["airtime_ns"] = all_rate_info[rate_group]["airtimes_ns"][mcs_offset]
    rate_info["MCS"] = mcs
    rate_info["MCS_ind"] = AVAILABLE_PARAMS["mcs"].index(mcs) + 1
    rate_info["modulation"] = mcs.split(",")[0]
    rate_info["coding"] = mcs.split(",")[1]
    rate_info["min_rssi"] = _cal_min_rssi(
        mcs_offset, int(rate_info["bandwidth"][:-3]), rate_info["nss"], num_rx_antennas=4
    )

    if rate_info["type"] in ["ofdm", "cck"]:
        rate_info["data_rate_Mbps"] = 0
    else:
        rate_info["data_rate_Mbps"] = _cal_data_rate(
            AVAILABLE_PARAMS["guard_interval"][rate_info["guard_interval"]],
            AVAILABLE_PARAMS["num_subcarriers"][rate_info["type"]][rate_info["bandwidth"]],
            AVAILABLE_PARAMS["num_codedbits_per_subcarrier_per_stream"][rate_info["modulation"]],
            AVAILABLE_PARAMS["duration_ofdm"][rate_info["type"]],
            AVAILABLE_PARAMS["coding_rate"][rate_info["coding"]],
            rate_info["nss"],
        )

    return rate_info


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

    bandwidth = f"{AVAILABLE_PARAMS['bandwidth'][int(fields[7])]}MHz"

    guard_interval = f"{list(AVAILABLE_PARAMS['guard_interval'])[int(fields[8])]}"
    guard_interval_microsec = f"{AVAILABLE_PARAMS['guard_interval'][guard_interval]}"
    group_info = {
        "rate_inds": rate_inds,
        "airtimes_ns": airtimes_ns,
        "type": fields[5],
        "mcs": AVAILABLE_PARAMS["mcs"][: len(rate_inds)],
        "nss": int(fields[6]),
        "bandwidth": bandwidth,
        "guard_interval": guard_interval,
        "guard_interval_microsec": guard_interval_microsec,
    }

    return group_ind, group_info


def _cal_data_rate(
    guard_interval,
    num_subcarrier,
    num_codedbit,
    duration_ofdm,
    coding_rate,
    num_spatialstream,
):
    data_rate = (num_subcarrier * num_codedbit * coding_rate * num_spatialstream) / (
        duration_ofdm + guard_interval
    )
    data_rate_Mbps = round(data_rate * 1e-6, 2)

    return data_rate_Mbps


def _cal_min_rssi(mcs_offset, bw, nss, num_rx_antennas):
    """
    For a given rate calculate minimum RSSI required.
    Based on the paper entitled
    'IEEE 802.11n/ac Data Rates under Power Constraints' by Yousri Daldoul et al.

    Parameters
    ----------
    mcs_offset : MCS index within a given group
    bw : Channel bandwidth
    nss : Number of spatial streams
    num_rx_antennas : Expected number of RX antennas

    Returns
    -------
    rssi : RSSI in dBm

    """

    base_rssi = [-82, -79, -77, -74, -70, -66, -65, -64, -59, -57]

    rssi = (
        base_rssi[mcs_offset]
        + (10 * math.log10(bw / 20))
        + (10 * math.log10(nss))
        - (10 * math.log10(num_rx_antennas / nss))
    )
    return rssi
