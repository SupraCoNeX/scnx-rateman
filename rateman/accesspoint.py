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

__all__ = ["AccessPoint", "NotConnectedException", "from_file", "from_strings"]


class AccessPoint:
    def __init__(self, name, addr, rcd_port=21059, logger=None):
        """
        Parameters
        ----------
        name : str
            Name given to the AP.
        addr : int
            IP address of the AP.
        rcd_port : int, optional
            Port over which the Rate Control API is accessed.
            The default is 21059.
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
        self._last_cmd = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def addr(self) -> str:
        return self._addr

    @property
    def supp_rates(self) -> str:
        return self._supp_rates

    @property
    def active_stations(self) -> dict:
        return self.get_stations()

    @property
    def connected(self) -> dict:
        return self._connected

    @connected.setter
    def connected(self, connection_status):
        self._connected = connection_status

    def get_sta_rate_control(self, sta):
        for (radio, info) in self._radios.items():
            if sta in info["stations"]["active"]:
                return (
                    info["stations"]["active"]["rate_control_algorithm"],
                    info["stations"]["active"]["rate_control_options"]
                )

        return None

    @property
    def airtimes(self) -> dict:
        return self._airtimes

    @airtimes.setter
    def airtimes(self, airtimes):
        self._airtimes = airtimes

    @property
    def reader(self) -> object:
        return self._reader

    @property
    def writer(self) -> object:
        return self._writer

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
            self._sample_table.append(list(map(int,row.split(","))))

    def get_stations(self, which="active") -> dict:
        if which == "all":
            return self.get_stations(which="active") + self.get_stations(
                which="inactive"
            )

        stas = {}
        for radio in self._radios:
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

    def add_radio(self, radio: str, driver: str, rc_alg="minstrel_ht_kernel_space", rc_opts={}, cfg=None) -> None:
        if radio not in self._radios:
            self._logger.debug(f"{self._name}: adding radio {radio} with driver {driver}")

            self._radios[radio] = {
                "driver": driver,
                "interfaces": [],
                "rate_control_algorithm": rc_alg,
                "rate_control_options": rc_opts,
                "config": cfg,
                "stations": {
                    "active": {},
                    "inactive": {}
                }
            }

    def add_interface(self, radio: str, iface: str) -> None:
        if radio not in self._radios or iface in self._radios[radio]["interfaces"]:
            return

        self._logger.debug(f"{self._name}: adding interface {iface} to radio {radio}")

        self._radios[radio]["interfaces"].append(iface)

    def radio_for_interface(self, iface: str) -> str:
        for radio in self._radios:
            if iface in self._radios[radio]["interfaces"]:
                return radio

        return None

    def add_station(self, sta: Station) -> None:
        if sta.mac_addr not in self._radios[sta.radio]["stations"]["active"]:
            self._logger.debug(f"adding active {sta} to {sta.radio} on {self._name}")
            self._radios[sta.radio]["stations"]["active"][sta.mac_addr] = sta

    def remove_station(self, mac: str, radio: str) -> None:
        try:
            sta = self._radios[radio]["stations"]["active"].pop(mac)
            sta.radio = None
            self._radios[radio]["stations"]["inactive"][mac] = sta
            self._logger.debug(f"removing {sta}")
        except KeyError as e:
            pass

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

        if cmd[-1] != "\n":
            cmd += "\n"

        self._writer.write(cmd.encode("ascii"))
        self._last_cmd = cmd

    def handle_error(self, error):
        self._logger.error(f"{self._name}: Error '{error}', last command='{self._last_cmd}'")

    async def connect(self):
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._addr, self._rcd_port), timeout=0.5
            )

            self._logger.debug(f"{self._name}: Connected at {self._addr}:{self._rcd_port}")

            self._connected = True
        except (
            OSError,
            asyncio.TimeoutError,
            asyncio.CancelledError,
            ConnectionError,
        ) as e:
            self._logger.error(
                f"Failed to connect to {self._name} at {self._addr}:{self._rcd_port}: {e}"
            )
            self._connected = False

    def set_default_rate_control(self, rc_alg, rc_opts={}, radio="all"):
        if radio == "all":
            for radio in self._radios:
                self.set_default_rate_control(rc_alg, rc_opts, radio)

            return

        if radio not in self._radios:
            return

        self._radios[radio]["rate_control_algorithm"] = rc_alg
        self._radios[radio]["rate_control_options"] = rc_opts

    def apply_radio_config(self, radio="all", new_config=None, apply_rc=True):
        if radio == "all":
            for radio in self._radios:
                self.apply_radio_config(radio, new_config)

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

        self._logger.debug(f"{self._name}: {radio}: applying config: {cfg}")

        if "sensitivity_control" in cfg:
            self.set_sensitivity_control(cfg["sensitivity_control"], radio)

        if "disable_firmware_rate_downgrade" in cfg:
            self.mt76_set_firmware_rate_downgrade(cfg["disable_firmware_rate_downgrade"], radio)

        if apply_rc and "rate_control_algorithm" in cfg:
            rc_alg = cfg["rate_control_algorithm"]
            rc_opts = cfg["rate_control_options"] if "rate_control_options" in cfg else {}
            self.apply_rate_control(radio, rc_alg, rc_opts)

    def apply_rate_control(self, radio="all", algorithm=None, options={}):
        if radio == "all":
            return [self.apply_rate_control(radio) for radio in self._radios]

        if radio not in self._radios:
            return None

        if not self._connected:
            raise NotConnectedException(f"{self._name}: Not Connected")

        if algorithm:
            self._radios[radio]["rate_control_algorithm"] = algorithm
            self._radios[radio]["rate_control_options"] = options

        rc_alg = self._radios[radio]["rate_control_algorithm"]
        rc_opts = self._radios[radio]["rate_control_options"]

        self._logger.debug(f"{self._name}: {radio}: applying rate control algorithm {rc_alg}, options: {rc_opts}")

        if rc_alg == "minstrel_ht_kernel_space":
            self.enable_auto_mode(radio)
            if "reset_rate_stats" in rc_opts and rc_opts["reset_rate_stats"]:
                self.reset_rate_stats(radio)

            return None
        else:
            rc = load_rate_control_algorithm(rc_alg)
            if not rc:
                return None

            return rc(self, self._loop, self._logger, **rc_opts)

    def set_rc_info(self, enable, radio="all"):
        if radio == "all":
            self._logger.debug(
                f"{self._name}: {'En' if enable else 'Dis'}abling RC info for all radios"
            )
            self.send(f"*;{'start' if enable else 'stop'};txs;rxs;stats")
        elif radio in self._radios:
            self._logger.debug(
                f"{self._name}: {radio}: {'En' if enable else 'Dis'}abling RC info"
            )
            self.send(f"{radio};{'start' if enable else 'stop'};txs;rxs;stats")

    def mt76_set_firmware_rate_downgrade(self, enable, radio="all"):
        if radio == "all":
            for radio in self._radios:
                self.mt76_disable_firmware_rate_downgrade(enable, radio)
            return

        if radio not in self._radios or "mt7615" not in self._radios[radio]["driver"]:
            return

        self._logger.debug(
            f"{self._name}: {radio}: {'En' if enable else 'Dis'}abling firmware rate downgrade"
        )
        self.send(f"{radio};debugfs;mt76/force_rate_retry;{1 if enable else 0}")

    def enable_manual_mode(self, radio=None) -> None:
        if not radio:
            for radio in self._radios:
                self.enable_manual_mode(radio=radio)

            return

        self._logger.debug(f"{self._name}: {radio}: Enabling manual mode")
        self.send(f"{radio};manual")

    def enable_auto_mode(self, radio="all") -> None:
        if radio == "all":
            for radio in self._radios:
                self.enable_auto_mode(radio=radio)

            return

        if radio not in self._radios:
            return

        if not self._connected:
            raise NotConnectedException(f"{self._name}: Not Connected")

        self._logger.debug(f"{self._name}: {radio}: Enabling auto mode")
        self.send(f"{radio};auto")

    def set_sensitivity_control(self, enable: bool, radio="all") -> None:
        if radio == "all":
            for radio in self._radios:
                self.set_sensitivity_control(enable, radio)

            return

        if radio not in self._radios:
            return

        self._logger.debug(
            f"{self._name}: {radio}: "
            f"{'En' if enable else 'Dis'}abling hardware sensitivity control"
        )

        val = 1 if enable else 0

        if self._radios[radio]["driver"] == "ath9k":
            self.send(f"{radio};debugfs;ath9k/ani;{val}")
        elif self._radios[radio]["driver"] == "mt76":
            self.send(f"{radio};debugfs;mt76/scs;{val}")

    def reset_rate_stats(self, radio="all", sta=None) -> None:
        if radio == "all":
            for radio in self._radios:
                self.reset_rate_stats(radio)

            return

        if radio not in self._radios:
            return

        if not self._connected:
            raise NotConnectedException(f"{self._name}: Not Connected")

        if sta:
            if sta in self._radios[radio]["stations"]["active"]:
                self._logger.debug(
                    f"{self._name}: {radio}: Resetting rate statistics for {sta}"
                )
                self.send(f"{radio};reset_stats;{sta}")
        else:
            self._logger.debug(f"{self._name}: {radio}: Resetting rate statistics")
            self.send(f"{radio};reset_stats")

    def set_rate(self, radio, mac, mrr_rates, mrr_counts) -> None:
        if len(mrr_rates) != len(mrr_counts):
            print("Error: The number of rate and counts do not match!")
            return

        mrr_rates = ["0" if mrr_rate == "00" else mrr_rate for mrr_rate in mrr_rates]

        if len(mrr_rates) == 1:
            rate = mrr_rates[0]
            count = mrr_counts[0]
        else:
            rate = ",".join(mrr_rates)
            count = ",".join(mrr_counts)

        self.send(f"{radio};rates;{mac};{rate};{count}")

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
