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
