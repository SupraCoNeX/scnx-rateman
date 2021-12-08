# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Rate Manager Object
----------------

This class provides an object for Rate Manager that utilizes functions defined
in different modules. 

"""
import csv
import numpy as np
from .core import setup_rateman_tasks
import io
from datetime import datetime
import paramiko
import asyncio
import json
import telegram
import os


__all__ = ["RateMan"]


class RateMan:
    def __init__(self) -> None:

        self._accesspoints = dict()
        self._txsDataFrame = list()
        self._clients = dict()
        self._mcsRates = dict()

        self._loop = asyncio.get_event_loop()

    @property
    def clients(self):
        return self._clients

    @clients.setter
    def clients(self, updated_data: dict):
        self._clients = updated_data

    @property
    def accesspoints(self) -> dict:
        # provides a list of access points in the network
        # dict with APID keys, with each key having a dict with radios,
        # which is also a dict with clients
        return self._accesspoints

    @accesspoints.setter
    def accesspoints(self, net_info: dict):
        self._accesspoints = net_info

    @property
    def mcsRates(self):
        return self._mcsRates

    @property
    def loop(self):
        return self._loop

    def set_reader_stream(self, APID: str, reader):
        self._accesspoints[APID]["reader"] = reader

    def set_writer_stream(self, APID: str, writer):
        self._accesspoints[APID]["writer"] = writer

    def set_fileHandle(self, APID: str, fileHandle):
        self._accesspoints[APID]["fileHandle"] = fileHandle

    def set_conn(self, APID: str, status: bool):
        self._accesspoints[APID]["conn"] = status

    def get_conn(self, APID: str):
        net_info = self._accesspoints
        status = net_info[APID]["conn"]
        return status

    def add_station(self, APID: str, client_MAC: str, supp_rates: list):
        """
        Adds MACID (client), its supported rates and attempts and success for
        each rate to the client data strucutre

        Parameters
        ----------
        APID: str
            ID of the Access Point associated with the client MAC
        client_MAC : str
            MACID of the client
        supp_rates : list
            list of rates supported by the client

        Returns
        -------
        None.

        """
        init_client = dict()
        init_supp_rates = dict()
        init_rates = dict()
        init_stats = {"attempts": 0, "success": 0}

        for rate in supp_rates:
            init_rates.update({rate: init_stats.copy()})

        if APID not in self._clients:
            init_supp_rates.update({"supp_rates": init_rates})
            init_client.update({client_MAC: init_supp_rates})
            self._clients.update({APID: init_client})
        else:
            if client_MAC in self._clients[APID]:
                client_info = self._clients[APID][client_MAC]
                client_info["supp_rates"].update(init_rates)
            else:
                init_supp_rates.update({"supp_rates": init_rates})
                init_client.update({client_MAC: init_supp_rates})
                self._clients[APID].update({client_MAC: init_supp_rates})

    def remove_station(self, APID: str, client_MAC: str):
        if APID in self._clients:
            self._clients[APID].pop(client_MAC)

    def get_suppRates_AP(self, APID):
        return self.accesspoints[APID]["supp_rates"]

    def add_suppRate_AP(self, APID, groupIdx, max_offset):
        if groupIdx not in self._accesspoints[APID]["supp_rates"]:
            self.accesspoints[APID]["supp_rates"].update({groupIdx: max_offset})

    def update_attempts(self, APID, client_MAC, rate, attempts):
        """
        Updates the number of attempts for the provided rate, MACID and
        APID.

        Parameters
        ----------
        APID: str
            ID of the Access Point associated with the client MAC
        client_MAC : str
            MACID of the client
        rate : str
            rate index
        attempts: int
            number of attempts to be updated

        Returns
        -------
        None.

        """
        client_info = self._clients[APID][client_MAC]
        rate_stat = client_info["supp_rates"][rate]
        rate_stat["attempts"] = attempts

    def update_success(self, APID, client_MAC, rate, success):
        """
        Updates the number of successes for the provided rate, MACID and
        APID.

        Parameters
        ----------
        APID: str
            ID of the Access Point associated with the client MAC
        client_MAC : str
            MACID of the client
        rate : str
            rate index
        attempts: int
            number of attempts to be updated

        Returns
        -------
        None.

        """
        client_info = self._clients[APID][client_MAC]
        rate = client_info["supp_rates"][rate]
        rate["success"] = success

    def addaccesspoints(self, ap_list_filename: dir) -> None:
        """
        Function to add a list of access points available in a network.
        Each access point has given a unique ID and relevant information
        is organized as a dict in the Rate Manager object as the
        the 'accesspoints' variable.

        Parameters
        ----------
        filename : dir

        Returns
        -------
        None

        """

        self._ap_list_filename = ap_list_filename
        with open(ap_list_filename, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for currentAP in reader:

                APID = currentAP["APID"]
                IPAdd = currentAP["IPADD"]
                portSSH = int(currentAP["PORT"])
                portMinstrel = 21059  # default port for Minstrel-RCD

                self._accesspoints[APID] = APID
                self._accesspoints[APID] = currentAP
                self._accesspoints[APID]["PORT"] = portSSH
                self._accesspoints[APID]["MPORT"] = portMinstrel

                # phy list is hard-coded -> ToDo: obtain list automatically
                # using getPhyList function
                self._accesspoints[APID]["phyList"] = ["phy0", "phy1"]
                self._accesspoints[APID]["supp_rates"] = dict()

    def get_IdxOffset(self, groupIdx):
        return self._mcsRates[groupIdx]["offset"]

    def load_mcsRates(self, file):
        """
        Loads the RC_idx to MCS index conversion file into the mcsRates
        data structure

        Parameters
        ----------
        APID: str
            ID of the Access Point associated with the client MAC
        client_MAC : str
            MACID of the client
        rate : str
            rate index
        attempts: int
            number of attempts to be updated

        Returns
        -------
        None.

        """
        path = os.path.dirname(__file__) + file

        with open(path, newline="") as csvfile:
            dataRows = csv.reader(csvfile, delimiter=";")
            for row in dataRows:
                if dataRows.line_num == 1:
                    supp_format = "*;0;#group_mbits;index;offset;type;nss;bw;gi;mbits"
                    line = ";".join(row)
                    if not line == supp_format:
                        raise Exception(
                            "Index to rate conversion file not in supported format!"
                        )
                    continue

                groupIdx = row[3]
                rates = row[-1].split(",")
                if groupIdx not in self._mcsRates:
                    group_info = {
                        "offset": row[4],
                        "allRates": rates,
                    }
                    self._mcsRates.update({groupIdx: group_info})

    def mcsIdx_to_rate(mcsIdx):
        pass

    def start(self, duration: float, rateMan: object, output_dir: str = "") -> None:
        """
        Start monitoring of TX Status (txs) and Rate Control Statistics
        (rc_stats). Send notification about the experiment from RateMan
        Telegram Bot.

        Parameters
        ----------

        duration: float
            time duration for which the data from APs has to be collected

        output_dir : str
            directory to which parsed data is saved

        Returns
        -------
        None.

        """

        self._duration = duration

        text_start = (
            os.getcwd()
            + ":\n\nExperiment Started at "
            + str(datetime.now())
            + "\nTime duration: "
            + str(duration)
            + " seconds"
            + "\nAP List: "
            + self._ap_list_filename
        )

        self._notify(text_start)

        #self.load_mcsRates("rates.csv")

        time_start = datetime.now()

        self._loop.create_task(setup_rateman_tasks(rateMan, duration, output_dir))

        try:
            self._loop.run_forever()
        finally:
            # Notify RateMan telegram bot to send text_end to chat_ids in keys.json
            elapsed_time = datetime.now() - time_start
            text_end = (
                os.getcwd()
                + ":\n\nExperiment Finished at "
                + str(datetime.now())
                + "\n"
            )

            # If RateMan stopped earlier than the specified duration
            if elapsed_time.total_seconds() < duration:
                text_end += (
                    "Error: RateMan stopped before the specified time duration of "
                    + str(duration)
                    + "!\n"
                    + "RateMan was fetching data from "
                    + str(self._ap_list_filename)
                )
            else:
                text_end += (
                    "Data for the AP List, "
                    + str(self._ap_list_filename)
                    + ", has been successfully collected for "
                    + str(duration)
                    + " seconds!"
                )
            self._notify(text_end)

            self._loop.close()
        pass

    def _enableMinstrelRCD(self, SSHClient: object) -> None:
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

        cmd = "minstrel-rcd -h 0.0.0.0 &"
        execute_command_SSH(SSHClient, cmd)

        pass

    def _notify(self, text) -> None:
        """
        This function sends message (text) to all the chat_ids, listed in
        keys.json, from the RateMan Telegram Bot

        Parameters
        ----------
        text : str
            the content of the message that is to be sent by the RateMan
            Telegram Bot

        Returns
        -------
        None.

        """

        bot_token = "1655932249:AAGWAhAJwBwnI6Kk0LrQc7CvN44B8ju7TsQ"
        chat_ids = ["-580120177"]
        bot = telegram.Bot(token=bot_token)
        # Marking end of notification for readability
        text += "\n--------------------------------------------"
        for chat_id in chat_ids:
            # bot.sendMessage(chat_id=chat_id, text=text)
            pass
