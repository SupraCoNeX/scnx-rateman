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
import argparse
import sys


pd.options.mode.chained_assignment = None  # default='warn'

# TODO: Output of tx status and stats are not consistent. Sometimes already converted.
# TODO: Improve Timestamp 2 interpolation. Very dirty now.


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


def get_path_arg():
    """
    Parses path argument provided in the exec command
    """

    parser = argparse.ArgumentParser(description="Scnx-Py-Minstrel")
    parser.add_argument("-p", help="Path to the txs/rcs data file", type=str)

    args = parser.parse_args()

    if args.p:
        try:
            # Checking if the file exists
            f = open(args.p)
            f.close()
        except IOError as e:
            print(e)
        else:
            path = args.p
    else:
        print(
            "Please specify a path, with -p, to the data file for minstrel-py to run!"
        )
        sys.exit(1)

    return path
