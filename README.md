# Rate Manager

The RateManager or simply RateMan provides a Python-based package for
 - Monitoring of status through `txs` (TX status) and `rcs` (Rate control statistics) information of one or more access points in a network.
 - Rate control through setting of appropriate MCS Rate per client/station per access point.
 - Data collection and management from network measurements.

## Rate Control API 

The rate control API enables us to access information from kernel space into the user space. In addition to enabling monitoring of status infromation, the API allows us to execute routines to perform rate setting based on a user space algorithm. The API is designed for WiFi systems based on OpenWrt OS. 

Felix Fietkau is the maintainer of the API.

Latest version of OpenWrt with the patches related to the Rate Control API is available at

https://git.openwrt.org/?p=openwrt/staging/nbd.git;a=commit;h=f565e743c2ce88065b3da245a734fc50dd21d9a8

The API is named as Minstrel-Rate Control Daemon (`minstrel-rcd`)

Note that the RateMan package utilizes the Minstrel-RCD to perform it's functions and thus has little or no capabilities without the API.

In this section, we will cover the basic details of the `minstrel-rcd`.


### Capabilities:

Here, functions which can be run through the `minstrel-rcd` are considered as main functions and are listed in the table below.

|Function|Description|Kernel Function|Command example|Additional Information|
|:------:|:----------|:--------------|---------------|----------------------|
|dump    |Print out the supported data rate set for each client already connected - usefull to seperate tx_status packets that are supported by minstrel.|`minstrel_ht_dump_stations(mp)`|`phy0;dump`||
|start   |Enable live print outs of tx statuses of connected STAs.|`minstrel_ht_api_set_active(mp, true)`|`phy0;start`||
|stop    |Disable live print outs of tx statuses of connected STAs.|`minstrel_ht_api_set_active(mp, false)`|`phy0;stop`||
|manual  |Disable minstrel-ht of kernel space and enable manual rate settings.|`minstrel_ht_api_set_manual(mp, true)`|`phy0;manual`||
|auto    |Enable minstrel-ht of kernel space.|`minstrel_ht_api_set_manual(mp, false)`|`phy0;auto`||
|rates   |Set rate table with given rates.|`minstrel_ht_set_rates(mp, mi, args[1], args[2])`|`phy0;{MAC address};{list of rate idxs};{num of counts for each rate}`|`args[1]` = list of rates seperated by `,` and `args[2]` = list of number of tries for a rate until choosing next rate.|
|probe   |??? Look for STAs or APs with given supported rates???|`minstrel_ht_set_probe_rate(mp, mi, args[1])`|`phy0;probe;{MAC address};{rate_idx}`|`args[1]` = list of rates supported by STA or AP???|

_Note: `mp` stands for `phy0` or `phy1`. `mi` stands for a station (MAC address)._

> TODO: Check if the description of the capailities is correct?

### How to setup a connection to `minstrel-rcd`?

In this subsection, we provide a list of steps to communicate with the rate control API, monitor default rate control algorithm and perform MCS rate setting on your router. In this example, the router IP address is 10.10.200.2

  1. In terminal T1, connect to router via a SSH connection
  ```
  ssh root@10.10.200.2
  ```
  
  2. In terminal T1, enable `minstrel-rcd`. This opens a connection for other programmes to use the rate control API.
  ```
  minstrel-rcd -h 0.0.0.0 &
  ``` 
  We can use this connection to access directories containing specific information relevant to rate control.
  
  3. In another terminal (T2), start a TCP/IP connection via tool like telnet to communicate with the rate control API via minstrel-rcd. Minstrel-rcd operates over a designated port, in our case it is 21059.
  ```
  telnet 10.10.200.2 21059
  ```
  On connection, the API will print all possible command options followed by a list of MCS gups available for the given router. 

### Monitoring tasks
For monitoring the status of a given access point, make sure the TCP/IP connection is established. The `txs` and/or `rcs` can be received by triggering the following example commands. These commands are handled over the radio interfaces of the access point which are typically denoted as `phy0`, `phy1` and so on. 


#### To trigger receiving the `txs`, run:
  ```
  phy1;start
  ```
#### To trigger receiving the `rcs`, run:
  ```
  phy1;start;stats
  ```
#### To trigger receiving both `txs` and `rcs`, run:
  ```
  phy1;start;stats;txs
  ```
- Note that upon triggering this command, trace lines for `txs` and `rcs` will be printed separately.


### Monitoring information format
Once the monitoring tasks have been triggered as above, the `txs` and/or `rcs` information is received/printed in the Terminal T2. Format of these traces is as follows,

#### Format of trace for `txs` information
```
phyID;timestamp_sec;timestamp_nanosec;txs;macaddr;num_frames;num_acked;probe;rate0,count0;rate1,count1;rate2,count2;rate3,count3
```

