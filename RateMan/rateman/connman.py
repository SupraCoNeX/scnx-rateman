# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org
#

r"""
Connection module
----------------

This module provides a collection of functions that enable starting and 
terminating an SSH based connection to devices like access point routers. 
Functions to obtain certain data from the APs are available too. 

"""

import socket
import paramiko

__all__ = [
    "obtain_SSHClient",
    "execute_command_SSH",
    "getPhyList",
    "getWLANList",
    "getStationList",
]


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


def getPhyList(SSHClient: object) -> list:
    """
    Get a list of the available radio devices for a given access point.

    Parameters
    ----------
    SSHClient : object
        SSH client object for a given access point.

    Returns
    -------
    list
        List containing Phy ID strings.

    """

    command = "iw phy"

    stdin, stdout, stderr = SSHClient.exec_command(command)

    lines = stdout.readlines()

    phy_list = []
    for line in lines:
        if "Wiphy" in line:
            phy_list.append(line[6:-1])

    return phy_list


def getWLANList(SSHClient: object) -> list:
    """
    Get a list of the available WLAN devices for a given access point.
    Number of WLAN devices corresponds to the number of radios.

    Parameters
    ----------
    SSHClient : object
        SSH client object for a given access point.

    Returns
    -------
    list
        List containing WLAN device ID strings.

    """

    command = "iw dev"

    stdin, stdout, stderr = SSHClient.exec_command(command)

    lines = stdout.readlines()

    wlan_list = []
    for line in lines:
        if "Interface" in line:
            wlan_list.append(line[11:-1])

    return wlan_list


def getStationList(APInfo: dict) -> None:
    """
    Get list of stations connected to a given WLAN device of the given
    access point.


    Parameters
    ----------

    APInfo : dict
        Dictionary with information about available access points.

    Returns
    -------
    None

    """

    APIDs = list(APInfo.keys())

    for APID in APIDs:

        SSHClient = APInfo[APID]["SSHClient"]
        if SSHClient != "not available":
            for wlan in APInfo[APID]["wlanList"]:
                station_list = []
                command = "iw dev " + wlan + " station dump"
                stdin, stdout, stderr = SSHClient.exec_command(command)
                lines = stdout.readlines()
                for line in lines:
                    if "Station" in line:
                        station_list.append(line[8:25])
                APInfo[APID]["staList"][wlan] = station_list

    return APInfo


def get_meta_data(APInfo: dict) -> None:
    APIDs = list(APInfo.keys())

    metadata_cmds = ["uname -a", "uptime"]

    pass
