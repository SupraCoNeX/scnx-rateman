# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#
import asyncio


__all__ = ["Station"]


class Station:
    def __init__(self, radio, mac_addr, supp_rates, timestamp) -> None:
        self._radio = radio
        self._mac_addr = mac_addr
        self._supp_rates = supp_rates
        self._latest_timestamp = timestamp
        self._stats = {}

    @property
    def latest_timestamp(self) -> str:
        return self._latest_timestamp

    @property
    def radio(self) -> str:
        return self._radio

    @radio.setter
    def radio(self, radio):
        self._radio = radio

    @property
    def supp_rates(self) -> list:
        return self._supp_rates

    @property
    def mac_addr(self) -> str:
        return self._mac_addr

    @property
    def stats(self) -> dict:
        return self._stats

    def lowest_supp_rate(self):
        return self._supp_rates[0]

    def update_stats(self, timestamp, info: dict) -> None:
        for rate, stats in info.items():
            if timestamp > self._latest_timestamp:
                self._latest_timestamp = timestamp
                self._stats[rate] = stats

    def check_rate_entry(self, rate):
        return rate in self._stats

    def get_attempts(self, rate):
        return self._stats[rate]["attempts"]

    def get_successes(self, rate):
        return self._stats[rate]["success"]

    def reset_stats(self) -> None:
        self._stats = {}

    def __str__(self):
        return f"STA[{self._mac_addr}]"
