```
 __                             
 )_)  _  _)_   _   )\/)  _   _  
/ \  (_( (_   )_) (  (  (_( ) ) 
             (_                 
```

**...provides a user-space Python package to annotate IEEE 8021.11 transmit rate & power per packet, hence per connected STA over multiple APs**

# RateMan
__enables the use of ```mac802.11 kernel <-> user-space``` API to control per packet rate & transmit power resource allocations.__

## Main features
 - Monitoring of status through TX status (`txs`), Received Signal Strength Indicator (`rxs`), and Rate control statistics (`stats`) information of one or more access points in a network.
 - Rate and TX power control through setting of appropriate MCS Rate and TX power level in dBm per client/station per access point.
 - Callback mechanism for online handling and processing of monitoring information, such as to save resource control traces.
 - Interface for Python-based resource control algorithm packages that rely on monitoring information. 


## Prerequisites
- RateMan is a controller based on the Open-source Resource Control API for real WiFi networks (ORCA) which constitutes of Linux kernel patches for (I) ```mac802.11 kernel <-> user space``` access to rate and power control information, and (II) remote control and telemetry interface. More information on [ORCA](https://github.com/SupraCoNeX/minstrel-rcd#readme)
- Python >= 3.8
  - no additional packages or libraries are required apart from those available in standard Python installation.


## Usage
### Stand-alone Package

#### Examples




### Within SupraCoNeX Experimentation Framework

#### Refer to scnx-experimentor



## Abstractions
### RateMan 
### AccessPoint
### Station
### RateControlAlgorithm


## Asyncio Task/Coroutine Management


## Developing your Own Resource Control Algorithm in User Space




 
 
 
 
 
 
 
 
 
 
 
 
 
 
