import io
from pathlib import Path
import signal

import pandas as pd
import numpy as np
from pandas.io.parsers import read_csv
import matplotlib.pyplot as plt

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

def flag_error_in_data(file):
    """Flag error lines in traces. There are timestamp errors and parsing errors
    if they are not timestamp errors.
    """
    df = read_csv(file, sep=';', names=range(14))
    df.columns = [
        "phy_nr",
        "timestamp",
        "timestamp2",
        "type",
        "macaddr",
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        "parsing_error",
        "timestamp_error",
    ]
    # Skip ap_info lines
    ap_info_len = df.loc[df['timestamp2'] == 'group'].index[-1]
    phy_len = df['phy_nr'].unique().size
    df_data = df.iloc[ap_info_len+phy_len:]
    # Set the `parsing_error` flag of lines with NaN as type to True
    df_data.loc[:, 'parsing_error'] = False
    df_data.loc[:, 'timestamp_error'] = False
    df_data.loc[df_data.type.isna(), 'parsing_error'] = True
    ts_new, ts_error = _interpolate_error_timestamps(df_data.timestamp)
    df_data.loc[:, 'timestamp'] = ts_new
    df_data.loc[ts_error, 'timestamp_error'] = True
    ts_new2, ts_error2 = _interpolate_error_timestamps(df_data.timestamp2, True)
    df_data.loc[:, 'timestamp2'] = ts_new2
    df_data.loc[ts_error2, 'timestamp_error'] = True
    df_data = df_data.set_index(["timestamp", "timestamp2"])
    return df_data

def _interpolate_error_timestamps(timestamps, ns=False, error_interval=1000):
    """Interpolate error timestamp.
    #TODO: Improve timestamp interpolation
    """
    ts = []
    ts_errors = []
    first_entry = True
    running_flag = False
    last_valid = 0
    counter = 0
    timestamps = timestamps.astype(str)
    for i, t in enumerate(timestamps):
        # Special case: 1st entry
        # Wait until receiving a valid timestamp but could be not correct
        # Therefore, there is the `running_flag` which should detect the wrong
        # first timestamp
        if first_entry:
            if pd.notna(t) and t.isnumeric():
                ts.append(int(t))
                for c in range(1, counter+1):
                    ts[i-c] = t-c
                first_entry = False
                last_valid = i
                counter = 0
                ts_errors.append(False)
            else:
                ts.append(pd.NA)
                counter += 1
                ts_errors.append(True)
        elif not running_flag and pd.notna(t) and t.isnumeric():
            diff = int(t) - int(timestamps.iloc[last_valid])
            if ns:
                ts.append(int(t))
                for j in range(1, counter+1):
                    ts[i-j] = int(t)-j
                counter = 0
                last_valid = i
                ts_errors.append(False)
            else:
                if diff < 0:
                    ts.append(pd.NA)
                    counter += 1
                    ts_errors.append(True)
                elif diff > error_interval:
                    ts.append(int(t))
                    for j in range(1, counter+1):
                        ts[i-j] = int(t)-j
                    running_flag = True
                    last_valid = i
                    counter = 0
                    ts_errors.append(False)
                elif 0 <= diff <= error_interval:
                    ts.append(int(t))
                    step_width = diff/(counter+1)
                    for j in range(1, counter+1):
                        ts[i-j] = int(int(t) - j * step_width)
                    running_flag = True
                    last_valid = i
                    counter = 0
                    ts_errors.append(False)
        elif pd.notna(t) and t.isnumeric():
            if ns:
                ts.append(int(t))
                step_width = (int(t) - int(timestamps.iloc[last_valid])) / (counter + 1)
                for j in range(1, counter+1):
                    ts[i-j] = int(int(t) - j * step_width)
                counter = 0
                last_valid = i
                ts_errors.append(False)
            elif np.abs(int(t) - int(timestamps.iloc[last_valid])) <= error_interval and not ns:
                ts.append(int(t))
                step_width = (int(t) - int(timestamps.iloc[last_valid])) / (counter + 1)
                for j in range(1, counter+1):
                    ts[i-j] = int(int(t) - j * step_width)
                last_valid = i
                counter = 0
                ts_errors.append(False)
            else:
                ts.append(pd.NA)
                counter += 1
                ts_errors.append(True)
        else:
            ts.append(pd.NA)
            counter += 1
            ts_errors.append(True)
    return ts, ts_errors

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

def plot_timestamp_errors(error_df):
    x = error_df['timestamp']

def plot_parsing_errors(error_df):
    pass
