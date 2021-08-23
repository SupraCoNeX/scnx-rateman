# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org

import io
from pathlib import Path
from re import I
import signal
from datetime import datetime
from pandas.io.parsers import read_csv
import pandas as pd


pd.options.mode.chained_assignment = None  # default='warn'

#TODO: Output of tx status and stats are not consistent. Sometimes already converted.
#TODO: Improve Timestamp 2 interpolation. Very dirty now. 


__all__ = ["read_stats_txs_csv", "timedInput"]

def read_stats_txs_csv(
    data: str, shifttime: bool = False, humanread: bool = True, bin_enc: bool = False
) -> pd.core.frame.DataFrame:
    """Read rc_stats and tx status from the given csv file.

    Parameters:
    -----------
    filename : str
        Path plus filename of csv file containing the tx-status data.

    Returns:
    --------
    txs_data : pd.core.frame.DataFrame
        Pandas dataframe with tx status of the client.
    stats_data : pd.core.frame.DataFrame
        Pandas datafram with rc_stats data of the client.
    """

    if bin_enc:
        p = io.StringIO(data.decode('utf-8'))
    else:
        p = Path(data)
        if not p.exists():
            raise FileNotFoundError
    # Read CSV file containing tx status and rc_stats and save in
    # dataframe `df`.
    df = pd.read_csv(p, sep=";", names=range(12))
    # Read tx status from dataframe `df`.
    txs_data = df[df.iloc[:, 3] == "txs"]
    txs_data.columns = [
        "phy_nr",
        "timestamp",
        "timestamp2",
        "type",
        "macaddr",
        "num_frames",
        "num_acked",
        "probe",
        "rate_count1",
        "rate_count2",
        "rate_count3",
        "rate_count4",
    ]
    # Read rc_stats from dataframe `df`.
    stats_data = df[df.iloc[:, 3] == "stats"]
    stats_data.columns = [
        "phy_nr",
        "timestamp",
        "timestamp2",
        "type",
        "macaddr",
        "rate",
        "avg_prob",
        "avg_tp",
        "cur_success",
        "cur_attempts",
        "hist_success",
        "hist_attempts",
    ]
    # stats_data_idx = stats_data.index
    # txs_data_idx = txs_data.index
    # rest_data_idx = df.index.difference(stats_data_idx.union(txs_data_idx))
    # rest_data = df[rest_data_idx]
    # Reset index of dataframes
    txs_data = txs_data.reset_index(drop=True)
    stats_data = stats_data.reset_index(drop=True)
    
    #TODO: Check: Omit probably defective packets (wrong timestamp)
    if txs_data.empty:
        txs_ts0 = 0
    else:
        txs_ts0 = txs_data.loc[0].timestamp
        txs_data = txs_data[txs_data["timestamp"] > txs_ts0]
    if stats_data.empty:
        stats_ts0 = 0
    else:
        stats_ts0 = stats_data.loc[0].timestamp
        stats_data = stats_data[stats_data["timestamp"] > stats_ts0]
    # Set timestamps as index for both dataframes `txs_data` and
    # `stats_data`.
    txs_data = txs_data.set_index(["timestamp", "timestamp2"])
    stats_data = stats_data.set_index(["timestamp", "timestamp2"])
    return txs_data, stats_data

def _convert_timestamps_to_datetime(df):
    """Convert timestamps to datetime objects."""
    pass

def timedInput(prompt="", timeout=1, timeoutmsg=None):
    def timeout_error(*_):
        raise TimeoutError

    signal.signal(signal.SIGALRM, timeout_error)
    signal.alarm(timeout)
    try:
        answer = input(prompt)
        signal.alarm(0)
        return answer
    except TimeoutError:
        if timeoutmsg:
            print(timeoutmsg)
        signal.signal(signal.SIGALRM, signal.SIG_IGN)
        return None


# if __name__ == '__main__':
#     file = '/home/martin/Projects/SupraCoNeX/data/Meas_20210713_173006/data/data_AP1.csv'
#     df = pd.read_csv(file, sep=';', names=range(12))
#     df_txs, df_stats = read_stats_txs_csv(file)
#     df_error = flag_error_in_data(file)
#     plot_timestamp_errors(df_error)
