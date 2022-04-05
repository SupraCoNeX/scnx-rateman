# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Station Object
----------------

This class provides ... 

"""
import asyncio


__all__ = ["Station"]


class Station:
    def __init__(self) -> None:

        self._sta_ID = ""
        self._sta_IP = ""
        self._sup_rates = {}
        self._cur_ts = ""
        self._sta_cur_stats = {}  # {rate: {cur_atmp, cur_succ}}

        self._loop = asyncio.get_event_loop()

    @property
    def stations(self) -> dict:
        # list of clients for a given AP at a given radio

        return 0

    @property
    def accesspoints(self) -> dict:
        # provides a list of access points in the network
        # dict with APID keys, with each key having a dict with radios,
        # which is also a dict with clients

        return self._accesspoints

    def update_stats(self, sta_IP, new_stats) -> None:
        """
        Start monitoring of TX Status (txs) and Rate Control Statistics
        (rc_stats). Send notification about the experiment from RateMan
        Telegram Bot.

        Parameters
        ----------

        duration: float
            time duration for which the data from APs has to be collected

        output_dir : str
            directory to which parsed data is saved

        Returns
        -------
        None.

        """

        pass
