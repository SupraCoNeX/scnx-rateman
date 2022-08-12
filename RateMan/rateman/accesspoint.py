# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Accesspoint Object
------------------

This class provides ... 

"""
import asyncio
import logging
import csv
from .station import Station

__all__ = ["AccessPoint", "get_aps_from_file"]


class AccessPoint:
    def __init__(self, ap_id, addr, ssh_port, rcd_port=21059):

        self._ap_id = ap_id
        self._addr = addr
        self._ssh_port = ssh_port
        self._rcd_port = rcd_port
        self._supp_rates = {}
        self._phys = {}
        self._connected = False
        self._collector = None

    @property
    def ap_id(self) -> str:
        return self._ap_id

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
    def active_stations(self) -> dict:
        return self.get_stations()
    
    @property
    def connected(self) -> dict:
        return self._connected

    @connected.setter
    def connected(self, connection_status):
        self._connected = connection_status

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

    def get_stations(self, which="active"):
        if which == "all":
            return self.stations(which="active") + self.stations(which="inactive")

        stas = {}
        for phy in self._phys:
            for mac, sta in self._phys[phy][which].items():
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
            logging.debug(f"{self.ap_id}: adding PHY {phy}")
            self._phys[phy] = {"active": {}, "inactive": {}}
            self._writer.write(f"{phy};dump\n".encode("ascii"))
            self._writer.write(f"{phy};start;txs;rxs;stats\n".encode("ascii"))

    def add_station(self, sta: Station) -> None:
        if sta.mac_addr not in self._phys[sta.radio]["active"]:
            logging.info(f"adding active {sta} on {sta.radio}")
            self._phys[sta.radio]["active"][sta.mac_addr] = sta

    def remove_station(self, mac: str, phy: str) -> None:
        try:
            sta = self._phys[phy]["active"].pop(mac)
            sta.radio = None
            self._phys[phy]["inactive"][mac] = sta
            logging.info(f"removing {sta} from {phy}")
        except KeyError as e:
            pass

    async def connect(self):
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._addr, self._rcd_port), timeout=0.5
            )

            logging.info(f"Connected to {self._ap_id} at {self._addr}:{self._rcd_port}")

            self._connected = True
        except (OSError, asyncio.TimeoutError, ConnectionError) as e:
            logging.error(
                f"Failed to connect to {self._ap_id} at {self._addr}:{self._rcd_port}: {e}"
            )
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
            
        print("Setting %s for %s" %(rate, count))

        self._writer.write(f"{phy};rates;{mac};{rate};{count}\n".encode("ascii"))

    def add_supp_rates(self, group_idx, max_offset):
        if group_idx not in self._supp_rates:
            self.supp_rates.update({group_idx: max_offset})


def get_aps_from_file(file: dir):
    def parse_ap(ap):
        ap_id = ap["APID"]
        addr = ap["IPADD"]
        ssh_port = ap["SSHPORT"]

        try:
            rcd_port = int(ap["RCDPORT"])
        except (KeyError, ValueError):
            rcd_port = 21059

        ap = AccessPoint(ap_id, addr, ssh_port, rcd_port)

        return ap

    with open(file, newline="") as csvfile:
        return [parse_ap(ap) for ap in csv.DictReader(csvfile)]
