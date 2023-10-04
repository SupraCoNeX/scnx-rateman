# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

import asyncio
import logging
import weakref
from contextlib import suppress
from functools import partial
from . import rate_control
from .exception import (
    RateControlError,
    RateControlConfigError,
    StationError,
    RadioError
)


__all__ = ["Station"]


class Station:
    """
    :class:`.Station` objects represent a device which is connected wirelessly to a device
    represented by an instance of :class:`.AccessPoint`. Consequently, since the the
    :class:`.AccessPoint` acts as the transmitter for data for the station, this is where
    transmission resource control tasks place. The ORCA system allows users to perform transmit rate
    and power control on a per-station basis. Consequently, this class is the main interaction point
    for resource control schemes.
    """
    def __init__(
        self,
        mac_addr: str,
        ap,
        radio: str,
        iface: str,
        timestamp: int,
        rc_mode: str,
        update_freq: int,
        sample_freq: int,
        tpc_mode: str,
        supported_rates: list,
        airtimes_ns: list,
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
        self._kernel_update_freq = update_freq
        self._kernel_sample_freq = sample_freq
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
        self._rc_module = None
        self._rc_ctx = None
        self._rc_pause_on_disassoc = False
        self._log = logger if logger else logging.getLogger()

    @property
    def loop(self):
        return self._loop

    @property
    def logger(self) -> logging.Logger:
        return self._log

    @property
    def last_seen(self) -> int:
        """
        Return the timestamp of the last known activity of the station given in nanoseconds since
        1970/1/1 00:00:00.
        """
        return self._last_seen

    @property
    def accesspoint(self) -> "AccessPoint":
        """
        Return the accesspoint to which the station is connected.
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
        Return the name of the virtual interface on the AP to which this station is connected.
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
        """
        Return the station's currently active `rc_mode` (`auto` or `manual`).
        """
        return self._rc_mode

    @property
    def kernel_stats_update_freq(self) -> int:
        """
        Return the frequency, with which the kernel rate statistics for this station get updated on
        the remote device.
        """
        return self._kernel_update_freq

    async def set_kernel_stats_update_freq(self, freq: int) -> None:
        """
        Set the frequency, at wich the kernel rate statistics for this station will be updated on
        the remote device.
        """
        if freq > 100:
            freq = 100

        self._kernel_update_freq = freq

        # the stats update frequency is effectively a lower bound to the sampling frequency due to
        # the way kernel Minstrel-HT is implemented
        if self._kernel_sample_freq < freq:
            self._kernel_sample_freq = freq

        await self._accesspoint.send(
            self._radio,
            f"rc_mode;{self._mac_addr};{self._rc_mode};{freq:x};{self._kernel_sample_freq:x}"
        )

    @property
    def kernel_sample_freq(self) -> int:
        """
        Return the frequency, with which the kernel implementation of Minstrel-HT samples new rates
        for this station. Only applies if `rc_mode=auto`.
        """
        return self._kernel_sample_freq

    async def set_kernel_sample_freq(self, freq: int) -> None:
        """
        Set the frequency, at wich the kernel Minstrel-HT implementation samples rates
        (if `rc_mode=auto`).
        """
        if freq > 100:
            freq = 100

        if freq < self._kernel_update_freq:
            freq = self._kernel_update_freq

        self._kernel_sample_freq = freq
        await self._accesspoint.send(
            self._radio,
            f"rc_mode;{self._mac_addr};{self._rc_mode};{self._kernel_update_freq:x};{freq:x}"
        )

    @property
    def tpc_mode(self) -> str:
        """
        Return the station's currently active `tpc_mode` (`auto` or `manual`).
        """
        return self._tpc_mode

    @property
    def overhead_mcs(self):
        """
        Return the overhead time for frames sent at MCS rates in nanoseconds.
        """
        return self._overhead_mcs

    @property
    def overhead_legacy(self):
        """
        Return the overhead time for frames sent at legacy rates in nanoseconds.
        """
        return self._overhead_legacy

    @property
    def supported_rates(self) -> list:
        """
        Return a list of all the transmission rates this station supports.
        """
        return self._supported_rates

    @property
    def airtimes_ns(self) -> list:
        return self._airtimes_ns

    @property
    def mac_addr(self) -> str:
        """
        Return the station's MAC address
        """
        return self._mac_addr

    @property
    def stats(self) -> dict:
        return self._stats

    @property
    def rate_control(self) -> tuple:
        """
        Return a tuple `(rc_alg, rc_opts)` where `rc_alg` is the name (`str`) of the rc algorithm
        controlling this station at the moment, and `rc_opts` is the `dict` with the configuration
        options it was started with.
        """
        return (self._rate_control_algorithm, self._rate_control_options)

    @property
    def pause_rc_on_disassoc(self):
        return self._rc_pause_on_disassoc

    @pause_rc_on_disassoc.setter
    def pause_rc_on_disassoc(self, val: bool):
        self._rc_pause_on_disassoc = val

    @property
    def log(self) -> logging.Logger:
        return self._log

    def __repr__(self):
        return f"STA[{self._mac_addr}]"

    def disassociate(self):
        self._radio = None
        self._accesspoint = None

    async def stop_rate_control(self):
        """
        Stop the user space rc algorithm controlling transmit rates and power for the station.
        """
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

        This function will raise a :class:`.RateControlError` if there is an error loading the rate
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
            if rc_opts:
                if rc_opts.get("reset_rate_stats", False):
                    await self.reset_kernel_rate_stats()
                    self.reset_rate_stats()

                if "update_freq" in rc_opts:
                    await self.set_kernel_stats_update_freq(rc_opts["update_freq"])

                if "sample_freq" in rc_opts:
                    await self.set_kernel_sample_freq(rc_opts["sample_freq"])
        else:
            self._rc_module = rate_control.load(rc_alg)

            configure = self._rc_module.configure
            run = self._rc_module.run

            self._rc_ctx = await configure(self, **rc_opts)

            self._rc = self._loop.create_task(run(self._rc_ctx), name=f"rc_{self._mac_addr}_{rc_alg}")
            self._rc.add_done_callback(partial(handle_rc_exception, self))

        self._rate_control_algorithm = rc_alg
        self._rate_control_options = rc_opts

        return self._rc

    async def pause_rate_control(self):
        if not self._rc_module.pause:
            raise RateControlConfigError(
                self,
                self._rate_control_algorithm,
                "Trying to pause rate control scheme that does not support pause/resume."
            )

        self._log.debug(f"{self}: Pause rate control {self._rate_control_algorithm}")
        await self._rc_module.pause(self._rc_ctx)

        # Attach a callback to clean up the paused RC task in case the STA object gets garbage
        # collected before the RC task is finished.
        weakref.finalize(self, cleanup_sta_rc, self)

    async def resume_rate_control(self):
        if not self._rc_module.resume:
            raise RateControlConfigError(
                self,
                self._rate_control_algorithm,
                "Trying to resume rate control scheme that does not support pause/resume."
            )

        self._log.debug(f"{self}: Resume rate control {self._rate_control_algorithm}")
        await self._rc_module.resume(self._rc_ctx)

    @property
    def lowest_supported_rate(self):
        """
        Return the index of the slowest rate that this station supports.
        """
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

    def reset_ampdu_stats(self):
        self._ampdu_subframes = 0
        self._ampdu_aggregates = 0

    def update_ampdu(self, num_frames: int):
        if num_frames > 1:
            self._ampdu_enabled = True

        self._ampdu_subframes += num_frames
        self._ampdu_aggregates += 1

    def update_rssi(self, timestamp: int, min_rssi: int, per_antenna: int):
        if timestamp > self._last_seen:
            self._rssi = min_rssi
            self._rssi_vals = per_antenna

    def get_rate_stats(self, rate: str) -> dict:
        """
        Return the statistics for the given rate. The returned dictionary includes the keys
        `attempts`, `success`, and `timestamp` keyed by transmit power levels. `attempts` counts the
        total number of transmissions attempted at the given rate for the given power level, while
        `success` counts the number of successful transmissions. `timestamp` gives the time of the
        last attempt made at the given rate and power level in nanoseconds since 1970/1/1 00:00:00.
        """
        return self._stats.get(rate, {})

    def reset_rate_stats(self):
        """
        Reset packet transmission attempts and success statistics for all supported rates and
        transmit power levels.
        """
        self._stats = {
            rate: {
                txpwr: {"attempts": 0, "success": 0, "timestamp": 0}
                for txpwr in [-1] + self._accesspoint.txpowers(self._radio)
            }
            for rate in self._supported_rates
        }

    async def reset_kernel_rate_stats(self):
        """
        Reset counters for attempted and successful transmission in the kernel of this station's
        access point.
        """
        await self._accesspoint.reset_kernel_rate_stats(radio=self._radio, sta=self._mac_addr)

    async def set_manual_rc_mode(self, enable: bool):
        """
        Configure the station's rate control mode. If `enable` is `True`, the station will be
        switched into manual rc mode. If `enable` is `False`, the station will be put into auto rc
        mode.
        """
        if enable == (self._rc_mode == "manual"):
            return

        mode = "manual" if enable else "auto"
        await self._accesspoint.send(self._radio, f"rc_mode;{self._mac_addr};{mode}")
        self._rc_mode = mode
        self._log.debug(f"{self}: set rc_mode={mode}")

    async def set_manual_tpc_mode(self, enable: bool):
        """
        Configure the station's transmit power control mode. If `enable` is `True`, the station will
        be switched into manual tpc mode. If `enable` is `False`, the station will be put into auto
        tpc mode.
        This function will raise a `RadioError` if either the radio serving the station does not
        support transmit power control or the TPC feature is disabled.
        """
        if enable == self._tpc_mode == "manual":
            return

        if enable:
            if not self._accesspoint.txpowers(self._radio):
                raise RadioError(self._accesspoint, self._radio, "TX power control not supported")
            elif not self._accesspoint._radios[self._radio]["features"].get("tpc", True):
                raise RadioError(self._accesspoint, self._radio, "TPC is disabled")

        mode = "manual" if enable else "auto"
        if self._accesspoint.radios[self._radio]['tpc']:
            await self._accesspoint.send(self._radio, f"tpc_mode;{self._mac_addr};{mode}")
            self._tpc_mode = mode
            self._log.debug(f"{self}: set tpc_mode={mode}")

    def _validate_txpwrs(self, pwrs: list[int]):
        supported_pwrs = self._accesspoint.txpowers(self._radio)
        for p in pwrs:
            if p not in supported_pwrs:
                raise RadioError(self._accesspoint, self._radio, f"Unsupported TX power level: {p}")

    def _validate_rates(self, rates: list[int]):
        for r in rates:
            r_str = str(r)

            if len(r_str) == 1:
                r_str = "0" + r_str

            if r_str not in self._supported_rates:
                raise StationError(self, f"Unsupported rate: {r}")

    async def set_rates(self, rates: list[int], counts: list[int]):
        """
        Set the station's rate table, i.e., the rates at which transmissions will be attempted and
        their respective retry counts. Given the hardware's support, transmissions to this station
        will be attempted at the rates identified by the indices in `rates` for however many
        attempts are set in `counts` until either transmission succeeds or all attempts have been
        exhausted. This function will raise a `ValueError` if `rates` and `counts` differ in length,
        and a `StationError` if the station is not in manual rc mode.
        """
        if len(rates) != len(counts):
            raise ValueError(f"Number of rates and counts must be identical!")

        if self._rc_mode != "manual":
            raise StationError(self, "Need to be in manual rate control mode to set rates")

        self._validate_rates(rates)

        mrr = ";".join([f"{r},{c}" for (r, c) in zip(rates, counts)])
        await self._accesspoint.send(self._radio, f"set_rates;{self._mac_addr};{mrr}")

    async def set_power(self, pwrs: list[int]):
        """
        Set the transmit power levels for the station's rate table. Given the hardware's support,
        this will prescribe which transmit power level is to be used at every stage of the retry
        chain when transmitting to this station.
        This function will raise a `RadioError` if the radio serving the station does not support
        transmit power control, and a`StationError` if the station is not in manual tpc mode.
        """
        if not self._accesspoint.txpowers(self._radio):
            raise RadioError(self._accesspoint, self._radio, "TX power control not supported")

        if self._tpc_mode != "manual":
            raise StationError(self, "Need to be in manual power control mode to set TX power")

        self._validate_txpwrs(pwrs)

        txpwrs = ";".join([f"{self._accesspoint.txpowers(self._radio).index(p):x}" for p in pwrs])
        await self._accesspoint.send(self._radio, f"set_power;{self._mac_addr};{txpwrs}")

    async def set_rates_and_power(self, rates: list[int], counts: list[int], pwrs: list[int]):
        """
        Set rates, retry counts, and transmit power levels for transmissions made to this station.
        This combines the effects of `set_rates()` and `set_power()`.
        This fucntion will raise a `ValueError` of `rates`, `counts`, and `pwrs` differ in length,
        and a `StationError` if the station is not in manual rc and manual tpc mode. If the radio
        serving this station does not support transmit power control, this function will raise a
        `RadioError`.
        """
        if not (len(rates) == len(counts) == len(pwrs)):
            raise ValueError(f"Number of rates, counts, and tx_powers must be identical!")

        if not self._accesspoint.txpowers(self._radio):
            raise RadioError(self._accesspoint, self._radio, "TX power control not supported")

        if not (self._rc_mode == "manual" and self._tpc_mode == "manual"):
            raise StationError(
                self,
                "Need to be in manual rate and power control mode to set rates and TX power"
            )

        self._validate_rates(rates)
        self._validate_txpwrs(pwrs)

        supported_pwrs = self._accesspoint.txpowers(self._radio)
        txpwrs = [supported_pwrs.index(p) for p in pwrs]
        mrr = ";".join([f"{r},{c},{p:x}" for ((r, c), p) in zip(zip(rates, counts), txpwrs)])
        await self._accesspoint.send(self._radio, f"set_rates_power;{self._mac_addr};{mrr}")

    async def set_probe_rate(self, rate: str, count: int, txpwr: int = None):
        """
        Sample a rate identified by its index `rate` for `count` attempts at transmit power level
        `txpwr`. This overwrite the first entry in the rate table for the station with the given
        values.
        This function will raise a `ValueError` if `rate` is not supported by the station, and a
        `StationError` if the station is not in manual rc mode. It will also raise a `StationError`
        if `txpwr` is not `None` and the station is not in manual tpc mode.
        """
        if rate not in self._supported_rates:
            raise ValueError(f"{self}: Cannot probe '{rate}': Not supported")

        if self._rc_mode != "manual":
            raise StationError(self, "Need to be in manual rate control mode to sample a rate")

        if txpwr and self._tpc_mode != "manual":
            raise StationError(self, "Need to be in manual transmit power control mode to set "
                               "tpc for a probe rate")

        self._validate_rates([rate])

        cmd = f"set_probe;{self._mac_addr};{rate},{count}"

        if txpwr and txpwr != -1:
            self._validate_txpwrs([txpwr])

            supported_pwrs = self._accesspoint.txpowers(self._radio)

            cmd += f",{supported_pwrs.index(txpwr):x}"

        await self._accesspoint.send(self._radio, cmd)

    def __str__(self):
        return f"STA[{self._mac_addr}]"


def handle_rc_exception(sta: Station, future):
    try:
        exception = future.exception()
    except asyncio.CancelledError:
        return

    if not exception:
        return

    rc_alg, _ = sta.rate_control

    sta.log.error(f"{sta}: Rate control '{rc_alg}' raised an exception: {exception.__repr__()}")
    sta.loop.create_task(cleanup_failed_rc(sta))


async def cleanup_failed_rc(sta: Station):
    await sta.stop_rate_control()


def cleanup_sta_rc(sta: Station):
    sta.loop.create_task(cleanup_failed_rc(sta))