|Field|Description|
|:------|:----------|
| `phyID`| Radio ID, e.g. `phy0`.|
|`timestamp_sec`| Timestamp for system time (Unix time) in seconds.|
|`timestamp_nanosec`| Timestamp for system time (Unix time) in nanoseconds. Complete timestamp is derived as `timestamp_sec.timestamp_nanosec`.|
|`txs`| Denotes that the traces is for TX status.|
|`macaddr`| MAC address of the station/client for which trace is received.|
|`num_frames`| Number of data packets in a given TX frame.|
|`num_acked`| Number of data packets of a frame which were successfully transmitted for which an `ACK` has been received.|
|`probe`| Binary index for type of frame. If `probe` = 1 for probing frame, 0 otherwise. |
|`rate0,count0`| 1st MCS rate (`rate0`) chosen for probing or data frame with `count0` attempts/tries.|
|`rate1,count1`| 2nd MCS rate (`rate1`) chosen for probing or data frame with `count1` attempts/tries.|
|`rate2,count2`| 3rd MCS rate (`rate2`) chosen for probing or data frame with `count2` attempts/tries.|
|`rate3,count3`| 4th MCS rate (`rate3`) chosen for probing or data frame with `count3` attempts/tries.|

E.g. 1. Successful transmission on 1st MCS rate
```
phy0;1626196159;112026795;txs;cc:32:e5:9d:ab:58;3;3;0;d7,1;0,0;0,0;0,0
```
Here we have a trace from `phy0` at timestamp, `1626196159.112026795`, for client with the MAC address of `cc:32:e5:9d:ab:58`, with `num_frames = 3`, `num_acked = 3`, `probe = 0` denotes that it was not a probing frame, index of 1st MCS rate tried `rate0` is `d7`, number of transmission tries for `rate0`, `count0 = 1`. In this case only one MCS rate tried and was successfully used. 

E.g. 2. Successful transmission on 2nd MCS rate 
```
phy1;1626189830;926593008;txs;d4:a3:3d:5f:76:4a;1;1;1;266,2;272,1;0,0;0,0
```
Here we have a trace from `phy1` at timestamp, `1626189830.926593008`, for client with the MAC address of `d4:a3:3d:5f:76:4a`, with `num_frames = 1`, `num_acked = 1`, `probe = 1` denotes that it was a probing frame, index of 1st MCS rate tried `rate0` is `266`, number of transmission tries for `rate0`, `count0 = 2`. In this case the `rate0` was not successful and hence a 2nd MCS rate with index `rate1` of `272` was tried `count1 = 1` times and this transmission was successful.

E.g. 3. Erroneous `txs` trace
```
phy1;1626189830;926593018;txs;86:f9:1e:47:68:da;2;0;0;0,0;0,0;0,0;0,0
```
In this case, the trace implies that no MCS rate has been tried.

#### How to Read the `rateX` Fields
Consider again the example from the previous section:
```
phy1;1626189830;926593008;txs;d4:a3:3d:5f:76:4a;1;1;1;266,2;272,1;0,0;0,0
```
The first digits of `rateX` tell us in which rate group to look. The rightmost digit from the rate entries gives us the group offset. *Note, that these are hex digits!*
In our example, rate `266` refers to the `6`th rate from group `26` and `272` refers to the `2`nd rate from group `27`. Looking at the `group` output mentioned above, we can find the exact rates. What `minstrel-rcd` is telling us is that we first tried to send a frame at rate **TODO RATE** twice before falling back to rate **TODO RATE** where transmission succeeded after one attempt.

#### Format of trace for `rcs` information
```
phyID;timestamp_sec;timestamp_nanosec;stats;macaddr;rate;avg_prob;avg_tp;cur_success;cur_attempts;hist_success;hist_attempts
```
Description of fields that are not present in `txs` trace:
|Field|Description|
|:------|:----------|
|`stats`| Denotes that the traces is for Rate Control Statistics.|
|`rate`| |
|`avg_prob`||
|`avg_tp`||
|`cur_success`||
|`cur_success`||
|`cur_attempts`||
|`hist_success`||
|`hist_attempts`||

> TODO: Add description of fields

  
E.g. 1. 
```
phy0;1626196159;020667844;stats;cc:32:e5:9d:ab:58;d7;3e8;281;1;1;c0d7;f6c4
```

> TODO: Explain example

  
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
     

### Rate Control Statistics



![alt tag](https://user-images.githubusercontent.com/79704080/112141900-385fd980-8bd6-11eb-99a2-5c18ff8e37e5.PNG)

> TODO: Add description of variables in table
     
    

 
 
 
 
 
 
 
 
 
 
 
 
 
 

