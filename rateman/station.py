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

from .accesspoint import AccessPoint
from . import rate_control
from .exception import RateControlError, RateControlConfigError, StationModeError

__all__ = ["Station"]


class Station:
    def __init__(
        self,
        mac_addr: str,
        ap: AccessPoint,
        radio: str,
        iface: str,
        timestamp: int,
        rc_mode: str,
        tpc_mode:str,
        supp_rates: list,
        airtimes_ns: int,
        overhead_mcs: int,
        overhead_legacy: int,
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
            MCS rates supported by the station.
        timestamp : str
            Timestamp in hex at which the station connected to the AP.
        """

        self._mac_addr = mac_addr
        self._accesspoint = ap
        self._loop = ap.loop
        self._radio = radio
        self._iface = iface
        self._supp_rates = supp_rates
        self._airtimes_ns = airtimes_ns
        self._last_seen = timestamp
        self._rc_mode = rc_mode
        self._tpc_mode = tpc_mode
        self._overhead_mcs = overhead_mcs
        self._overhead_legacy = overhead_legacy
        self._ampdu_enabled = False
        self._ampdu_packets = 0
        self._ampdu_len = 0
        self._avg_ampdu_len = 0
        self._stats = dict.fromkeys(
            supp_rates,
            dict.fromkeys(
                [-1] + ap.get_txpowers(radio),
                {"attempts": 0, "success": 0, "timestamp": timestamp}
            )
        )
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

    @property
    def radio(self) -> str:
        return self._radio

    @property
    def interface(self) -> str:
        return self._iface

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
    def rc_mode(self) -> str:
        return self._rc_mode

    @property
    def tpc_mode(self) -> str:
        return self._tpc_mode

    @property
    def overhead_mcs(self):
        return self._overhead_mcs

    @property
    def overhead_legacy(self):
        return self._overhead_legacy

    @property
    def supported_rates(self) -> list:
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

    @property
    def logger(self) -> logging.Logger:
        return self._log

    def __repr__(self):
        return f"STA[{self._mac_addr}]"

    async def stop_rate_control(self):
        if not self._rate_control_algorithm:
            return

        self._log.debug(
            f"{self}: Stop rate control algorithm '{self._rate_control_algorithm}', "
            f"options={self._rate_control_options}"
        )

        if self._rc:
            self._rc.cancel()
            try:
                await self._rc
            except (asyncio.CancelledError, StationModeError):
                pass

        self._rc = None
        self._rate_control_algorithm = None
        self._rate_control_options = None

    # TODO: only handle user space rc in this function?
    def start_rate_control(self, rc_alg: str, rc_opts: dict) -> asyncio.Task:
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
        control algorithm. It will also raise a rateman.RateControlConfigError if the station is not
        in the appropriate rate control mode, i.e., auto for kernel minstrel-ht and manual for user
        space rate control.
        """

        if self._rate_control_algorithm == rc_alg and self._rate_control_options == rc_opts:
            return

        if rc_alg == "minstrel_ht_kernel_space":
            if self._rc_mode == "manual":
                raise RateControlConfigError(self, rc_alg, "Not in auto rate control mode")

            self._log.debug(f"{self}: Start rate control algorithm '{rc_alg}', options={rc_opts}")

            self._rate_control_algorithm = rc_alg
            self._rate_control_options = rc_opts
            return None

        elif self._rc_mode == "auto":
            raise RateControlConfigError(self, rc_alg, "Not in manual rate control mode")

        elif self._rate_control_algorithm != None:
            raise RateControlConfigError(
                self,
                rc_alg,
                f"Rate control algorithm '{self._rate_control_algorithm}' must be stopped first"
            )

        self._log.debug(f"{self}: Start rate control algorithm '{rc_alg}', options={rc_opts}")
    
        configure, rc = rate_control.load(rc_alg)

        self._rate_control_algorithm = rc_alg
        self._rate_control_options = rc_opts

        ctx = await configure(self)

        self._rc = self._loop.create_task(rc(ctx), name=f"rc_{self._mac_addr}_{rc_alg}")

        return self._rc

    @property
    def lowest_supp_rate(self):
        return self._supp_rates[0]

    def reset_rate_stats(self, rate):
        if rate in self._stats:
            for txpwr in self._stats[rate]:
                self._stats[rate][txpwr] = {
                    "attempts": 0,
                    "success": 0,
                    "timestamp": 0
                }

    def update_rate_stats(self, timestamp: int, rate: str, txpwr: int, atmpts: int, succ: int):
        if timestamp < self._last_seen:
            return

        self._last_seen = timestamp

        if not txpwr:
            txpwr = -1

        if rate not in self._stats:
            self._stats[rate] = {}
            self._stats[rate][txpwr] = {
                "attempts": 0,
                "success": 0
            }

        if txpwr not in self._stats[rate]:
            return

        self._stats[rate][txpwr]["attempts"] += atmpts
        self._stats[rate][txpwr]["success"] += succ

        # If the station is not in manual TPC mode, i.e., the driver decides on TX power, we
        # also update the counters for the TX power index -1, which is the index to set for letting
        # the driver make the transmit power decision. This is done because user space rate control
        # algorithms that do not set TX power will fetch the
        if self._tpc_mode == "auto":
            self._stats[rate][-1]["attempts"] += atmpts
            self._stats[rate][-1]["success"] += succ

    def update_rssi(self, timestamp, min_rssi, per_antenna):
        if timestamp > self._last_seen:
            self._rssi = min_rssi
            self._rssi_vals = per_antenna

    def get_rate_stats(self, rate: str) -> dict:
        return self._stats.get(rate, {})

    def reset_stats(self) -> None:
        """
        Reset packet transmission attempts and success statistics over all
        rates.

        """
        self._stats = {}

    def set_manual_rc_mode(self, enable: bool) -> None:
        if enable == (self._rc_mode == "manual"):
            return

        mode = "manual" if enable else "auto"
        self._accesspoint.send(self._radio, f"rc_mode;{self._mac_addr};{mode}")
        self._rc_mode = mode
        self._log.debug(f"{self}: set rc_mode={mode}")

    def set_manual_tpc_mode(self, enable: bool) -> None:
        if enable == self._tpc_mode == "manual":
            return

        mode = "manual" if enable else "auto"
        self._accesspoint.send(self._radio, f"tpc_mode;{self._mac_addr};{mode}")
        self._tpc_mode = mode
        self._log.debug(f"{self}: set tpc_mode={mode}")

    def set_rates(self, rates: list, counts: list) -> None:
        if len(rates) != len(counts):
            raise ValueError(f"Number of rates and counts must be identical!")

        if self._rc_mode != "manual":
            raise StationModeError(self, "Need to be in manual rate control mode to set rates")

        mrr = ";".join([f"{r},{c}" for (r,c) in zip(rates, counts)])
        self._accesspoint.send(self._radio, f"set_rates;{self._mac_addr};{mrr}")

    def set_power(self, pwrs: list) -> None:
        if self._tpc_mode != "manual":
            raise StationModeError(self, "Need to be in manual power control mode to set tx power")

        txpwrs = ";".join([str(p) for p in pwrs])
        self._accesspoint.send(self._radio, f"set_power;{self._mac_addr};{txpwrs}")

    def set_rates_and_power(self, rates: list, counts: list, pwrs: list) -> None:
        if not (len(rates) == len(counts) == len(pwrs)):
            raise ValueError(f"Number of rates, counts, and tx_powers must be identical!")

        if not (self._rc_mode == "manual" and self._tpc_mode == "manual"):
            raise StationModeError(
                self,
                "Need to be in manual rate and power control mode to set rates and tx power"
            )

        mrr = ";".join([f"{r},{c},{p}" for ((r, c), p) in zip(zip(rates, counts), pwrs)])
        self._accesspoint.send(self._radio, f"set_rates_power;{self._mac_addr};{mrr}")

    def set_probe_rate(self, rate: str, count: int, txpwr: int) -> None:
        if rate not in self._supp_rates:
            raise ValueError(f"{self}: Cannot probe '{rate}': Not supported")

        if self._rc_mode != "manual":
            raise StationModeError(self, "Need to be in manual rate control mode to sample a rate")

        self._accesspoint.send(self._radio, f";set_probe;{self._mac_addr};{rate},{count},{txpwr}")

    def __str__(self):
        return f"STA[{self._mac_addr}]"
