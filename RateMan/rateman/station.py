# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Station Class
-------------

A Station object is created at instance a station connects to a given AP. 

"""


__all__ = ["Station"]


class Station:
    def __init__(self, radio, mac_addr, supp_rates, timestamp) -> None:
        self._radio = radio
        self._mac_addr = mac_addr
        self._supp_rates = supp_rates
        self._last_seen = timestamp
        self._stats = {}
        self._rssi = 1
        self._rssi_vals = []

    @property
    def last_seen(self) -> str:
        return self._last_seen

    @property
    def radio(self) -> str:
        return self._radio

    @radio.setter
    def radio(self, radio):
        self._radio = radio

    @property
    def supp_rates(self) -> list:
        return self._supp_rates

    @property
    def mac_addr(self) -> str:
        return self._mac_addr

    @property
    def stats(self) -> dict:
        return self._stats

    def lowest_supp_rate(self):
        return self._supp_rates[0]

    def update_stats(self, timestamp, info: dict) -> None:
        '''
        Parameters
        ----------
        timestamp : TYPE
            DESCRIPTION.
        info : dict
            DESCRIPTION.

        Returns
        -------
        None
            DESCRIPTION.

        '''
        for rate, stats in info.items():
            if timestamp > self._last_seen:
                self._last_seen = timestamp
                self._stats[rate] = stats

    def update_rssi(self, timestamp, min_rssi, per_antenna):
        if timestamp > self._last_seen:
            self._rssi = min_rssi
            self._rssi_vals = per_antenna

    def check_rate_entry(self, rate):
        '''
        

        Parameters
        ----------
        rate : TYPE
            DESCRIPTION.

        Returns
        -------
        TYPE
            DESCRIPTION.

        '''
        return rate in self._stats

    def get_attempts(self, rate):
        '''
        

        Parameters
        ----------
        rate : TYPE
            DESCRIPTION.

        Returns
        -------
        TYPE
            DESCRIPTION.

        '''
        return self._stats[rate]["attempts"]

    def get_successes(self, rate):
        '''
        

        Parameters
        ----------
        rate : TYPE
            DESCRIPTION.

        Returns
        -------
        TYPE
            DESCRIPTION.

        '''
        return self._stats[rate]["success"]

    def reset_stats(self) -> None:
        '''
        

        Returns
        -------
        None
            DESCRIPTION.

        '''
        self._stats = {}

    def __str__(self):
        return f"STA[{self._mac_addr}]"
