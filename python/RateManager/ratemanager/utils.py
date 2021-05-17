

import pandas as pd
from pathlib import Path


__all__ = [
    "read_stats_txs_csv",
]


def read_stats_txs_csv(filename: str) -> pd.core.frame.DataFrame:
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
    p = Path(filename)
    if not p.exists():
        raise FileNotFoundError
    else:
        # Read CSV file containing tx status and rc_stats and save in
        # dataframe `df`.
        df = pd.read_csv(p, sep=';', header=3)
        # Filter tx status from dataframe `df`.
        txs_data = df[df.iloc[:, 2] == 'txs'].iloc[:, :9]
        txs_data.columns = [
            'phy_nr',
            'timestamp',
            'type',
            'macaddr',
            'num_frames',
            'num_acked',
            'probe',
            'rates',
            'counts'
        ]
        # Filter rc_stats from dataframe `df`.
        stats_data = df[df.iloc[:, 2] == 'stats']
        stats_data.columns = [
            'phy_nr',
            'timestamp',
            'type',
            'macaddr',
            'rate',
            'avg_prob',
            'avg_tp',
            'cur_success',
            'cur_attempts',
            'hist_success',
            'hist_attempts'
        ]
        # Set timestamps as index for both dataframes `txs_data` and
        # `stats_data`.
        txs_data.set_index('timestamp')
        stats_data.set_index('timestamp')
    return txs_data, stats_data
