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

__all__ = ["AccessPoint", "from_file", "from_strings"]


class AccessPoint:
    def __init__(self, name, addr, rcd_port=21059, rc_alg="minstrel_ht_kernel_space"):
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
        save_data : bool, optional
            Flag denoting if trace data is to be saved for the AP.
            The default is False.
        output_dir : dir, optional
            File path of the directory where data is collected by RateMan
            instance.
            The default is None.

        """
        self._name = name
        self._addr = addr
        self._rcd_port = rcd_port
        self._supp_rates = {}
        self._radios = {}
        self._connected = False
        self._save_data = False
        self._output_dir = None
        self._data_file = None
        self._latest_timestamp = 0
        self._rate_control_alg = rc_alg

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
    
    def add_radio(self, radio: str, driver: str) -> None:
        if radio not in self._radios:
            logging.info(f"{self._name}: adding radio {radio} with driver {driver}")
            self._radios[radio] = {
                "driver": driver,
                "interfaces": [],
                "stations": {
                    "active": {},
                    "inactive": {}
                }
            }

    def add_interface(self, radio: str, iface: str) -> None:
        if radio not in self._radios or iface in self._radios[radio]["interfaces"]:
            return

        logging.info(f"{self._name}: adding interface {iface} to radio {radio}")

        self._radios[radio]["interfaces"].append(iface)

    def radio_for_interface(self, iface: str) -> str:
        for radio in self._radios:
            if iface in self._radios[radio]["interfaces"]:
                return radio

        return None

    def add_station(self, sta: Station) -> None:
        if sta.mac_addr not in self._radios[sta.radio]["stations"]["active"]:
            logging.info(f"adding active {sta} to {sta.radio} on {self._name}")
            self._radios[sta.radio]["stations"]["active"][sta.mac_addr] = sta

    def remove_station(self, mac: str, radio: str) -> None:
        try:
            sta = self._radios[radio]["stations"]["active"].pop(mac)
            sta.radio = None
            self._radios[radio]["stations"]["inactive"][mac] = sta
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

            logging.info(f"Connected to {self._name} at {self._addr}:{self._rcd_port}")

            self._connected = True

            if self.save_data:
                self.open_data_file()

        except (
            OSError,
            asyncio.TimeoutError,
            asyncio.CancelledError,
            ConnectionError,
        ) as e:
            logging.error(
                f"Failed to connect to {self._name} at {self._addr}:{self._rcd_port}: {e}"
            )
            self._connected = False
            
    def enable_rc_info(self, radio=None):
        if not radio:
            for radio in self._radios:
                self.enable_rc_info(radio=radio)
        
        if radio:
            logging.info(f"Enabling RC info for {radio} on {self._name}")
            self._writer.write(f"{radio};start;stats;txs\n".encode("ascii"))

    def disable_kernel_fallback(self, radio: str, driver: str):
        logging.info(f"Disabling Kernel Fallback RC for {radio} with {driver} on {self._name}")
        self._writer.write(f"{radio};debugfs;{driver}/force_rate_retry;1".encode("ascii"))

    def enable_manual_mode(self, radio=None) -> None:
        if not radio:
            for radio in self._radios:
                self.enable_manual_mode(radio=radio)
        
        if radio:
            logging.info(f"Enabling manual mode on {radio} on {self._name}")
            self._writer.write(f"{radio};stop\n".encode("ascii"))
            self._writer.write(f"{radio};dump\n".encode("ascii"))
            self._writer.write(f"{radio};manual\n".encode("ascii"))
            
    def enable_auto_mode(self, radio=None) -> None:
        if not radio:
            for radio in self._radios:
                self.enable_auto_mode(radio=radio)
        if radio:                    
            logging.info(f"Enabling auto mode on {radio} on {self._name}")
            self._writer.write(f"{radio};stop\n".encode("ascii"))
            self._writer.write(f"{radio};auto\n".encode("ascii"))

    def toggle_sensitivity_control(self, toggle: [0,1]) -> None:

        if toggle not in [0, 1]:
             logging.error(
                 f"Invalid toggle {toggle} for {self._name}"
             )   
        else:
            logging.info(
                f"Setting sensitivity control for {self._name} to {toggle}"
            )
            
            for radio in self._radios:
                if self._radios[radio]["driver"] == "ath9k":
                    self._writer.write(f"{radio};debugfs;ath9k/ani;{toggle}\n".encode("ascii"))
                elif self._radios[radio]["driver"] == "mt76":
                    self._writer.write(f"{radio};debugfs;mt76/scs;{toggle}\n".encode("ascii"))

    def reset_radio_stats(self, radio=None) -> None:
        if not radio:
            for radio in self._radios:
                self.reset_radio_stats(radio=radio)
        if radio:                
            logging.info(f"Reseting rate statistics for {radio} on {self._name}")
            self._writer.write(f"{radio};stop\n".encode("ascii"))
            self._writer.write(f"{radio};reset_stats\n".encode("ascii"))

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
        
        self._writer.write(f"{radio};rates;{mac};{rate};{count}\n".encode("ascii"))
    
    def set_probe_rate(self, radio, mac, rate) -> None:
        self._writer.write(f"{radio};probe;{mac};{rate}\n".encode("ascii"))
        logging.info(f"{radio};probe;{mac};{rate}\n")

    def add_supp_rates(self, group_ind, group_info):
        if group_ind not in self._supp_rates:
            self._supp_rates.update({group_ind: group_info})

    def open_data_file(self):
        if not bool(self._output_dir):
            self._output_dir = os.path.join(os.getcwd())

        self._data_file = open(self._output_dir + "/" + self._name + ".csv", "w")

def from_file(file: dir):
    def parse_ap(ap):
        name = ap["NAME"]
        addr = ap["ADDR"]

        try:
            rcd_port = int(ap["RCDPORT"])
        except (KeyError, ValueError):
            rcd_port = 21059

        ap = AccessPoint(name, addr, rcd_port=rcd_port)
        return ap

    with open(file, newline="") as csvfile:
        return [parse_ap(ap) for ap in csv.DictReader(csvfile)]


def from_strings(ap_strs):
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

        aps.append(AccessPoint(name, addr, rcd_port))

    return aps
