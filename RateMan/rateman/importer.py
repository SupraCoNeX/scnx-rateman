# -*- coding: utf-8 -*-
r"""
Importer Module
-------------------

This module provides a collection of functions to import collected data.
>TODO: extend description

"""

import io
from pathlib import Path
from pandas.io.parsers import read_csv
import pandas as pd
import linecache
import numpy as np


__all__ = ["read_stats_txs_csv", "obtain_txs_df", "obtain_rcs_df"]


def obtain_txs_df(filename):
    
    num_lines = sum(1 for line in open(filename, mode="r"))

    
    txs_array = np.empty((15,), dtype="<U11")
    temp_txs = np.empty((15,), dtype="<U11")

    
    for ii in range(num_lines):
        line = linecache.getline(filename, ii)
        
        if (line.find("*") == -1 and line.find("txs") != -1):
    
            fields = line.split(sep=";")
            
            timestamp_ns = int(fields[1]+fields[2])
            mac_addr = fields[4]
            num_frames = int(fields[5], 16)
            num_ack = int(fields[6], 16)
            probe = fields[7]
            rate_ind1 = fields[8].split(sep=",")[0]
            rate_ind2 = fields[9].split(sep=",")[0]
            rate_ind3 = fields[10].split(sep=",")[0]
            rate_ind4 = fields[11].split(sep=",")[0]
        
            count1 = int(fields[8].split(sep=",")[1], 16)
            count2 = int(fields[9].split(sep=",")[1], 16)
            count3 = int(fields[10].split(sep=",")[1], 16)
            count4 = int(fields[11].strip().split(sep=",")[1], 16)
        
            attempts = sum(num_frames * list(map(int, [count1, count2, count3, count4])))
            
            temp_txs =  np.array([
                timestamp_ns,
                mac_addr,
                num_frames,
                num_ack,
                probe,
                rate_ind1,
                count1,
                rate_ind2,
                count2,
                rate_ind3,
                count3,
                rate_ind4,
                count4,
                attempts,
                num_ack,
            ])
        
            txs_array = np.vstack((txs_array, temp_txs))
    
    txs_array = txs_array[1:,:]
    txs_df = pd.DataFrame(
        txs_array,
        columns=[
            "timestamp_ns",
            "mac_addr",
            "num_frames",
            "num_ack",
            "probe",
            "rate_ind1",
            "count1",
            "rate_ind2",
            "count2",
            "rate_ind3",
            "count3",
            "rate_ind4",
            "count4",
            "attempts",
            "success",
        ],
    )

    return txs_df

def obtain_rcs_df(filename):
    
    num_lines = sum(1 for line in open(filename, mode="r"))

    rcs_array = np.empty((9,), dtype="<U11")   
    temp_rcs = np.empty((9,), dtype="<U11")

    for ii in range(num_lines):
        line = linecache.getline(filename, ii)
        
        if (line.find("*") == -1 and line.find("stats") != -1):
       
            fields = line.split(sep=";")
            
            timestamp_ns = int(fields[1]+fields[2])
            mac_addr = fields[4]
            rate = fields[5]
            avg_prob = fields[6]
            avg_tp = fields[7]
            cur_success = fields[8]
            cur_attempts = fields[9]
            hist_success = fields[10]
            hist_attempts = fields[11]
            
        
            temp_rcs = [
                timestamp_ns,
                mac_addr,
                rate,
                avg_prob,
                avg_tp,
                cur_success,
                cur_attempts,
                hist_success,
                hist_attempts
            ]
            
            rcs_array = np.vstack((rcs_array, temp_rcs))
    
    rcs_df = pd.DataFrame(
        rcs_array,
        columns=[
            "timestamp_ns",
            "mac_addr",
            "rate",
            "avg_prob",
            "avg_tp",
            "cur_success",
            "cur_attempts",
            "hist_success",
            "hist_attempts"
        ],
    )

    return rcs_df


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
  
    return txs_data, stats_data
