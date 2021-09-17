# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Demo to check collected data file
----------------

>TODO: write description


"""
import rateman
import pandas as pd
import numpy as np
import logging


filename = "C:/Users/pawarsp/Desktop/PhD/1_ResourceAllocation/Code/SupraCoNeX/scnx-analysis/data_Mesh_Andre.csv"


def create_logger(filename="error.log"):
    logging.basicConfig(
        filename=filename,
        level=logging.DEBUG,
        format="\n%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger(__name__)
    return logger


def check_data(filename, logger=None):
    # Obtain TXS and RCS Dataframes

    txs_df = rateman.obtain_txs_df(filename, logger=logger)
    rcs_df = rateman.obtain_rcs_df(filename, logger=logger)

    ts_txs_df = txs_df.timestamp_ns.to_numpy().astype(np.int64)
    ts_rcs_df = rcs_df.timestamp_ns.to_numpy().astype(np.int64)

    # Obtain dataframe with flags indicating validity of a give trace
    data_flags_df = rateman.obtain_data_flags(filename)
    data_flags_array = data_flags_df.to_numpy()

    num_total_lines = len(data_flags_array)

    # Subselect complete dataframe for traces with TXS or RCS information
    stats_flags_df = data_flags_df[data_flags_df["stats_field"] == 1]
    stats_flags_array = stats_flags_df.to_numpy()

    num_stat_lines = len(stats_flags_array)

    num_invalid_timestamps = len(np.where(stats_flags_array[:, 2] == 0)[0])
    num_invalid_num_fields = len(np.where(stats_flags_array[:, 1] == 0)[0])

    num_invalid_lines = len(np.where(stats_flags_array == 0)[0])
    num_valid_stat_lines = num_stat_lines - num_invalid_lines

    print(f"File: {filename}")

    print(
        "Number of valid traces in data file %d from %s total lines"
        % (num_valid_stat_lines, num_total_lines)
    )

    print("Number of invalid traces in data file %d" % (num_invalid_lines))


if __name__ == "__main__":
    logger = create_logger()
    check_data(filename=filename, logger=logger)
