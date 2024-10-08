# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

import asyncio
import csv
import sys
import logging
from functools import reduce

from .station import Station
from .rate_info import *
from .exception import (
    RadioUnavailableError,
    AccessPointNotConnectedError,
    UnsupportedFeatureException,
    AccessPointError,
)

__all__ = ["AccessPoint", "from_file", "from_strings"]


class AccessPoint:
    """
    Objects of this class represent a remote wireless device running an instance of ORCA-RCD to
    which RateMan connects and which it potentially controls. Although the class is called
    `AccessPoint`, the device need not necessary fulfill the role of an access point in the sense
    of the IEEE 802.11 standard (WiFi). As far as RateMan is concerned, it is a wireless device
    whose wireless transmission parameters are controllable using the ORCA system.
    Instances of this class sould be created using :func:`.from_strings` or
    :func:`.from_file`
    """

    def __init__(self, name: str, addr: str, rcd_port=21059, logger=None, loop=None):
        """
        Parameters
        ----------
        name : str
            Name given to the AP.
        addr : str
            IP address of the AP.
        rcd_port : int, optional
            Port over which the Rate Control API is accessed. Defaults to 21059
        logger : logging.Logger
            Log

        """
        self._name = name
        self._api_version = None
        self._addr = addr
        self._rcd_port = rcd_port
        self._all_group_info = dict()
        self._all_rate_info = dict()
        self._radios = dict()
        self._connected = False
        self._latest_timestamp = 0
        self._log = logger if logger else logging.getLogger()
        self._loop = loop
        self._last_cmd = None
        self._reader = None
        self._writer = None
        self._task = None
        self._first_non_header_line = None
        self._record_rcd_trace = False
        self._rcd_trace_file = None
        self._header_collected = False

    async def api_info(self, timeout=0.5):
        it = aiter(self._reader)
        while True:
            try:
                async with asyncio.timeout(timeout):
                    data = await anext(it)
                    line = data.decode("utf-8")

                if line.startswith("*") or ";0;add" in line or ";0;sta" in line:
                    yield line.rstrip()
                else:
                    self._first_non_header_line = data
                    return
            except UnicodeError:
                continue
            except asyncio.TimeoutError:
                return

    async def events(self):
        if self._first_non_header_line:
            line = self._first_non_header_line
            self._first_non_header_line = None
            yield line

        async for data in self._reader:
            try:
                if self._record_rcd_trace:
                    self._rcd_trace_file.write(data.decode("utf-8"))
                yield data
            except UnicodeError:
                continue

    def __str__(self):
        return self._name

    def __repr__(self):
        return f"AP[name={self._name}, addr={self._addr}:{self._rcd_port}]"

    @property
    def name(self) -> str:
        """
        The accesspoint's name.
        """
        return self._name

    @property
    def api_version(self) -> tuple[int, int, int]:
        """
        The ORCA API version supported by the accesspoint.
        """
        return self._api_version

    @property
    def addr(self) -> str:
        """
        The accesspoint's IP address.
        """
        return self._addr

    @property
    def port(self) -> int:
        """
        The port on which the ORCA-RCD instance on the accesspoint listens.
        """
        return self._rcd_port

    @property
    def header_collected(self):
        return self._header_collected

    @header_collected.setter
    def header_collected(self, header_collected):
        self._header_collected = header_collected

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, loop):
        self._loop = loop

    @property
    def logger(self):
        return self._log

    @property
    def connected(self) -> bool:
        """
        Whether rateman is connected to the accesspoint.
        """
        return self._connected

    @connected.setter
    def connected(self, connection_status):
        self._connected = connection_status

    @property
    def radios(self) -> dict:
        """
        The access point's radios dictionary.
        """
        return self._radios

    @property
    def sample_table(self) -> list:
        return self._sample_table

    @sample_table.setter
    def sample_table(self, sample_table_data):
        self._sample_table = [list(map(int, row.split(","))) for row in sample_table_data]

    @property
    def all_group_info(self):
        return self._all_group_info

    def get_rate_info(self, rate: int, attr: str = "") -> dict:
        if rate in self._all_rate_info:
            rate_info = self._all_rate_info[rate]

            if attr in rate_info.keys():
                return rate_info[attr]
            elif attr != "":
                return

            return rate_info

    def start_recording_rcd_trace(self, path):
        """
        Record incoming ORCA events in a file at the given path.
        """
        self.stop_recording_rcd_trace()

        self._rcd_trace_file = open(path, "w")
        self._record_rcd_trace = True

    def stop_recording_rcd_trace(self):
        if self._rcd_trace_file:
            self._rcd_trace_file.close()

        self._rcd_trace_file = None
        self._record_rcd_trace = False

    def stations(self, radio="all") -> list[Station]:
        """
        Return a list of :class:`Station` s of the given radio. If `radio` is `"all"` the returned
        list will include the stations of all of the accesspoint's radios.
        """
        if radio == "all":
            return reduce(
                lambda a, b: a + b, [self.stations(radio=radio) for radio in self._radios], []
            )
        elif radio not in self._radios:
            raise AccessPointError(self, f"No such radio '{radio}'")

        return [sta for _, sta in self._radios[radio]["stations"].items()]

    def _get_sta(self, mac, radio):
        try:
            return self._radios[radio]["stations"][mac]
        except KeyError:
            return None

    def get_sta(self, mac: str, radio: str = None) -> "Station":
        if not radio:
            for radio in self._radios:
                sta = self.get_sta(mac, radio)
                if sta:
                    return sta

            return None

        return self._get_sta(mac, radio)

    def enabled_events(self, radio: str) -> list:
        """
        Return a list of ORCA API events which are currently enabled, i.e., which are being reported
        by the device to which rateman is connected.
        """
        return self._radios[radio]["events"]

    def get_feature_state(self, radio: str, feature: str):
        try:
            if feature not in self._radios[radio]["features"]:
                raise UnsupportedFeatureException(self, radio, feature)

            return self._radios[radio]["features"][feature]
        except KeyError as e:
            raise RadioUnavailableError(self, radio) from e

    def features(self, radio: str) -> list:
        """
        Return the list of supported features of a given radio.
        """
        try:
            return self._radios[radio]["features"].keys()
        except KeyError as e:
            raise RadioUnavailableError(self, radio) from e

    async def _set_feature(self, radio, feature, val):
        try:
            if feature not in self._radios[radio]["features"]:
                raise UnsupportedFeatureException(self, radio, feature)
            elif self._radios[radio]["features"][feature] == val:
                return
        except KeyError as e:
            raise RadioUnavailableError(self, radio) from e

        self._radios[radio]["features"][feature] = val
        await self.send(radio, f"set_feature;{feature};{val}")

    async def set_feature(self, radio: str, feature: str, val: str) -> None:
        """
        Configure a given radio's feature. This will raise a :class:`.RadioUnavailableError` if the
        radio is unknown and a :class:`.UnsupportedFeatureException` if the radio does not support
        the feature.

        Parameters
        ----------
        radio : str
            The radio for which to configure the feature
        feature : str
            The feature to configure
        val : str
            The setting for the feature

        """
        await self._set_feature(radio, feature, val)

    def add_radio(
        self, radio: str, driver: str, ifaces: list, events: list, features: dict, tpc: dict
    ) -> None:
        self._log.debug(
            f"{self._name}: adding radio '{radio}', driver={driver}, "
            f"interfaces={ifaces}, events={events}, "
            f"features={', '.join([f + ':' + s for f, s in features.items()])} "
        )

        if radio not in self._radios:
            self._radios[radio] = {}

        self._radios[radio].update(
            {
                "driver": driver,
                "interfaces": ifaces,
                "events": events,
                "features": features,
                "tpc": tpc,
                "stations": {},
            }
        )

    def radio_for_interface(self, iface: str) -> str:
        """
        Return the radio on which the given virtual interface is running.
        """
        for radio in self._radios:
            if iface in self._radios[radio]["interfaces"]:
                return radio

        return None

    def interfaces(self, radio: str) -> list:
        """
        Return the list of virtual interfaces running on the given radio. Raises a
        :class:`.RadioUnavailableError` if the radio is unknown.
        """
        try:
            return self._radios[radio]["interfaces"]
        except KeyError as e:
            raise RadioUnavailableError(self, radio) from e

    def driver(self, radio: str) -> str:
        """
        Return the name of the given radio's driver. Raises a :class:`.RadioUnavailableError` if the
        radio is unknown.
        """
        try:
            return self._radios[radio]["driver"]
        except KeyError as e:
            raise RadioUnavailableError(f"{self._name}: No such radio '{radio}'") from e

    def txpowers(self, radio: str) -> list:
        """
        Return the list of transmit power levels supported by the given radio. Raises a
        :class:`.RadioUnavailableError` if the radio is unknown.
        """
        if radio not in self._radios:
            raise RadioUnavailableError(self, radio)

        return self._radios[radio]["tpc"]["txpowers"] if self._radios[radio]["tpc"] else []

    async def add_station(self, sta):
        old_sta = self.get_sta(sta.mac_addr)
        if old_sta:
            old_sta.associate(self, sta.radio)

            # The station's supported rate set may have changed while it was disassociated
            old_sta.supported_rates = sta.supported_rates

            if old_sta.rc_paused:
                await old_sta.resume_rate_control()
            return

        if sta.mac_addr not in self._radios[sta.radio]["stations"]:
            self._log.debug(f"{self._name}:{sta.radio}: Adding {sta}")
            self._radios[sta.radio]["stations"][sta.mac_addr] = sta

    async def update_station(self, sta):
        if sta.mac_addr not in self._radios[sta.radio]["stations"]:
            await self.add_station(sta)
            return

        old_sta = sta.accesspoint.get_sta(sta.mac_addr, radio=sta.radio)

        # TODO: do we have to update more than the supported rate set?
        old_sta.supported_rates = sta.supported_rates

    async def remove_station(self, mac: str, radio: str) -> Station:
        try:
            sta = self._radios[radio]["stations"][mac]
        except KeyError:
            return None

        sta.disassociate()

        if sta.pause_rc_on_disassoc:
            await sta.pause_rate_control()
        else:
            self._log.debug(f"{self._name}:{radio}: Removing {sta}")
            del self._radios[radio]["stations"][mac]
            await sta.stop_rate_control()

        return sta

    def update_timestamp(self, timestamp_str):
        try:
            timestamp = int(timestamp_str, 16)
        except Exception:
            return False

        if self._latest_timestamp == 0:
            self._latest_timestamp = timestamp
            return True

        if (
            timestamp > self._latest_timestamp
            and len(timestamp_str) - len(f"{self._latest_timestamp:x}") <= 1
        ):
            self._latest_timestamp = timestamp
            return True

        return False

    async def send(self, radio: str, cmd: str):
        if not self.connected:
            raise AccessPointNotConnectedError(self, f"Cannot send '{cmd}'")

        if radio != "*" and radio not in self._radios:
            raise ValueError(f"{self}: Unknown radio '{radio}'")

        self._last_cmd = cmd
        if cmd[-1] != "\n":
            cmd += "\n"

        self._writer.write(f"{radio};{cmd}".encode("ascii"))

        await self._writer.drain()

    def handle_error(self, error):
        self._log.error(f"{self._name}: Error '{error}', last command='{self._last_cmd}'")

    async def connect(self):
        if self._connected:
            return

        try:
            r, w = await asyncio.open_connection(self._addr, self._rcd_port)
            self._reader = r
            self._writer = w
            self._connected = True
        except asyncio.CancelledError as e:
            self._task = None
            self._connected = False
            raise e
        except Exception as e:
            self._log.error(
                f"{self._name}: Failed to connect at {self._addr}:{self._rcd_port}: {e.__repr__()}"
            )
            self._connected = False
            raise e

        self._log.debug(f"{self._name}: Connected at {self._addr}:{self._rcd_port}")

    async def disconnect(self, timeout=3.0):
        if self._rcd_trace_file:
            self.stop_recording_rcd_trace()

        if not self._writer:
            return

        for radio in self._radios:
            for sta in self.stations(radio):
                rc_alg, _ = sta.rate_control
                if rc_alg != "minstrel_ht_kernel_space":
                    self._log.warning(
                        f"Disconnecting from {self} will leave {sta} without rate control"
                    )
                    await sta.stop_rate_control()

            self._radios[radio]["stations"] = {}

        self._writer.close()

        try:
            async with asyncio.timeout(timeout):
                await self._writer.wait_closed()
        except asyncio.TimeoutError:
            self._log.warning(f"{self._name}: did not disconnect within {timeout}s")

        self._writer = None
        self._connected = False

    async def enable_events(self, radio="all", events: list = ["txs"]) -> None:
        """
        Enable the given events for the given radio. If `radio` is `"*"` or
        `"all"`, the events will be enabled on all the accesspoint's radios.
        """
        if radio in ["all", "*"]:
            radio = "*"
            for r in self._radios:
                enabled_events = set(self._radios[r]["events"])
                enabled_events.update(events)
                self._radios[r]["events"] = list(enabled_events)
        else:
            enabled_events = set(self._radios[radio]["events"])
            enabled_events.update(events)
            self._radios[radio]["events"] = list(enabled_events)

        await self.disable_events(radio)

        self._log.debug(f"{self._name}:{radio}: Enable events {events}")

        await self.send(radio, "start;" + ";".join(events))

    async def disable_events(self, radio="all", events: list = []) -> None:
        """
        Disable the given events for the given radio. If `radio` is `"*"` or
        `"all"`, the events will be disabled on all the accesspoint's radios.
        """
        if radio in ["all", "*"]:
            radio = "*"
            for r in self._radios:
                self._radios[r]["events"] = list(set(self._radios[r]["events"]) - set(events))
        else:
            self._radios[radio]["events"] = list(set(self._radios[radio]["events"]) - set(events))

        self._log.debug(f"{self._name}:{radio}: Disable events {events}")

        await self.send(radio, "stop;" + ";".join(events))

    async def dump_stas(self, radio="all"):
        if radio == "all":
            radio = "*"

        await self.send(radio, "dump")

    async def debugfs_set(self, path, value, radio="all"):
        """
        write the given `value` to the file located in debugfs on the connected device under
        `/sys/kernel/debug/ieee80211/<radio>/<path>`. `path` cannot contain `..` or `.`.
        """
        if radio == "all":
            for radio in self._radios:
                await self.debugfs_set(path, value, radio=radio)
            return

        if radio not in self._radios:
            return

        self._log.debug(f"{self._name}:{radio}: debugfs: setting {path}={value}")
        await self.send(radio, f"debugfs;{path};{value}")

    async def reset_kernel_rate_stats(self, radio="all", sta="all") -> None:
        """
        Reset the rate statistics in the kernel for the given `sta` and `radio` on the remote
        device. `sta` must be either a MAC address or `"all"`. If it is `"all"`, the reset_stats
        command will be executed for all radios. In this case, it does not make sense to supply a
        MAC address for `sta`.
        """
        if radio in ["*", "all"]:
            radio = "*"
        elif radio not in self._radios:
            raise RadioUnavailableError(self, radio)

        if sta == "all":
            self._log.debug(f"{self._name}:{radio}: Resetting in-kernel rate statistics")
            await self.send(radio, f"reset_stats;all")
        elif (
            sta in self._radios[radio]["stations"]
            and self._radios[radio]["stations"][sta].associated
        ):
            self._log.debug(f"{self._name}:{radio}:{sta}: Resetting in-kernel rate statistics")
            await self.send(radio, f"reset_stats;{sta}")

    def add_group_rate_info(self, group_ind, group_info):
        self._all_group_info.update({group_ind: group_info})
        for rate_idx in group_info["rate_inds"]:
            rate = int(rate_idx, 16)
            rate_info = get_rate_info(group_info, rate)
            self._all_rate_info.update({rate: rate_info})

    async def _set_all_stations_mode(self, radio, which, mode):
        if mode not in ["manual", "auto"]:
            raise ValueError(f"Invalid mode '{mode}', must be either 'manual' or 'auto'")

        self._log.debug(f"{self._name}:{radio}: Setting {which} for all stations to {mode}")

        await self.send(radio, f"{which};all;{mode}")

        if radio == "*":
            for r in self._radios:
                for sta in [s for s in self.stations(r) if s.associated]:
                    if which == "rc_mode":
                        sta._rc_mode = mode
                    else:
                        sta._tpc_mode = mode
        else:
            for sta in [s for s in self.stations(radio) if s.associated]:
                if which == "rc_mode":
                    sta._rc_mode = mode
                else:
                    sta._tpc_mode = mode

    async def set_all_stations_rc_mode(self, mode: str, radio="*") -> None:
        """
        Convenience function to set the rc mode for all stations of a given radio or even across
        all radios.
        """
        await self._set_all_stations_mode(radio, "rc_mode", mode)

    async def set_all_stations_tpc_mode(self, mode: str, radio="*") -> None:
        """
        Convenience function to set the tpc mode for all stations of a given radio or even across
        all radios.
        """
        await self._set_all_stations_mode(radio, "tpc_mode", mode)

    async def enable_tprc_echo(self, enable: bool, radio="*") -> None:
        """
        Enable echoing of rc and tpc commands in the form of ORCA API events. This can be useful
        for debugging.
        """
        action = "start" if enable else "stop"
        await self.send(radio, f"{action};tprc_echo")


