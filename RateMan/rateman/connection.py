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
import paramiko

__all__ = [
    "open_connection",
    "close_connection",
    "obtainSSHClient",
    "execute_command_SSH",
]


def open_connection(host, port):
    socketHandle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socketHandle.connect((host, port))
    return socketHandle


def close_connection(socketHandle):
    socketHandle.close()


def obtainSSHClient(SSHHost, SSHPort, SSHUsr, SSHPass):

    SSHClient = paramiko.SSHClient()
    SSHClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    SSHClient.connect(SSHHost, SSHPort, SSHUsr, SSHPass)

    return SSHClient


def execute_command_SSH(SSHClient, cmd: str):

    SSHClient.exec_command(cmd)
