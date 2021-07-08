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
import time
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

    def addaccesspoints(self, filename: dir) -> None:
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
        with open(filename, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for currentAP in reader:

                APID = currentAP["APID"]
                IPAdd = currentAP["IPADD"]
                portSSH = int(currentAP["PORT"])
                portMinstrel = 21059 # default port for Minstrel-RCD

                self._accesspoints[APID] = APID
                self._accesspoints[APID] = currentAP
                self._accesspoints[APID]["PORT"] = portSSH
                self._accesspoints[APID]["MPORT"] = portMinstrel

                # phy list is hard-coded -> ToDo: obtain list automatically
                # using getPhyList function
                self._accesspoints[APID]["phyList"] = ['phy0', 'phy1']

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

    def start(self, path, duration: float) -> None:
        """
        Start monitoring of TX Status (txs) and Rate Control Statistics
        (rc_stats).

        Parameters
        ----------
        path : str
            the path of the AP list from which the TX Status (txs) and 
            Rate Control Statistics (rc_stats) are to be fetched.

        duration: float
            time duration for which the data from APs has to be collected

        Returns
        -------
        None.

        """

        self._duration = duration

        # Notify RateMan telegram bot to send text_start to chat_ids in keys.json
        text_start = str(os.path.dirname(os.path.abspath(__file__))) + ": Experiment started at " + str(time.time())
        self.notify(text_start)

        self._loop.create_task(main_AP_tasks(self._accesspoints, self._loop,
                                             self._duration))

        try:
            self._loop.run_forever()
        finally:
            # Notify RateMan telegram bot to send text_end to chat_ids in keys.json
            text_end = "Experiment Finished! Data for the AP List, " + str(path) + ", has been done collecting for " + str(duration) + " seconds!"
            self.notify(text_end)

            self._loop.close()
        pass

    def savedata(self, host: str, port: str) -> None:

        # data is structured per AP and can be structure per client

        pass

    def notify(self, text) -> None:
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
        with open('../docs/keys.json', 'r') as telegram_keys:
            keys = json.load(telegram_keys)
            bot_token = keys['bot_token']
            bot = telegram.Bot(token=bot_token)
            for chat_id in keys['chat_ids']:
                bot.sendMessage(chat_id=chat_id, text=text)
        print("Notified all users!")

