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

filename = '../../scnx-analysis/data_Mesh_sample.csv'


# Obtain TXS and RCS Dataframes

txs_df = rateman.obtain_txs_df(filename)
rcs_df = rateman.obtain_rcs_df(filename)


# Obtain dataframe with flags indicating validity of a give trace
data_flags_df = rateman.obtain_data_flags(filename)
data_flags_array = data_flags_df.to_numpy()

num_total_lines = len(data_flags_array)

# Subselect complete dataframe for traces with TXS or RCS information
stats_flags_df = data_flags_df[data_flags_df['stats_field'] == '1']
stats_flags_array = stats_flags_df.to_numpy()

num_stat_lines = len(stats_flags_array)

num_invalid_timestamps = len(np.where(stats_flags_array[:, 2] == '0')[0])
num_invalid_num_fields = len(np.where(stats_flags_array[:, 1] == '0')[0])

num_invalid_lines = len(np.where(stats_flags_array == '0')[0])
num_valid_stat_lines = num_stat_lines - num_invalid_lines

print('Number of valid traces in data file %d from %s total lines' %
      (num_valid_stat_lines, num_total_lines))
