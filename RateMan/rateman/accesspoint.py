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
import sys
import os
from .station import Station

__all__ = ["AccessPoint", "get_aps_from_file", "parse_ap_strs"]


class AccessPoint:
    def __init__(self, ap_id, addr, ssh_port, rcd_port=21059):
        """
        Parameters
        ----------
        ap_id : str
            ID given to the AP.
        addr : int
            IP address of the AP.
        ssh_port : int
            SSH Port of the AP.
        rcd_port : int, optional
            Port over which the Rate Control API is accessed.
            The default is 21059.
        save_data : bool, optional
            Flag denoting if trace data is to be saved for the AP.
            The default is False.
        output_dir : dir, optional
            File path of the directory where data is collected by RateMan
            instance.
            The default is None.

        """
        self._ap_id = ap_id
        self._addr = addr
        self._rcd_port = rcd_port
        self._supp_rates = {}
        self._phys = {}
        self._connected = False
        self._save_data = False
        self._output_dir = None
        self._data_file = None
        self._latest_timestamp = 0

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
    def active_stations(self) -> dict:
        return self.get_stations()

    @property
    def connected(self) -> dict:
        return self._connected

    @connected.setter
    def connected(self, connection_status):
        self._connected = connection_status

    @property
    def save_data(self) -> bool:
        return self._save_data

    @save_data.setter
    def save_data(self, save_data: bool):
        self._save_data = save_data

    @property
    def output_dir(self) -> bool:
        return self._output_dir

    @output_dir.setter
    def output_dir(self, output_dir: bool):
        self._output_dir = output_dir

    @property
    def data_file(self) -> object:
        return self._data_file

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
    def phys(self) -> list:
        return self._phys

    def get_stations(self, which="active") -> dict:
        if which == "all":
            return self.get_stations(which="active") + self.get_stations(
                which="inactive"
            )

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
            self._writer.write(f"{phy};start;stats;txs\n".encode("ascii"))

    def add_station(self, sta: Station) -> None:
        if sta.mac_addr not in self._phys[sta.radio]["active"]:
            logging.info(f"adding active {sta} to {sta.radio} on {self.ap_id}")
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

    async def connect(self):
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._addr, self._rcd_port), timeout=0.5
            )

            logging.info(f"Connected to {self.ap_id} at {self._addr}:{self._rcd_port}")

            self._connected = True

            if self.save_data:
                self.open_data_file()

        except (OSError, asyncio.TimeoutError, ConnectionError) as e:
            logging.error(
                f"Failed to connect to {self.ap_id} at {self._addr}:{self._rcd_port}: {e}"
            )
            self._connected = False

    def enable_rc_info(self, phy=None):
        if not phy:
            for phy in self._phys:
                self.enable_rc_info(phy=phy)

        logging.info(f"Enabling API for {phy} on {self._ap_id}")
        self._writer.write(f"{phy};start;stats;txs\n".encode("ascii"))

    def enable_manual_mode(self, phy=None) -> None:
        if not phy:
            for phy in self._phys:
                self.enable_manual_mode(phy=phy)
                
        logging.info(f"Enabling manual mode on {phy} on {self._ap_id}")
        self._writer.write(f"{phy};stop\n".encode("ascii"))
        self._writer.write(f"{phy};manual\n".encode("ascii"))
    
    def enable_auto_mode(self, phy=None) -> None:
        if not phy:
            for phy in self._phys:
                self.enable_auto_mode(phy=phy)
                
        logging.info(f"Enabling auto mode on {phy} on {self._ap_id}")
        self._writer.write(f"{phy};stop\n".encode("ascii"))
        self._writer.write(f"{phy};auto\n".encode("ascii"))
    
    def reset_phy_stats(self, phy=None) -> None:
        if not phy:
            for phy in self._phys:
                self.reset_phy_stats(phy=phy)
                
        logging.info(f"Reseting rate table for {phy} on {self._ap_id}")
        self._writer.write(f"{phy};stop\n".encode("ascii"))
        self._writer.write(f"{phy};reset_stats\n".encode("ascii"))

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

    def add_supp_rates(self, group_ind, group_info):
        if group_ind not in self._supp_rates:
            self._supp_rates.update({group_ind: group_info})

    def open_data_file(self):
        if not bool(self._output_dir):
            self._output_dir = os.path.join(os.getcwd())

        self._data_file = open(self._output_dir + "/" + self.ap_id + ".csv", "w")


def get_aps_from_file(file: dir):
    def parse_ap(ap):
        ap_id = ap["APID"]
        addr = ap["IPADD"]

        try:
            ssh_port = int(ap["SSHPORT"])
        except (KeyError, ValueError):
            ssh_port = 22

        try:
            rcd_port = int(ap["RCDPORT"])
        except (KeyError, ValueError):
            rcd_port = 21059

        ap = AccessPoint(ap_id, addr, ssh_port, rcd_port=rcd_port)
        return ap

    with open(file, newline="") as csvfile:
        return [parse_ap(ap) for ap in csv.DictReader(csvfile)]


def parse_ap_strs(ap_strs):
    aps = []

    for apstr in ap_strs:
        fields = apstr.split(":")
        if len(fields) < 2:
            print(f"Invalid access point: '{apstr}'", file=sys.stderr)
            continue

        ap_id = fields[0]
        addr = fields[1]

        try:
            ssh_port = int(fields[2])
        except (IndexError, ValueError):
            ssh_port = 22
        try:
            rcd_port = int(fields[3])
        except (IndexError, ValueError):
            rcd_port = 21059

        aps.append(AccessPoint(ap_id, addr, ssh_port, rcd_port))

    return aps
