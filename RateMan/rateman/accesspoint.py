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
import logging
import csv
from .station import Station

__all__ = ["AccessPoint", "from_file", "from_str"]


class AccessPoint:
    def __init__(self, id, addr, rcd_port=21059):

        self._id = id
        self._addr = addr
        self._rcd_port = rcd_port
        self._supp_rates = {}
        self._phys = {}
        self._connected = False
        self._collector = None
        self._latest_timestamp = 0

    @property
    def id(self) -> str:
        return self._id

    @property
    def addr(self) -> str:
        return self._addr

    @property
    def supp_rates(self) -> str:
        return self._supp_rates

    @property
    def stations(self) -> dict:
        return {}

    @property
    def connected(self) -> dict:
        return self._connected

    @connected.setter
    def connected(self, connection_status):
        self._connected = connection_status

    @property
    def rate_control_type(self) -> dict:
        return self._rate_control_type

    @rate_control_type.setter
    def rate_control_type(self, rate_control_type):
        self._rate_control_type = rate_control_type

    @property
    def rate_control_alg(self) -> dict:
        return self._rate_control_alg

    @rate_control_alg.setter
    def rate_control_alg(self, rate_control_alg):
        self._rate_control_alg = rate_control_alg

    @property
    def rate_control(self) -> dict:
        return self._rate_control

    @rate_control.setter
    def rate_control(self, rate_control):
        self._rate_control = rate_control

    @property
    def rate_control_settings(self) -> dict:
        return self._rate_control_settings

    @rate_control_settings.setter
    def rate_control_settings(self, rate_control_settings):
        self._rate_control_settings = rate_control_settings

    @property
    def reader(self) -> object:
        return self._reader

    @property
    def writer(self) -> object:
        return self._writer

    @property
    def phys(self) -> list:
        return self._phys

    def stations(self, which="active"):
        if which == "all":
            return self.stations(which="active") + self.stations(which="inactive")

        stas = {}
        for phy in self._phys:
            for mac,sta in self._phys[phy][which].items():
                stas[mac] = sta

        return stas

    def _get_sta(self, mac, phy, state):
        try:
            return self._phys[phy][state][mac]
        except KeyError:
            return None

    def get_sta(self, mac: str, phy: str = None, state="active"):
        if not phy:
            for phy in self._phys:
                sta = self.get_sta(mac, phy, state=state)
                if sta:
                    return sta

            return None

        if state == "any":
            sta = self._get_sta(mac, phy, "active")
            return sta if sta else self._get_sta(mac, phy, "inactive")

        return None

    def add_phy(self, phy: str) -> None:
        if phy not in self._phys:
            logging.debug(f"{self.id}: adding PHY {phy}")
            self._phys[phy] = {"active": {}, "inactive": {}}
            self._writer.write(f"{phy};dump\n".encode("ascii"))
            self._writer.write(f"{phy};start;txs;rxs;stats\n".encode("ascii"))

    def add_station(self, sta: Station) -> None:
        if sta.mac_addr not in self._phys[sta.radio]["active"]:
            logging.info(f"adding active {sta}")
            self._phys[sta.radio]["active"][sta.mac_addr] = sta

    def remove_station(self, mac: str, phy: str) -> None:
        try:
            sta = self._phys[phy]["active"].pop(mac)
            sta.radio = None
            self._phys[phy]["inactive"][mac] = sta
            logging.info(f"removing {sta}")
        except KeyError as e:
            pass

    def update_timestamp(self, timestamp_str):
        timestamp = int(timestamp_str, 16)

        if self._latest_timestamp == 0:
            self._latest_timestamp = timestamp
            return True

        if timestamp > self._latest_timestamp and len(timestamp_str) - len(f"{self._latest_timestamp:x}") <= 1:
            self._latest_timestamp = timestamp
            return True

        return False

    async def connect(self):
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._addr, self._rcd_port),
                timeout=0.5
            )

            logging.info(f"Connected to {self._id} at {self._addr}:{self._rcd_port}")

            self._connected = True
        except (OSError, asyncio.TimeoutError, ConnectionError) as e:
            logging.error(f"Failed to connect to {self._id} at {self._addr}:{self._rcd_port}: {e}")
            self._connected = False

    def enable_rc_api(self, phy=None):
        if not phy:
            for phy in self._phys:
                self.enable_rc_api(phy=phy)

        self._writer.write(f"{phy};stop\n".encode("ascii"))
        self._writer.write(f"{phy};start;stats;txs;rxs\n".encode("ascii"))

    def set_rate(self, phy, mac, mrr_rates, mrr_counts) -> None:
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

        self._writer.write(f"{phy};rates;{mac};{rate};{count}\n".encode("ascii"))

    def add_supp_rates(self, group_idx, max_offset):
        if group_idx not in self._supp_rates:
            self.supp_rates.update({group_idx: max_offset})

def from_file(file):
    def parse_ap(ap):
        id = ap["APID"]
        addr = ap["IPADD"]

        try:
            rcd_port = int(ap["MinstrelRCD_Port"])
        except (KeyError, ValueError):
            rcd_port = 21059

        ap = AccessPoint(id, addr, rcd_port=rcd_port)
        ap.rate_control_alg = rate_control_alg
        ap.rate_control_handle = self.get_rc_alg_entry(rate_control_alg)

        return ap

    with open(file, newline="") as csvfile:
        return [parse_ap(ap) for ap in csv.DictReader(csvfile)]

def from_str(ap_strs):
    aps = []

    for apstr in ap_strs:
        fields = apstr.split(":")
        if len(fields) < 2:
            print(f"Invalid access point: '{apstr}'", file=sys.stderr)
            continue

        id = fields[0]
        addr = fields[1]

        try:
            rcd_port = int(fields[2])
        except (IndexError, ValueError):
            rcd_port = 21059

        aps.append(AccessPoint(id, addr, rcd_port))

    return aps
