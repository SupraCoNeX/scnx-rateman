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
from .connman import *
from .core import *
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

        self._accesspoints = {}
        self._txsDataFrame = []
        self._rcstats = []

        self._loop = asyncio.get_event_loop()

    @property
    def clients(self) -> dict:
        # list of clients for a given AP at a given radio

        return 0

    @property
    def accesspoints(self) -> dict:
        # provides a list of access points in the network
        # dict with APID keys, with each key having a dict with radios,
        # which is also a dict with clients

        return self._accesspoints

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

    def start(self, duration: float, output_dir: str = "") -> None:
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

        # Notify RateMan telegram bot to send text_start to the listed chat_ids in keys.json
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

        # self._notify(text_start)

        time_start = datetime.now()

        self._loop.create_task(
            setup_rateman_tasks(self._accesspoints, self._loop, duration, output_dir)
        )

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
            # self._notify(text_end)

            self._loop.close()
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
            bot.sendMessage(chat_id=chat_id, text=text)
