# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Station Class
-------------

A Station object is created at instance a station connects to a given AP. 

"""

import asyncio
import logging

from . import rate_control
from .exception import RateControlError, RateControlConfigError

__all__ = ["Station"]


class Station:
    def __init__(
        self,
        ap,
        radio,
        timestamp,
        mac_addr,
        supp_rates,
        airtimes_ns,
        overhead_mcs,
        overhead_legacy,
        rc_alg="minstrel_ht_kernel_space",
        rc_opts=None,
        logger=None
    ) -> None:
        """
        Parameters
        ----------
        radio : str
            Name of physical radio of the AP to which station is connected.
        mac_addr : str
            MAC address of the station.
        supp_rates : list
            List of MCS rates supported by the station.
        timestamp : str
            Timestamp in hex at which the station connected to the AP.
        """

        self._accesspoint = ap
        self._loop = ap.loop
        self._radio = radio
        self._mac_addr = mac_addr
        self._supp_rates = supp_rates
        self._airtimes_ns = airtimes_ns
        self._last_seen = timestamp
        self._overhead_mcs = overhead_mcs
        self._overhead_legacy = overhead_legacy
        self._ampdu_enabled = False
        self._ampdu_packets = 0
        self._ampdu_len = 0
        self._avg_ampdu_len = 0
        self._stats = {}
        self._rssi = 1
        self._rssi_vals = []
        self._rate_control_algorithm = rc_alg
        self._rate_control_options = rc_opts
        self._rc = None
        self._log = logger if logger else logging.getLogger()

    @property
    def last_seen(self) -> str:
        return self._last_seen

    @property
    def accesspoint(self):
        return self._accesspoint

    @accesspoint.setter
    def accesspoint(self, ap):
        self._accesspoint = ap

    @property
    def radio(self) -> str:
        return self._radio

    @radio.setter
    def radio(self, radio):
        self._radio = radio

    @property
    def ampdu_packets(self) -> int:
        return self._ampdu_packets

    @ampdu_packets.setter
    def ampdu_packets(self, packet_count):
        self._ampdu_packets = packet_count

    @property
    def ampdu_len(self) -> int:
        return self._ampdu_len

    @ampdu_len.setter
    def ampdu_len(self, length):
        self._ampdu_len = length

    @property
    def avg_ampdu_len(self):
        return self._avg_ampdu_len

    @avg_ampdu_len.setter
    def avg_ampdu_len(self, avg_length):
        self._avg_ampdu_len = avg_length

    @property
    def ampdu_enabled(self) -> bool:
        return self._ampdu_enabled

    @ampdu_enabled.setter
    def ampdu_enabled(self, enabled: bool):
        self._ampdu_enabled = enabled

    @property
    def overhead_mcs(self):
        return self._overhead_mcs

    @property
    def overhead_legacy(self):
        return self._overhead_legacy

    @property
    def supp_rates(self) -> list:
        return self._supp_rates

    @property
    def airtimes_ns(self) -> list:
        return self._airtimes_ns

    @property
    def mac_addr(self) -> str:
        return self._mac_addr

    @property
    def stats(self) -> dict:
        return self._stats

    @property
    def rate_control(self):
        return (self._rate_control_algorithm, self._rate_control_options)

    def __repr__(self):
        return f"STA[{self._mac_addr}]"

    def stop_rate_control(self):
        if not self._rate_control_algorithm:
            return

        self._log.info(
            f"{self}: Stop rate control algorithm '{self._rate_control_algorithm}', "
            f"options={self._rate_control_options}"
        )

        if self._rc:
            self._rc.cancel()
            try:
                self._loop.run_until_complete(self._rc)
            except:
                pass

        self._rc = None
        self._rate_control_algorithm = None
        self._rate_control_options = None

    # TODO: only handle user space rc in this function?
    def start_rate_control(self, rc_alg, rc_opts):
        """
        Put this STA under the given rate control algorithm. 
        '''
        Parameters
        ----------
        rc_alg : str
            The name of the rate control algorithm
        rc_opts : dict
            Configuration options specific to the rate control algorithm

        This function will raise a rateman.RateControlError if there is an error loading the rate
        control algorithm. It will also raise a rateman.RateControlConfigError if the configuration
        of the AP's radio does not permit the rate control algorithm to run, e.g. because the radio
        is not in the required mode (auto/manual).
        """

        if self._rate_control_algorithm == rc_alg and self._rate_control_options == rc_opts:
            return

        ap = self._accesspoint

        if rc_alg == "minstrel_ht_kernel_space":
            if ap.get_radio_mode(self._radio) == "manual":
                raise RateControlConfigError(self, rc_alg, f"{self._radio} not in auto mode")

            self._log.info(f"{self}: Start rate control algorithm '{rc_alg}', options={rc_opts}")

            self._rate_control_algorithm = rc_alg
            self._rate_control_options = rc_opts
            return

        elif ap.get_radio_mode(self._radio) == "auto":
            raise RateControlConfigError(self, rc_alg, f"PHY '{self._radio}' not in manual mode")

        elif self._rate_control_algorithm != None:
            raise RateControlConfigError(
                self,
                rc_alg,
                f"Rate control algorithm '{self._rate_control_algorithm}' must be stopped first"
            )

        self._log.info(f"{self}: Start rate control algorithm '{rc_alg}', options={rc_opts}")
    
        rc = rate_control.load(rc_alg)

        self._rate_control_algorithm = rc_alg
        self._rate_control_options = rc_opts
        self._rc = self._loop.create_task(
            rc(self._accesspoint, self, logger=self._log, **rc_opts),
            name=f"rc_{self._accesspoint.name}_{self._radio}_{self._mac_addr}_{rc_alg}"
        )

        return self._rc

    def lowest_supp_rate(self):
        return self._supp_rates[0]

    def update_stats(self, timestamp, info: dict) -> None:
        """
        Update packet transmission attempts and success statistics.
        '''
        Parameters
        ----------
        timestamp : str
            Timestamp in hex at stats are updated.
        info : dict
            Key-value pairs with rates and their corresponding stats.

        """
        if timestamp > self._last_seen:
            for rate, stats in info.items():
                self._stats[rate] = stats
            self._last_seen = timestamp

    def update_rssi(self, timestamp, min_rssi, per_antenna):
        if timestamp > self._last_seen:
            self._rssi = min_rssi
            self._rssi_vals = per_antenna

    def check_rate_entry(self, rate):
        """


        Parameters
        ----------
        rate : TYPE
            DESCRIPTION.

        Returns
        -------
        TYPE
            DESCRIPTION.

        """
        return rate in self._stats

    def get_attempts(self, rate):
        """
        Get count of packet transmission attempts for the a give rate.

        Parameters
        ----------
        rate : str
            MCS rate index.

        Returns
        -------
        int
            Latest count of packet transmission attempts for a given rate.

        """
        return self._stats[rate]["attempts"]

    def get_successes(self, rate):
        """
        Get count of packet transmission successes for the a give rate.

        Parameters
        ----------
        rate : str
            MCS rate index.

        Returns
        -------
        int
            Latest count of packet transmission successes for a given rate.

        """
        return self._stats[rate]["success"]

    def reset_stats(self) -> None:
        """
        Reset packet transmission attempts and success statistics over all
        rates.

        """
        self._stats = {}

    def __str__(self):
        return f"STA[{self._mac_addr}]"
