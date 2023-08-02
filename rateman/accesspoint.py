# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Accesspoint Object
------------------

TODO

"""
import asyncio
import csv
import sys
import os
import logging
from functools import reduce

from .exception import RadioConfigError, AccessPointNotConnectedError, UnsupportedFeatureException

__all__ = ["AccessPoint", "from_file", "from_strings"]


class AccessPoint:
    def __init__(self, name, addr, rcd_port=21059, logger=None, loop=None):
        """
        Parameters
        ----------
        name : str
            Name given to the AP.
        addr : int
            IP address of the AP.
        rcd_port : int, optional
            Port over which the Rate Control API is accessed. Defaults to 21059
        logger : logging.Logger
            Log
        """
        self._name = name
        self._addr = addr
        self._rcd_port = rcd_port
        self._supp_rates = {}
        self._radios = {}
        self._connected = False
        self._latest_timestamp = 0
        self._logger = logger if logger else logging.getLogger()
        self._loop = loop
        self._last_cmd = None
        self._reader = None
        self._writer = None
        self._task = None
        self._first_non_header_line = None

    async def api_info(self, timeout=0.5):
        it = aiter(self._reader)
        while True:
            try:
                async with asyncio.timeout(timeout):
                    line = (await anext(it)).decode("utf-8").rstrip()

                if line.startswith("*") or ";0;add" in line or ";0;sta" in line:
                    yield line
                else:
                    self._first_non_header_line = line
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
                yield data.decode("utf-8").rstrip()
            except UnicodeError:
                continue

    def __str__(self):
        return self._name

    def __repr__(self):
        return f"AP[name={self._name}, addr={self._addr}:{self._rcd_port}]"

    @property
    def name(self) -> str:
        return self._name

    @property
    def addr(self) -> str:
        return self._addr

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, loop):
        self._loop = loop

    @property
    def logger(self):
        return self._logger

    @property
    def supported_rates(self) -> dict:
        return self._supp_rates

    @property
    def connected(self) -> dict:
        return self._connected

    @connected.setter
    def connected(self, connection_status):
        self._connected = connection_status

    @property
    def radios(self) -> list:
        return self._radios

    @property
    def sample_table(self) -> list:
        return self._sample_table

    @sample_table.setter
    def sample_table(self, sample_table_data):
        self._sample_table = []
        for row in sample_table_data:
            self._sample_table.append(list(map(int, row.split(","))))

    def get_stations(self, radio="all", which="active"):
        if radio == "all":
            return reduce(
                lambda a, b: a + b,
                [self.get_stations(radio=radio, which=which) for radio in self._radios],
                []
            )

        if which == "all":
            return (
                self.get_stations(radio, which="active") +
                self.get_stations(radio, which="inactive")
            )

        return [sta for _, sta in self._radios[radio]["stations"][which].items()]

    def _get_sta(self, mac, radio, state):
        try:
            return self._radios[radio]["stations"][state][mac]
        except KeyError:
            return None

    def get_sta(self, mac: str, radio: str = None, state="active"):
        if not radio:
            for radio in self._radios:
                sta = self.get_sta(mac, radio, state=state)
                if sta:
                    return sta

            return None

        if state == "any":
            sta = self._get_sta(mac, radio, "active")
            return sta if sta else self._get_sta(mac, radio, "inactive")

        return self._get_sta(mac, radio, state)

    def enabled_events(self, radio: str) -> list:
        return self._radios[radio]["events"]

    def features(self, radio: str) -> list:
        return self._radios[radio]["features"].keys()

    async def _set_feature(self, radio, feature, state):
        try:
            if feature not in self._radios[radio]["features"]:
                raise UnsupportedFeatureException(self, radio, feature)
            elif self._radios[radio]["features"][feature] == state:
                return
        except KeyError as e:
            raise RateManError(f"{self._name}: No such radio '{radio}'") from e

        self._radios[radio]["features"][feature] = state
        await self.send(radio, f"set_feature;{feature};{'on' if state else 'off'}")

    async def enable_feature(self, radio :str, feature: str) -> None:
        """
        Enable a given radio's feature.

        Parameters
        ----------
        radio : str
            The radio for which to enable the feature
        feature : str
            The feature to enable

        This will raise a `RateManError` if the radio is unknown and a `UnsupportedFeatureException`
        if the radio does not support the feature.
        """
        await self._set_feature(radio, feature, True)

    async def disable_feature(self, radio: str, feature: str):
        """
        Disable a given radio's feature.

        Parameters
        ----------
        radio : str
            The radio for which to disable the feature
        feature : str
            The feature to disable

        This will raise a `RateManError` if the radio is unknown and a `UnsupportedFeatureException`
        if the radio does not support the feature.
        """
        await self._set_feature(radio, feature, False)

    def add_radio(self, radio: str, driver: str, ifaces: list, events: list, active_features: list,
                  inactive_features: list, tpc: dict) -> None:
        self._logger.debug(
            f"{self._name}: adding radio '{radio}', driver={driver}, "
            f"interfaces={ifaces}, events={events}, active_features={active_features} "
            f"inactive_features={inactive_features}, tpc={tpc}"
        )

        if radio not in self._radios:
            self.radios[radio] = {}

        self._radios[radio].update({
            "driver": driver,
            "interfaces": ifaces,
            "events": events,
            "features": {
                f: (f in active_features) for f in (active_features + inactive_features) if f
            },
            "tpc": tpc,
            "stations": {"active": {}, "inactive": {}}
        })

    def radio_for_interface(self, iface: str) -> str:
        for radio in self._radios:
            if iface in self._radios[radio]["interfaces"]:
                return radio

        return None

    def interfaces(self, radio: str) -> list:
        """
        Return the list of virtual interfaces running on the given radio.
        """
        try:
            return self._radios[radio]["interfaces"]
        except KeyError as e:
            raise RateManError(f"{self._name}: No such radio '{radio}'") from e

    def get_radio_driver(self, radio: str) -> str:
        """
        Return the name of the given radio's driver.
        """
        try:
            return self._radios[radio]["driver"]
        except KeyError as e:
            raise RateManError(f"{self._name}: No such radio '{radio}'") from e

    def txpowers(self, radio: str) -> list:
        """
        Return the list of transmit power levels supported by the given radio.
        """
        if self._radios[radio]["tpc"]:
            return self._radios[radio]["tpc"]["txpowers"]
        else:
            return []

    def add_station(self, sta):
        # TODO: maybe handle sta;updates here, too?
        # Check for diff in capabilities and update accordingly
        if sta.mac_addr not in self._radios[sta.radio]["stations"]["active"]:
            self._logger.debug(f"{self._name}:{sta.radio}: Adding {sta}")

            self._radios[sta.radio]["stations"]["active"][sta.mac_addr] = sta

    def remove_station(self, mac: str, radio: str):
        try:
            sta = self._radios[radio]["stations"]["active"].pop(mac)
        except KeyError:
            return None

        sta.disassociate()

        self._radios[radio]["stations"]["inactive"][mac] = sta
        self._logger.debug(f"{self._name}:{sta.radio}: Removed {sta}")
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
        self._logger.error(f"{self._name}: Error '{error}', last command='{self._last_cmd}'")

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
            self._logger.error(
                f"{self._name}: Failed to connect at {self._addr}:{self._rcd_port}: {e.__repr__()}"
            )
            self._connected = False
            raise e

        self._logger.debug(f"{self._name}: Connected at {self._addr}:{self._rcd_port}")

    async def disconnect(self, timeout=3.0):
        if not self._writer:
            return

        for radio in self._radios:
            for sta in self.get_stations(radio):
                rc_alg, _ = sta.rate_control
                if rc_alg != "minstrel_ht_kernel_space":
                    self._logger.warning(
                        f"Disconnecting from {self} will leave {sta} without rate control"
                    )
                    await sta.stop_rate_control()

        self._writer.close()
        try:
            async with asyncio.timeout(timeout):
                await self._writer.wait_closed()
        except asyncio.TimeoutError:
            self._logger.warning(f"{self._name}: did not disconnect within {timeout}s")

        self._writer = None
        self._connected = False

        self._logger.debug(f"{self}: disconnected")

    async def apply_system_config(self, radio="all", new_config=None):
        if radio == "all":
            for radio in self._radios:
                await self.apply_system_config(radio, new_config)
            return

        if radio not in self._radios:
            return

        if not self._connected:
            raise AccessPointNotConnectedError(self, "Cannot apply system config")

        if new_config:
            self._radios[radio]["config"] = new_config

        cfg = self._radios[radio]["config"]
        if not cfg:
            return

        self._logger.debug(f"{self._name}:{radio}: applying system config: {cfg}")

        if "sensitivity_control" in cfg:
            await self.set_sensitivity_control(cfg["sensitivity_control"], radio)

        if "mt76_force_rate_retry" in cfg:
            await self.mt76_force_rate_retry(cfg["mt76_force_rate_retry"], radio)

    async def enable_events(self, events: list, radio="all") -> None:
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

        await self.send(radio, "start;" + ";".join(events))

    async def disable_events(
        self, events: list = ["txs", "rxs", "stats", "tprc_echo"], radio="all"
    ) -> None:
        if radio in ["all", "*"]:
            radio = "*"
            for r in self._radios:
                self._radios[r]["events"] = list(set(self._radios[r]["events"]) - set(events))
        else:
            self._radios[radio]["events"] = list(set(self._radios[radio]["events"]) - set(events))

        await self.send(radio, "stop;" + ";".join(events))

    async def dump_stas(self, radio="all"):
        if radio == "all":
            radio = "*"

        await self.send(radio, "dump")

    async def debugfs_set(self, path, value, radio="all"):
        if radio == "all":
            for radio in self._radios:
                self.debugfs_set(path, value, radio=radio)
            return

        if radio not in self._radios:
            return

        self._logger.debug(f"{self._name}:{radio}: debugfs: setting {path}={value}")
        await self.send(radio, f"debugfs;{path};{value}")

    async def mt76_force_rate_retry(self, enable, radio="all"):
        if radio == "all":
            for radio in self._radios:
                await self.mt76_force_rate_retry(enable, radio)

            return

        if "mt76" in self._radios[radio]["driver"]:
            await self.debugfs_set("mt76/force_rate_retry", 1 if enable else 0, radio)

    async def set_sensitivity_control(self, enable: bool, radio="all") -> None:
        if radio == "all":
            for radio in self._radios:
                await self.set_sensitivity_control(enable, radio)

            return

        if radio not in self._radios:
            return

        self._logger.debug(
            f"{self._name}:{radio}: "
            f"{'En' if enable else 'Dis'}abling hardware sensitivity control"
        )

        val = 1 if enable else 0

        if self._radios[radio]["driver"] == "ath9k":
            await self.send(radio, f"debugfs;ath9k/ani;{val}")
        elif self._radios[radio]["driver"] == "mt76":
            await self.send(radio, f"debugfs;mt76/scs;{val}")

    async def reset_kernel_rate_stats(self, radio="all", sta="all") -> None:
        if radio in ["*", "all"]:
            radio = "*"
        elif radio not in self._radios:
            return

        if sta == "all":
            self._logger.debug(f"{self._name}:{radio}: Resetting in-kernel rate statistics")
            await self.send(radio, f"reset_stats")
        elif sta in self._radios[radio]["stations"]["active"]:
            self._logger.debug(f"{self._name}:{radio}:{sta}: Resetting in-kernel rate statistics")
            await self.send(radio, f"reset_stats;{sta}")

    def add_supp_rates(self, group_ind, group_info):
        if group_ind not in self._supp_rates:
            self._supp_rates.update({group_ind: group_info})

    async def _set_all_stations_mode(self, radio, which, mode):
        if mode not in ["manual", "auto"]:
            raise ValueError(f"Invalid mode '{mode}', must be either 'manual' or 'auto'")

        self._logger.debug(f"{self._name}:{radio}: Setting {which} for all stations to {mode}")

        await self.send(radio, f"{which};all;{mode}")

        if radio == "*":
            for r in self._radios:
                for sta in self.get_stations(r):
                    if which == "rc_mode":
                        sta._rc_mode = mode
                    else:
                        sta._tpc_mode = mode
        else:
            for sta in self.get_stations(radio):
                if which == "rc_mode":
                    sta._rc_mode = mode
                else:
                    sta._tpc_mode = mode

    async def set_all_stations_rc_mode(self, mode: str, radio="*") -> None:
        await self._set_all_stations_mode(radio, "rc_mode", mode)

    async def set_all_stations_tpc_mode(self, mode: str, radio="*") -> None:
        await self._set_all_stations_mode(radio, "tpc_mode", mode)

    async def enable_tprc_echo(self, enable: bool, radio="*") -> None:
        action = "start" if enable else "stop"
        await self.send(radio, f"{action};tprc_echo")


def from_file(file: dir, logger=None):
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


def from_strings(ap_strs, logger=None):
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
