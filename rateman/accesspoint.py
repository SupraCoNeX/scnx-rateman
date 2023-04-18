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
from .station import Station

__all__ = ["AccessPoint", "from_file", "from_strings"]


class AccessPoint:
    def __init__(self, name, addr, rcd_port=21059, config=None, logger=None, loop=None):
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

    def __aiter__(self):
        return self._reader

    async def __anext__(self):
        return self._reader.__anext__()

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

    @logger.setter
    def logger(self, logger):
        self._logger = logger

    def get_default_rc(self, radio):
        try:
            rc_alg = self._radios[radio]["default_rate_control_algorithm"]
            rc_opts = self._radios[radio]["default_rate_control_options"]
            return (rc_alg, rc_opts)
        except KeyError:
            return (None, None)

    def set_default_rc(self, rc_alg, rc_opts, radio="all"):
        if radio == "all":
            for radio in self._radios:
                self.set_default_rc(rc_alg, rc_opts, radio=radio)
            return

        self._logger.info(
            f"{self._name}:{radio}: Set default rc algorithm '{rc_alg}', options={rc_opts}"
        )

        if radio not in self._radios:
            self._radios[radio] = {}

        self._radios[radio]["default_rate_control_algorithm"] = rc_alg
        self._radios[radio]["default_rate_control_options"] = rc_opts

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

    def get_stations(self, radio, which="active"):
        if which == "all":
            return self.get_stations(radio, which="active").update(
                self.get_stations(radio, which="inactive")
            )

        stas = {}
        for mac, sta in self._radios[radio]["stations"][which].items():
            stas[mac] = sta

        return stas

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

        return None

    def add_radio(
        self,
        radio: str,
        driver: str,
        rc_alg=None,
        rc_opts=None,
        cfg=None,
    ) -> None:
        self._logger.debug(
            f"{self._name}: adding radio '{radio}', driver={driver}"
        )

        if radio not in self._radios:
            self.radios[radio] = {}

        if (rc_alg and rc_opts) is None:
            if "default_rate_control_algorithm" in self._radios[radio]:
                rc_alg = self._radios[radio]["default_rate_control_algorithm"]
                rc_opts = self._radios[radio]["default_rate_control_options"]
            else:
                rc_alg, rc_opts = self.get_default_rc(radio)

        self._radios[radio].update({
            "driver": driver,
            "interfaces": [],
            "mode": "unknown",
            "rate_control_algorithm": rc_alg,
            "rate_control_options": rc_opts,
            "config": cfg,
            "stations": {"active": {}, "inactive": {}},
        })

    def add_interface(self, radio: str, iface: str) -> None:
        if radio in self._radios and iface in self._radios[radio]["interfaces"]:
            return

        self._logger.debug(f"{self._name}:{radio}: adding interface '{iface}'")

        self._radios[radio]["interfaces"].append(iface)

    def radio_for_interface(self, iface: str) -> str:
        for radio in self._radios:
            if iface in self._radios[radio]["interfaces"]:
                return radio

        return None

    def add_station(self, sta: Station) -> bool:
        if sta.mac_addr not in self._radios[sta.radio]["stations"]["active"]:
            self._logger.debug(f"{self._name}:{sta.radio}: Adding active {sta}")
            self._radios[sta.radio]["stations"]["active"][sta.mac_addr] = sta
            sta.accesspoint = self
            return True
        return False

    def remove_station(self, mac: str, radio: str) -> None:
        try:
            sta = self._radios[radio]["stations"]["active"].pop(mac)
        except KeyError:
            return None

        sta.radio = None
        sta.accesspoint = None
        self._radios[radio]["stations"]["inactive"][mac] = sta
        self._logger.debug(f"Removed {sta}")
        return sta

    def update_timestamp(self, timestamp_str):
        try:
            timestamp = int(timestamp_str, 16)
        except:
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

    def send(self, cmd: str):
        if not self.connected:
            raise NotConnectedException(f"{self._name}: Cannot send '{cmd}': Not Connected")
        self._last_cmd = cmd
        if cmd[-1] != "\n":
            cmd += "\n"
        self._writer.write(cmd.encode("ascii"))

    def handle_error(self, error):
        self._logger.error(f"{self._name}: Error '{error}', last command='{self._last_cmd}'")

    async def connect(self):
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._addr, self._rcd_port), timeout=0.5
            )

            self._logger.debug(f"{self._name}: Connected at {self._addr}:{self._rcd_port}")
            self._connected = True

        except (OSError, asyncio.TimeoutError, ConnectionError) as e:
            self._logger.error(
                f"{self._name}: Failed to connect at {self._addr}:{self._rcd_port}: {e}"
            )
            self._connected = False
            raise e

    async def disconnect(self):
        if not self._writer:
            return

        self._writer.close()
        await self._writer.wait_closed()

    def apply_system_config(self, radio="all", new_config=None):
        if radio == "all":
            for radio in self._radios:
                self.apply_system_config(radio, new_config)
            return

        if radio not in self._radios:
            return

        if not self._connected:
            raise NotConnectedException(f"{self._name}: Not Connected")

        if new_config:
            self._radios[radio]["config"] = new_config

        cfg = self._radios[radio]["config"]
        if not cfg:
            return

        self._logger.debug(f"{self._name}:{radio}: applying system config: {cfg}")

        if "sensitivity_control" in cfg:
            self.set_sensitivity_control(cfg["sensitivity_control"], radio)

        if "mt76_force_rate_retry" in cfg:
            self.mt76_force_rate_retry(cfg["mt76_force_rate_retry"], radio)

    def set_rc_info(self, enable, radio="all"):
        if radio == "all":
            self._logger.debug(
                f"{self._name}: {'En' if enable else 'Dis'}abling RC info for all radios"
            )
            for radio in self._radios:
                self.send(f"{radio};{'start' if enable else 'stop'};txs;rxs;stats")
        elif radio in self._radios:
            self._logger.debug(
                f"{self._name}:{radio}: {'En' if enable else 'Dis'}abling RC info"
            )
            self.send(f"{radio};{'start' if enable else 'stop'};txs;rxs;stats")

    def dump_stas(self, radio="all"):
        if radio == "all":
            self.send("*;dump")
        else:
            self.send(f"{radio};dump")

    def debugfs_set(self, path, value, radio="all"):
        if radio == "all":
            for radio in self._radios:
                self.debugfs_set(path, value, radio=radio)
            return

        if radio not in self._radios:
            return

        self._logger.debug(f"{radio}:debugfs: setting {path}={value}")
        self.send(f"{radio};debugfs;{path};{value}")

    def mt76_set_automatic_rate_downgrade(self, enable, radio="all"):
        if radio == "all":
            for radio in self._radios:
                self.mt76_set_automatic_rate_downgrade(enable, radio)

            return

        if "mt76" in self._radios[radio]["driver"]:
            self.debugfs_set("mt76/force_rate_retry", 1 if enable else 0, radio)

    def enable_manual_mode(self, radio=None) -> None:
        if not radio:
            for radio in self._radios:
                self.enable_manual_mode(radio=radio)

            return

        if radio not in self._radios or self._radios[radio]["mode"] == "manual":
            return

        self._logger.debug(f"{self._name}:{radio}: Enabling manual mode")
        self.send(f"{radio};manual")
        self._radios[radio]["mode"] = "manual"

    def enable_auto_mode(self, radio="all") -> None:
        if radio == "all":
            for radio in self._radios:
                self.enable_auto_mode(radio=radio)

            return

        if radio not in self._radios or self._radios[radio]["mode"] == "auto":
            return

        self._logger.debug(f"{self._name}:{radio}: Enabling auto mode")

        # Warn about stations whose user space RC will be affected by switching this radio to auto
        stas = [
            sta for _,sta in self._radios[radio]["stations"]["active"].items()
            if sta.rate_control[0] != "minstrel_ht_kernel_space"
        ]

        if len(stas) != 0:
            self._logger.warning(
                f"{self._name}:{radio}: Associated stations' rate control will "
                f"become 'minstrel_ht_kernel_space': {','.join([str(s) for s in stas])}"
            )

        # switch all other stations of the same radio to minstrel_ht_kernel_space
        for sta in stas:
            sta.start_rate_control("minstrel_ht_kernel_space", {})

        self.send(f"{radio};auto")
        self._radios[radio]["mode"] = "auto"

    def set_sensitivity_control(self, enable: bool, radio="all") -> None:
        if radio == "all":
            for radio in self._radios:
                self.set_sensitivity_control(enable, radio)

            return

        if radio not in self._radios:
            return

        self._logger.debug(
            f"{self._name}:{radio}: "
            f"{'En' if enable else 'Dis'}abling hardware sensitivity control"
        )

        val = 1 if enable else 0

        if self._radios[radio]["driver"] == "ath9k":
            self.send(f"{radio};debugfs;ath9k/ani;{val}")
        elif self._radios[radio]["driver"] == "mt76":
            self.send(f"{radio};debugfs;mt76/scs;{val}")

    def reset_kernel_rate_stats(self, radio="all", sta="all") -> None:
        if radio == "all":
            for radio in self._radios:
                self.reset_rate_stats(radio)

            return

        if radio not in self._radios:
            return

        if sta == "all":
            self._logger.debug(f"{self._name}:{radio}: Resetting in-kernel rate statistics")
            self.send(f"{radio};reset_stats")
        elif sta in self._radios[radio]["stations"]["active"]:
            self._logger.debug(f"{self._name}:{radio}:{sta}: Resetting in-kernel rate statistics")
            self.send(f"{radio};reset_stats;{sta}")

    def set_rate(self, radio, mac, mrr_rates, mrr_counts) -> None:
        if len(mrr_rates) != len(mrr_counts):
            raise ValueError("The number of rates and counts must be identical!")

        mrr_rates = ["0" if mrr_rate == "00" else mrr_rate for mrr_rate in mrr_rates]

        if len(mrr_rates) == 1:
            rates = mrr_rates[0]
            counts = mrr_counts[0]
        else:
            rates = ",".join([str(r) for r in mrr_rates])
            counts = ",".join([str(c) for c in mrr_counts])

        self.send(f"{radio};rates;{mac};{rates};{counts}")

    def set_probe_rate(self, radio, mac, rate) -> None:
        self.send(f"{radio};probe;{mac};{rate}")
        self._logger.debug(f"{radio};probe;{mac};{rate}\n")

    def add_supp_rates(self, group_ind, group_info):
        if group_ind not in self._supp_rates:
            self._supp_rates.update({group_ind: group_info})


class NotConnectedException(Exception):
    def __init__(self, msg):
        super().__init__(msg)


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
            rcd_port = int(fields[3])
        except (IndexError, ValueError):
            rcd_port = 21059

        aps.append(AccessPoint(name, addr, rcd_port, logger))

    return aps