def from_file(file: dir, logger=None) -> list:
    """
    Parse the given csv file and return a list of :class:.`AccessPoint` objects created according to
    the lines within. Lines must have the format `<NAME>,<ADDR>,<RCDPORT>` for name, IP address and
    ORCA-RCD listening port, respectively.
    `logger` sets the :class:`logging.Logger` for the newly created :class:`.AccessPoint` s.
    """

    def parse_ap(ap):
        name = ap["NAME"]
        addr = ap["ADDR"]

        try:
            rcd_port = int(ap["RCDPORT"])
        except (KeyError, ValueError):
            rcd_port = 21059

        ap = AccessPoint(name, addr, rcd_port, logger)
        return ap

    with open(file, newline="") as csvfile:
        return [parse_ap(ap) for ap in csv.DictReader(csvfile)]


def from_strings(ap_strs: list, logger=None) -> list:
    """
    Parse the given list of strings and return a list of :class:`.AccessPoint` objects created from
    them. The list entries in `ap_strs` must adhere to the following format:
    `<NAME>,<ADDR>[,<RCDPORT>]` for name, IP address, and (optionally) ORCA-RCD listening port,
    respectively.
    `logger` sets the :class:`logging.Logger` for the newly created :class:`.AccessPoint` s.
    """
    aps = []

    for apstr in ap_strs:
        fields = apstr.split(":")
        if len(fields) < 2:
            print(f"Invalid access point: '{apstr}'", file=sys.stderr)
            continue

        name = fields[0]
        addr = fields[1]

        try:
            rcd_port = int(fields[2])
        except (IndexError, ValueError):
            rcd_port = 21059

        aps.append(AccessPoint(name, addr, rcd_port, logger))

    return aps
