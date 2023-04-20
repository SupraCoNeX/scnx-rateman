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
- RateMan is a controller based on the Open-source Resource Control API for real WiFi networks (ORCA) which constitutes of Linux kernel patches for (I) ```mac802.11 kernel <-> user space``` access to rate and power control information, and (II) remote control and telemetry interface. More information on [ORCA](https://github.com/SupraCoNeX/minstrel-rcd#readme).
- Python >= 3.8
  - no additional packages or libraries are required apart from those available in standard Python installation.


## Usage
### Stand-alone Package
After cloning the `scnx-rateman` repository, install the `rateman` package with 
```
    pip install -e <package-dir>
```
The `-e` installs the package in edit mode in case you plan on continually pull onto a development branch. The `<package-dir>` is expected to be `scnx-rateman` folder, or generally where the `pyproject.toml` is located. 

#### Examples
Basic format to run `rateman` examples
```
    python <example.py> ap-list options
```
Examples are located under the `...scnx-rateman/examples/` directory. 

##### Passive trace collection
This example demonstrates the collection of monitoring information via `txs` information per AP using the default Linux kernel mac80211 rate control - [Minstrel-HT](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/net/mac80211/rc80211_minstrel_ht.c?id=81`5816493b7589e74ff4e1e7eaf3aadc7b73621). To collect trace over an AP with IP `10.10.10.1`, run the

```
    python passive-tracing.py AP1:10.10.10.1 
```

##### Active rate control
A user space rate control algorithm implemented as a Python package can be used to perform rate control over a given list of APs

```
    python passive-tracing.py AP1:10.10.10.1 -r <rate-control-package-name>
```
Here the option `-r` is used to parse the `<rate-control-package-name>`. Within `rateman` the rate control package is imported hence this argument must match the exact package name. This is case, the rate control is performed using the user space algorithm instead of the default kernel algorithm.

##### Active rate and power control


### Within SupraCoNeX Experimentation Framework

#### Refer to scnx-experimentor


## Abstractions
### RateMan 
### AccessPoint
### Station
### RateControlAlgorithm


## Asyncio Task/Coroutine Management


## Developing your Own Resource Control Algorithm in User Space





 
 
 
 
 
 
 
 
 
 
 
 
 
 
