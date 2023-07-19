```
 __                             
 )_)  _  _)_   _   )\/)  _   _  
/ \  (_( (_   )_) (  (  (_( ) ) 
             (_                 
```

**...provides a user-space API to control IEEE 8021.11 transmit rate & power per station**

## Examples

The examples directory contains simple examples showcasing Rateman's capabilities and its interface. To run them you require a wireless device running [orca-rcd](https://github.com/SupraCoNeX/orca-rcd) with at least one associated station. For example, to run the `basic.py` example, execute
```
python scnx-rateman/examples/basic.py <NAME>:<IPADDR>:<RCDPORT>
```

where 

- <NAME> is an arbitrary name used to identify the device on which orca-rcd runs,
- <IPADDR> is that device's IP address, and
- <RCDPORT> is the port orca-rcd listens on. If you omit this option, it will default to 21059.

You should see detailed logs about rateman's actions as well as the raw event data rateman receives from orca-rcd on the console.
Take a look at the other examples showcasing different capabilities. The files contain extensive comments explaining what is being done.
