# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Demo for plotting
----------------

>TODO: write description


"""
import rateman
import pandas as pd


file = 'collected_data/data_AP1.csv'
df = pd.read_csv(file, sep=';', names=range(12))
df_txs, df_stats = rateman.read_stats_txs_csv(file)
df_error = rateman.flag_error_in_data(file)
rateman.plot_timestamp_errors(df_error)
