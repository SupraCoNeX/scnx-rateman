# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Accesspoint Object
----------------

This class provides ... 

"""
import asyncio
import logging
from .station import Station

__all__ = ["AccessPoint"]


class AccessPoint:
    def __init__(self, AP_ID, AP_IP, AP_SSH_port, AP_MinstrelRCD_port=21059) -> None:

        self._AP_ID = AP_ID
        self._AP_IP = AP_IP
        self._AP_SSH_port = AP_SSH_port
        self._AP_MinstrelRCD_port = AP_MinstrelRCD_port
        self._supp_rates = {}
        self._phy_list = ["phy0", "phy1"]
        self._sta_list_inactive = {}.fromkeys(self._phy_list, {})
        self._sta_list_active = {}.fromkeys(self._phy_list, {})
        self._connection = False
        self._data_dir = ""

    @property
    def AP_ID(self) -> str:

        return self._AP_ID

    @property
    def AP_IP(self) -> str:

        return self._AP_IP

    @property
    def AP_SSH_port(self) -> str:

        return self._AP_SSH_port

    @property
    def supp_rates(self) -> str:

        return self._supp_rates

    @property
    def stations(self) -> dict:
        # list of clients for a given AP at a given radio

        pass

    @property
    def connection(self) -> dict:
        # list of clients for a given AP at a given radio

        return self._connection

    @connection.setter
    def connection(self, connection_status):
        self._connection = connection_status

    @property
    def reader(self) -> object:
        # list of clients for a given AP at a given radio

        return self._reader

    @property
    def writer(self) -> object:
        # list of clients for a given AP at a given radio

        return self._writer

    @property
    def file_handle(self) -> object:

        return self._file_handle

    @property
    def phy_list(self) -> dict:
        # list of clients for a given AP at a given radio

        return self._phy_list

    @property
    def sta_list_inactive(self) -> dict:
        # list of clients for a given AP at a given radio

        return self._sta_list_inactive

    @property
    def sta_list_active(self) -> dict:
        # list of clients for a given AP at a given radio

        return self._sta_list_active

    def add_station(self, sta_info) -> None:
        """


        Parameters
        ----------
        SSHClient : object
            SSH client object for a given access point.

        Returns
        -------
        None
            DESCRIPTION.

        """
        print("adding station")
        for phy in self._phy_list:
            if sta_info["radio"] == phy:
                if sta_info["mac_addr"] not in list(self._sta_list_active[phy].keys()):
                    self._sta_list_active[phy][sta_info["mac_addr"]] = Station(
                        sta_info["radio"],
                        sta_info["mac_addr"],
                        sta_info["sup_rates"],
                        sta_info["timestamp"],
                    )

        pass

    def remove_station(self, sta_info) -> None:
        """


        Parameters
        ----------
        SSHClient : object
            SSH client object for a given access point.

        Returns
        -------
        None
            DESCRIPTION.

        """

        if sta_info["mac_addr"] not in list(
            self._sta_list_inactive[sta_info["radio"]].keys()
        ):
            self._sta_list_inactive[sta_info["radio"]][
                sta_info["mac_addr"]
            ] = self._sta_list_active[sta_info["radio"]][sta_info["mac_addr"]]

        self._sta_list_active[sta_info["radio"]].pop([sta_info["mac_addr"]], None)

        pass

    async def connect_AP(self, output_dir=""):
        """
        This async function takes a dictionary containing information about
        an AP and connects with it.

        Parameters
        ----------
        ap_info : dictionary
            contains parameters such as ID, IP Address and Port of an AP
        output_dir : str
            the main directory where results of the experiment are stored

        Returns
        -------
        ap_info : dictionary
            contains parameters such as ID, IP Address, Port, relevant file
            streams and connection status of an AP
        """

        self._data_dir = output_dir

        self._file_handle = open(output_dir + "/data_" + self._AP_ID + ".csv", "w")

        self._conn_handle = asyncio.open_connection(
            self._AP_IP, self._AP_MinstrelRCD_port
        )

        try:
            self._reader, self._writer = await asyncio.wait_for(
                self._conn_handle, timeout=5
            )

            logging.info(
                "Connected to {} : {} {}".format(
                    self._AP_ID, self._AP_IP, self._AP_SSH_port
                )
            )

            self._connection = True

        except (OSError, asyncio.TimeoutError, ConnectionError) as error_type:

            logging.error(
                "Failed to connect {} : {} {} -> {}".format(
                    self._AP_ID, self._AP_IP, self._AP_SSH_port, error_type
                )
            )

            self._connection = False

        pass

    def start_radios(self):
        """
        This async function for an AP starts the radios i.e. executes the command
        to enable rate control API.

        Parameters
        ----------
        ap_info : dictionary
            contains parameters such as ID, IP Address, Port, relevant file
            streams and connection status of an AP

        Returns
        -------
        None.

        """

        cmd_footer = ";stop"
        for phy in self._phy_list:
            cmd = phy + cmd_footer
            self._writer.write(cmd.encode("ascii") + b"\n")

        cmd_footer = ";start;stats;txs"
        for phy in self._phy_list:
            cmd = phy + cmd_footer
            self._writer.write(cmd.encode("ascii") + b"\n")

    async def set_rate(ap_handles) -> None:
        """


        Parameters
        ----------
        ap_handles : TYPE
            DESCRIPTION.

        Returns
        -------
        None
            DESCRIPTION.

        """

        try:
            print("in rate setter")

            APID = "AP2"
            phy = "phy1"
            macaddr = ap_handles[APID]["staList"]["wlan1"][0]
            writer = ap_handles[APID]["writer"]

            def cmd(phy, macaddr, rate):
                return phy + ";rates;" + macaddr + ";" + rate + ";1"

            while True:
                await asyncio.sleep(0.05)

                ap_handles = getStationList(ap_handles)
                print("setting rate now")
                writer.write((phy + ";manual").encode("ascii") + b"\n")
                rate_ind = str(random.Random().randint(80, 87))

                writer.write(cmd(phy, macaddr, rate_ind).encode("ascii") + b"\n")
                writer.write((phy + ";auto").encode("ascii") + b"\n")
        except KeyboardInterrupt:
            pass
        writer.close()

    def add_supp_rates(self, group_idx, max_offset):
        """


        Parameters
        ----------
        group_idx : TYPE
            DESCRIPTION.
        max_offset : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """
        if group_idx not in self._supp_rates:
            self.supp_rates.update({group_idx: max_offset})
        pass
