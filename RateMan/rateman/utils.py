import io
from os import stat
from pathlib import Path
from pdb import set_trace
import signal
import time

import pandas as pd

pd.options.mode.chained_assignment = None  # default='warn'

# TODO: Output of tx status and stats are not consistent. Sometimes already converted.


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
        p = io.StringIO(data.decode("utf-8"))
    else:
        p = Path(data)
        if not p.exists():
            raise FileNotFoundError
    # Read CSV file containing tx status and rc_stats and save in
    # dataframe `df`.
    df = pd.read_csv(p, sep=";", header=3)
    # Filter tx status from dataframe `df`.
    txs_data = df[df.iloc[:, 2] == "txs"].iloc[:, :9]
    txs_data.columns = [
        "phy_nr",
        "timestamp",
        "type",
        "macaddr",
        "num_frames",
        "num_acked",
        "probe",
        "rates",
        "counts",
    ]
    # Filter rc_stats from dataframe `df`.
    stats_data = df[df.iloc[:, 2] == "stats"]
    stats_data.columns = [
        "phy_nr",
        "timestamp",
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
    if humanread:
        # Convert boot timestamp into seconds (uptime of system)
        to_sec = lambda x: int(x, 16) / 1000000000
        txs_data["timestamp"] = txs_data.timestamp.apply(to_sec)
        stats_data["timestamp"] = stats_data.timestamp.apply(to_sec)
        # Convert avg throughput from hex to bit/s
        to_bits = lambda x: int(x, 16)
        try:
            stats_data["avg_tp"] = stats_data.avg_tp.apply(to_bits)
        except TypeError:
            print("Average Throughput probably already converted...")
    # Reset index of dataframes
    txs_data = txs_data.reset_index(drop=True)
    stats_data = stats_data.reset_index(drop=True)
    # Omit probably defective packets (wrong timestamp) and shift time to
    # zero if `shifttime = True`.
    if not txs_data.empty:
        txs_ts0 = txs_data.loc[0].timestamp
        txs_data = txs_data[txs_data["timestamp"] > txs_ts0]
        if shifttime:
            shifttxs = lambda x: x - txs_ts0
            txs_data["timestamp"] = txs_data.timestamp.apply(shifttxs)
    if not stats_data.empty:
        stats_ts0 = stats_data.loc[0].timestamp
        stats_data = stats_data[stats_data["timestamp"] > stats_ts0]
        if shifttime:
            shiftstats = lambda x: x - stats_ts0
            stats_data["timestamp"] = stats_data.timestamp.apply(shiftstats)
    # Set timestamps as index for both dataframes `txs_data` and
    # `stats_data`.
    txs_data = txs_data.set_index("timestamp")
    stats_data = stats_data.set_index("timestamp")
    return txs_data, stats_data


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
#     csvfile = 'demo/collected_data/data_AP1.csv'
#     txs, stats = read_stats_txs_csv(csvfile, True)
#     print("Done")
