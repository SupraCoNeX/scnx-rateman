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
from datetime import datetime
import asyncio
import json
import telegram
import os
from .accesspoint import AccessPoint
from .manage_asyncio import *

__all__ = ["RateMan"]


class RateMan:
    def __init__(self) -> None:

        self._net_info = {}
        self._ap_handles = {}
        self._accesspoints = {}
        self._meas_info = ""

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

    def add_ap_list(self, ap_list_filename: dir) -> None:
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
            for cur_AP in reader:

                AP_ID = cur_AP["APID"]
                AP_IP = cur_AP["IPADD"]
                AP_SSH_port = int(cur_AP["PORT"])
                AP_MinstrelRCD_port = 21059

                self._net_info[AP_ID] = AP_ID
                self._net_info[AP_ID] = cur_AP
                self._net_info[AP_ID]["SSHPORT"] = AP_SSH_port
                self._net_info[AP_ID]["MPORT"] = AP_MinstrelRCD_port

                AP_handle = AccessPoint(AP_ID, AP_IP, AP_SSH_port, AP_MinstrelRCD_port)
                self._ap_handles[AP_ID] = AP_handle

        pass

    def start(
        self, duration: float, notify: bool = False, output_dir: str = ""
    ) -> None:
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

        if notify:
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
            time_start = datetime.now()

        self._loop.create_task(setup_ap_tasks(self._ap_handles, duration, output_dir))
        try:
            self._loop.run_forever()
        finally:
            if notify:
                elapsed_time = datetime.now() - time_start
                text_end = (
                    os.getcwd()
                    + ":\n\nExperiment Finished at "
                    + str(datetime.now())
                    + "\n"
                )

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

        original_cwd = os.getcwd()

        dirpath = os.path.dirname(__file__)
        os.chdir(dirpath)

        with open("../docs/keys.json", "r") as telegram_keys:
            keys = json.load(telegram_keys)
            bot_token = keys["bot_token"]
            bot = telegram.Bot(token=bot_token)

            text += "\n--------------------------------------------"

            for chat_id in keys["chat_ids"]:
                bot.sendMessage(chat_id=chat_id, text=text)

        os.chdir(original_cwd)
