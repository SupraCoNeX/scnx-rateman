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
    "open_sock_conn",
    "close_sock_conn",
    "obtain_SSHClient",
    "execute_command_SSH",
]


def open_sock_conn(host: str, port: int) -> object:
    """
    Open a socket connection for give host IP address and port number.

    Parameters
    ----------
    host : str
        IP address of host.
    port : int
        Associated port number.

    Returns
    -------
    object
        Socket object.

    """

    socketHandle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socketHandle.connect((host, port))
    return socketHandle


def close_sock_conn(socketHandle: object) -> None:
    """
    Close connection for given socket object.

    Parameters
    ----------
    socketHandle : object
        Socket object.

    Returns
    -------
    None

    """

    socketHandle.close()
    pass


def obtain_SSHClient(SSHHost: str, SSHPort: int, SSHUsr: str, SSHPass: str) -> object:
    """


    Parameters
    ----------
    SSHHost : str
        IP address of host.
    SSHPort : int
        Associated port number.
    SSHUsr : str
        Username of SSH connection.
    SSHPass : str
        Associated password.

    Returns
    -------
    object
        SSH client object.

    """

    SSHClient = paramiko.SSHClient()
    SSHClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    SSHClient.connect(SSHHost, SSHPort, SSHUsr, SSHPass)

    return SSHClient


def execute_command_SSH(SSHClient: object, cmd: str) -> None:
    """
    Execute a given command over an SSH connection.

    Parameters
    ----------
    SSHClient : object
        SSH client object.
    cmd : str
        Command to be executed.

    Returns
    -------
    None

    """

    SSHClient.exec_command(cmd)

    pass
