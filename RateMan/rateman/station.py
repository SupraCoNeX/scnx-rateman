# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Station Object
----------------

This class provides ... 

"""
import asyncio


__all__ = ["Station"]


class Station:
    def __init__(self, radio, mac_addr, sup_rates, timestamp) -> None:

        self._radio = radio
        self._mac_addr = mac_addr
        self._sup_rates = sup_rates
        self._latest_timestamp = timestamp
        self._stats = {}  # {rate: {timestamp, cur_atmp, cur_succ}}

        self._loop = asyncio.get_event_loop()

    @property
    def latest_timestamp(self) -> str:
        """


        Returns
        -------
        str
            DESCRIPTION.

        """

        return self._latest_timestamp

    @property
    def radio(self) -> str:
        """


        Returns
        -------
        str
            DESCRIPTION.

        """

        return self._radio

    @property
    def sup_rates(self) -> list:
        """


        Returns
        -------
        list
            DESCRIPTION.

        """

        return self._sup_rates

    @property
    def mac_addr(self) -> str:
        """


        Returns
        -------
        str
            DESCRIPTION.

        """

        return self._mac_addr

    @property
    def stats(self) -> dict:
        """


        Returns
        -------
        str
            DESCRIPTION.

        """

        return self._stats

    def update_stats(self, new_stats: dict) -> None:
        """


        Parameters
        ----------

        new_stats: dict


        Returns
        -------
        None.

        """

        for rate in new_stats.keys():
            timestamp = new_stats[rate]["timestamp"]
            self._stats[rate] = new_stats[rate]
            if timestamp > self._latest_timestamp:
                self._latest_timestamp = timestamp

        print(self._stats)

        pass

    def empty_stats(self) -> None:
        """


        Parameters
        ----------

        new_stats: dict


        Returns
        -------
        None.

        """

        self._stats = {}

        pass
