```
 __                             
 )_)  _  _)_   _   )\/)  _   _  
/ \  (_( (_   )_) (  (  (_( ) ) 
             (_                 
```

**...provides a Python API to control IEEE 8021.11 transmit rate & power per station across a WiFi network using orca-rcd**


## User Space Resource Control Interface
Rateman performs resource control per station using individual `asyncio` tasks. In order to perform user space rate and power control, the station has to be switched into the appropriate mode. There are two parameters, rate control and power control, and both can either be in `auto` mode or `manual` mode. In auto mode control of the parameter in question is left to the wireless device's kernel and/or chipset driver while manual mode enables us to control it directly. Configuring the modes is done using the functions `Station::set_manual_rc_mode()` and `Station::set_manual_tpc_mode()`.
In order to write a user space resource control scheme, one simply needs to create a python module exposing two functions: `configure()` and `run()`.

- `configure()` has the following signature: `async def configure(sta: rateman.Station, **rc_opts: dict) -> object`. It receives as arguments the station for which the resource control scheme is to be stared as well as configuration options in the form of a python dictionary. `configure()` is expected to initialize the resource control scheme and configure the station. For example, if the scheme only performs rate control and leaves transmit power control to the device, `configure()` would contain the following lines.

  ```
  async def configure(sta: rateman.Station, **rc_opts: dict) -> object:
        sta.set_manual_rc_mode(True)  # enable manual rate control
        sta.set_manual_tpc_mode(False)  # enable automatic transmit power control

        # ...
  ```

  `configure()` is expected to terminate and return anything that the resource control scheme needs for operation. Its returned `object` is passed to `run()` as argument directly.

- `run()` has the following signature `async def run(args: object) -> None:` and is intended to run indefinitely. To this end, it gets scheduled in its own `asyncio` task after `configure()` returns and should contain some form of infinite loop.

### User Space Resource Control Funtions
These are the relevant functions that `Station` objects expose for performing resource control:

- `async def set_manual_rc_mode(self, enable: bool) -> None:`

  To switch the `Station` into `manual` or `auto` rate control mode.
- `async def set_manual_tpc_mode(self, enable: bool) -> None:`

  To switch the `Station` into `manual` or `auto` transmit power control mode.
- `async def set_rates(self, rates: list, counts: list) -> None:`

  To set the rates and retry counts of the `Station`'s MRR.
- `async def set_power(self, pwrs: list) -> None:`

  To set the transmit powers for the `Station`'s MRR.
- `async def set_rates_and_power(self, rates: list, counts: list, pwrs: list) -> None:`

  To set rates, retry counts, and tramsit powers for the `Station`'s MRR.
- `async def set_probe_rate(self, rate: str, count: int, txpwr: int) -> None:`

  To perform rate sampling of the given rate at the given transmit power for the given number of attempts.

## Examples

The examples directory contains simple examples showcasing Rateman's capabilities and its interface. To run them you require a wireless device running [orca-rcd](https://github.com/SupraCoNeX/orca-rcd) with at least one associated station. For example, to run the `basic.py` example, execute
```
python scnx-rateman/examples/basic.py <NAME>:<IPADDR>:<RCDPORT>
```

where 

- `NAME` is an arbitrary name used to identify the device on which orca-rcd runs,
- `IPADDR` is that device's IP address, and
- `RCDPORT` is the port orca-rcd listens on. If you omit this option, it will default to 21059.

On the console, you should see detailed logs about rateman's actions as well as the raw event data rateman receives from orca-rcd. Take a look at the other examples showcasing different capabilities. The files contain extensive comments explaining what is being done.
