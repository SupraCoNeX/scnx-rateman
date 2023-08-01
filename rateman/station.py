# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

import asyncio
import logging
from contextlib import suppress
from functools import partial

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
        tpc_mode: str,
        supported_rates: list,
        airtimes_ns: int,
        overhead_mcs: int,
        overhead_legacy: int,
        rc_alg="minstrel_ht_kernel_space",
        rc_opts=None,
        logger=None
    ):
        self._mac_addr = mac_addr
        self._accesspoint = ap
        self._loop = ap.loop
        self._radio = radio
        self._iface = iface
        self._supported_rates = supported_rates
        self._airtimes_ns = airtimes_ns
        self._last_seen = timestamp
        self._rc_mode = rc_mode
        self._tpc_mode = tpc_mode
        self._overhead_mcs = overhead_mcs
        self._overhead_legacy = overhead_legacy
        self._ampdu_enabled = False
        self._ampdu_aggregates = 0
        self._ampdu_subframes = 0
        self._stats = {}
        self.reset_rate_stats()
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
    def accesspoint(self) -> AccessPoint:
        """
        Return the accesspoint this station is connected to.
        """
        return self._accesspoint

    @property
    def radio(self) -> str:
        """
        Return the name of the radio (PHY) at the AP where this station is connected.
        """
        return self._radio

    @property
    def interface(self) -> str:
        """
        Return the virtual interface on the AP to which this station is connected.
        """
        return self._iface

    @property
    def ampdu_aggregates(self) -> int:
        """
        Return the number of AMPDU aggregate frames sent to the station.
        """
        return self._ampdu_aggregates

    @property
    def ampdu_subframes(self) -> int:
        """
        Return the total number of sub-frames sent in AMPDU aggreagate frames to the station.
        """
        return self._ampdu_subframes

    @property
    def ampdu_enabled(self) -> bool:
        """
        Return `True` if AMPDU is enabled for the station, `False` otherwise.
        """
        return self._ampdu_enabled

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
        return self._supported_rates

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

    def disassociate(self):
        self._radio = None
        self._accesspoint = None

    async def stop_rate_control(self):
        if not self._rate_control_algorithm:
            return

        self._log.debug(
            f"{self}: Stop rate control algorithm '{self._rate_control_algorithm}', "
            f"options={self._rate_control_options}"
        )

        if self._rc:
            self._rc.cancel()
            with suppress(asyncio.CancelledError):
                await self._rc
                result = self._rc.result()

        self._rc = None
        self._rate_control_algorithm = None
        self._rate_control_options = None

    async def start_rate_control(self, rc_alg: str, rc_opts: dict) -> asyncio.Task:
        """
        Put this STA under the given rate control algorithm. The algorithm is identified by its
        module name, which will be used to try and import the module. The module is expected to
        expose `configure()` and `run()` functions.
        `configure()` takes as arguments the `Station` object and the rate control configuration
        options and can return an arbitrary object. It is expected to configure the Station in a way
        that is appropriate for the rate control algorithm. The core operation of the rate control
        algorithm is expedted to happen in `run()`, which takes as its sole argument the object that
        `configure()` returned.

        This function will raise a `rateman.RateControlError` if there is an error loading the rate
        control algorithm's Python module.
        '''
        Parameters
        ----------
        rc_alg : str
            The name of the rate control algorithm
        rc_opts : dict
            Configuration options specific to the rate control algorithm.
        """

        if self._rate_control_algorithm == rc_alg and self._rate_control_options == rc_opts:
            return

        if self._rate_control_algorithm:
            await self.stop_rate_control()

        self._log.debug(f"{self}: Start rate control algorithm '{rc_alg}', options={rc_opts}")

        if rc_alg == "minstrel_ht_kernel_space":
            await self.set_manual_rc_mode(False)
            await self.set_manual_tpc_mode(False)

            rc_task = None
        else:
            configure, rc = rate_control.load(rc_alg)
            ctx = await configure(self, **rc_opts)

            self._rc = self._loop.create_task(rc(ctx), name=f"rc_{self._mac_addr}_{rc_alg}")
            rc_task = self._rc
            rc_task.add_done_callback(partial(handle_rc_exception, self))

        self._rate_control_algorithm = rc_alg
        self._rate_control_options = rc_opts

        return rc_task

    @property
    def lowest_supported_rate(self):
        return self._supported_rates[0]

    def update_rate_stats(self, timestamp: int, rate: str, txpwr: int, attempts: int, succ: int):
        if rate == "110" or timestamp < self._last_seen:
            return

        self._last_seen = timestamp

        if not txpwr:
            txpwr = -1

        self._stats[rate][txpwr]["attempts"] += attempts
        self._stats[rate][txpwr]["success"] += succ
        self._stats[rate][txpwr]["timestamp"] = timestamp

        # If the station is not in manual TPC mode, i.e., the driver decides on TX power, we
        # also update the counters for the TX power index -1, which is the index to set for letting
        # the driver make the transmit power decision. This is done because user space rate control
        # algorithms that do not set TX power will fetch the stats at txpwr == -1.
        if self._tpc_mode == "auto" and txpwr != -1:
            self._stats[rate][-1]["attempts"] += attempts
            self._stats[rate][-1]["success"] += succ
            self._stats[rate][-1]["timestamp"] = timestamp

    def update_ampdu(self, num_frames):
        self._ampdu_enabled = (num_frames > 1)
        if not self._ampdu_enabled:
            return

        self._ampdu_subframes += num_frames
        self._ampdu_aggregates += 1

    def update_rssi(self, timestamp, min_rssi, per_antenna):
        if timestamp > self._last_seen:
            self._rssi = min_rssi
            self._rssi_vals = per_antenna

    def get_rate_stats(self, rate: str) -> dict:
        return self._stats.get(rate, {})

    def reset_rate_stats(self) -> None:
        """
        Reset packet transmission attempts and success statistics for all supported rates and
        transmit power levels.

        """
        self._stats = {
            rate: {
                txpwr: {"attempts": 0, "success": 0, "timestamp": 0}
                for txpwr in [-1] + self._accesspoint.get_txpowers(self._radio)
            }
            for rate in self._supported_rates
        }

    async def reset_kernel_rate_stats(self) -> None:
        """
        Reset counters for attempted and successful transmission in the kernel of this station's
        access point.
        """
        await self._accesspoint.reset_kernel_rate_stats(radio=self._radio, sta=self._mac_addr)

    async def set_manual_rc_mode(self, enable: bool) -> None:
        if enable == (self._rc_mode == "manual"):
            return

        mode = "manual" if enable else "auto"
        await self._accesspoint.send(self._radio, f"rc_mode;{self._mac_addr};{mode}")
        self._rc_mode = mode
        self._log.debug(f"{self}: set rc_mode={mode}")

    async def set_manual_tpc_mode(self, enable: bool) -> None:
        if enable == self._tpc_mode == "manual":
            return

        mode = "manual" if enable else "auto"
        await self._accesspoint.send(self._radio, f"tpc_mode;{self._mac_addr};{mode}")
        self._tpc_mode = mode
        self._log.debug(f"{self}: set tpc_mode={mode}")

    async def set_rates(self, rates: list, counts: list) -> None:
        if len(rates) != len(counts):
            raise ValueError(f"Number of rates and counts must be identical!")

        if self._rc_mode != "manual":
            raise StationModeError(self, "Need to be in manual rate control mode to set rates")

        mrr = ";".join([f"{r},{c}" for (r, c) in zip(rates, counts)])
        await self._accesspoint.send(self._radio, f"set_rates;{self._mac_addr};{mrr}")

    async def set_power(self, pwrs: list) -> None:
        if self._tpc_mode != "manual":
            raise StationModeError(self, "Need to be in manual power control mode to set tx power")

        txpwrs = ";".join([str(p) for p in pwrs])
        await self._accesspoint.send(self._radio, f"set_power;{self._mac_addr};{txpwrs}")

    async def set_rates_and_power(self, rates: list, counts: list, pwrs: list) -> None:
        if not (len(rates) == len(counts) == len(pwrs)):
            raise ValueError(f"Number of rates, counts, and tx_powers must be identical!")

        if not (self._rc_mode == "manual" and self._tpc_mode == "manual"):
            raise StationModeError(
                self,
                "Need to be in manual rate and power control mode to set rates and tx power"
            )

        mrr = ";".join([f"{r},{c},{p}" for ((r, c), p) in zip(zip(rates, counts), pwrs)])
        await self._accesspoint.send(self._radio, f"set_rates_power;{self._mac_addr};{mrr}")

    async def set_probe_rate(self, rate: str, count: int, txpwr: int = None) -> None:
        if rate not in self._supported_rates:
            raise ValueError(f"{self}: Cannot probe '{rate}': Not supported")

        if self._rc_mode != "manual":
            raise StationModeError(self, "Need to be in manual rate control mode to sample a rate")

        cmd = f"set_probe;{self._mac_addr};{rate},{count}"

        if txpwr and txpwr != -1:
            cmd += f",{txpwr}"

        await self._accesspoint.send(self._radio, cmd)

    def __str__(self):
        return f"STA[{self._mac_addr}]"


def handle_rc_exception(sta, future, **kwargs):
    exception = future.exception()
    rc_alg, _ = sta.rate_control

    sta.logger.error(f"{sta}: Rate control '{rc_alg}' raised an exception: {exception.__repr__()}")
    sta._rc = sta._loop.create_task(cleanup_failed_rc(sta))


async def cleanup_failed_rc(sta):
    sta._rc = None
    sta._rate_control_algorithm = None
    sta._rate_control_options = None
    await sta.start_rate_control("minstrel_ht_kernel_space", None)
