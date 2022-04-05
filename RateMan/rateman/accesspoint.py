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

__all__ = ["Accesspoint"]


class Accesspoint:
    def __init__(self, AP_ID, AP_IP, AP_SSH_port, AP_MinstrelRCD_port=21059) -> None:

        self._AP_ID = AP_ID
        self._AP_IP = AP_IP
        self._AP_SSH_port = AP_SSH_port
        self._AP_MinstrelRCD_port = AP_MinstrelRCD_port
        self._supp_rates = ""
        self._sta_list_all = []
        self._sta_list_active = []
        self._phy_list = ["phy0", "phy1"]
        self._connection = False

    @property
    def stations(self) -> dict:
        # list of clients for a given AP at a given radio

        return 0

    @property
    def accesspoints(self) -> dict:
        # provides a list of access points in the network
        # dict with APID keys, with each key having a dict with radios,
        # which is also a dict with clients

        return self._accesspoints

    def add_station(self, sta_IP) -> None:
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

        pass

    async def connect_AP(self, output_dir):
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

        self._fileHandle = open(output_dir + "/data_" + self._AP_ID + ".csv", "w")

        self._conn_handle = asyncio.open_connection(self._AP_IP, self._AP_SSH_port)

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
