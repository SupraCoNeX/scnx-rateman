# Rate Control API Documentation 

The rate control API enables monitoring and controlling of rate control algorithms for WiFi systems based on OpenWrt OS. 

The API is developed by Felix Fietkau and is available as a patch at:

https://git.openwrt.org/?p=openwrt/staging/nbd.git;a=commit;h=f565e743c2ce88065b3da245a734fc50dd21d9a8


## Overview
> TODO: Insert some figure with all main blocks/packages of the Rate Control API with a short description.


## How to install?
> TODO

## Capabilities:

Here, functions which can be run through the `minstrel-rcd` are considered as main functions and are listed in the table below.

|Function|Description|Kernel Function|Command example|Additional Information|
|:------:|:----------|:--------------|---------------|----------------------|
|dump    |??? Print out supported rates of connected STAs???|`minstrel_ht_dump_stations(mp)`|`phy0;dump`||
|start   |Enable live print outs of tx statuses of connected STAs.|`minstrel_ht_api_set_active(mp, true)`|`phy0;start`||
|stop    |Disable live print outs of tx statuses of connected STAs.|`minstrel_ht_api_set_active(mp, false)`|`phy0;stop`||
|manual  |Disable minstrel-ht of kernel space and enable manual rate settings.|`minstrel_ht_api_set_manual(mp, true)`|`phy0;manual`||
|auto    |Enable minstrel-ht of kernel space.|`minstrel_ht_api_set_manual(mp, false)`|`phy0;auto`||
|rates   |Set rate table with given rates.|`minstrel_ht_set_rates(mp, mi, args[1], args[2])`|`phy0;{MAC address};{list of rate idxs};{num of counts for each rate}`|`args[1]` = list of rates seperated by `,` and `args[2]` = list of number of tries for a rate until choosing next rate.|
|probe   |??? Look for STAs or APs with given supported rates???|`minstrel_ht_set_probe_rate(mp, mi, args[1])`|`phy0;probe;{MAC address};{rate_idx}`|`args[1]` = list of rates supported by STA or AP???|

_Note: `mp` stands for `phy0` or `phy1`. `mi` stands for a station (MAC address)._

> TODO: Check if the description of the capailities is correct?

## How to setup a connection to  the rate control API?

In this section, we provide a list of steps to communicate with the rate control API, monitor default rate control algorithm and perform MCS rate setting on your router. In this example, the router IP address is 10.10.200.2

  1. In a new terminal (T1), enable Minstrel remote control daemon (`minstrel-rcd`) in the background. This opens a connection for other programmes to use the rate control API.
  ```
  minstrel-rcd -h 0.0.0.0 &
  ```
    
  2. In terminal T1, connect to router via a SSH connection
  ```
  ssh root@10.10.200.2
  ```
  We can use this connection to access directories containing specific information relevant to rate control.
  
  3. In another terminal (T2), start a TCP/IP connection via tool like telnet to communicate with the rate control API via minstrel-rcd. Minstrel-rcd operates over a designated port, in our case it is 21059.
  ```
  telnet 10.10.200.2 21059
  ```
  On connection, the API will print all possible command options followed by a list of MCS gups available for the given router. 

### How to monitor rate control by receiving the TX status?

Upon establishing a TCP/IP connection with the rate control API in T2, to monitor the tx status of a WiFi interface (usually named `phy0` or `phy1`) run:
  ```
  phy1;start
  ```
  > Due to some bug(?), sometimes monitoring the tx status does not work right from the start in the current version (VERSION HERE), and a restart of the telnet connection is required (see step 3 above).

### How to set MCS rates?

Up on establishing a TCP/IP connection with the rate control API in T2, you can use the following steps to perform rate setting
  
  1. Enable rate control API for a given radio using the command:
  ```
  phy1;start
  ```
  This command enables a continuous string of TX_Status.
       
  2. Enable manual rate setting using the command:
  ```
  phy1;manual
  ```
  This command also disables the default rate control algorithm, in our case Minstrel-HT.
    
  3. Set desired MCS rate using the command format:
  ```
  phy1;rates;<macaddr>;<rates>;<counts>
  ```    
  Actual rate setting is done using the `rates` argument in the second position. Note that the `rates` to be set must be the HEX version of the rate `idx` found in the `rc_stats` table.
     

## Rate Control Statistics



![alt tag](https://cryptpad.fr/file/#/2/file/RpjMy4WGupnh5KN-filC8APG/)
  
  
> TODO: Add description of variables in table
     
    

 
 
 
 
 
 
 
 
 
 
 
 
 
 

