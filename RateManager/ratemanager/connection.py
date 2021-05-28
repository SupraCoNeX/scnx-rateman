# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Connection module
----------------

This module provides a collection of functions that enable starting and 
terminating a socket based connection to devices like access point routers 

"""

import socket

__all__ = [
    "open_connection",
    "close_connection",
]


def open_connection(host, port):
    socketHandle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socketHandle.connect((host, port))
    return socketHandle


def close_connection(socketHandle):
    socketHandle.close()
