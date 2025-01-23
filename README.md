```
________         _____
___  __ \______ ___  /______ _______ ___ ______ ________
__  /_/ /_  __ `/_  __/_  _ \__  __ `__ \_  __ `/__  __ \
_  _, _/ / /_/ / / /_  /  __/_  / / / / // /_/ / _  / / /
/_/ |_|  \__,_/  \__/  \___/ /_/ /_/ /_/ \__,_/  /_/ /_/
```

**...provides a Python package to control IEEE 802.11 transmit rate & power per station across a 
WiFi network using orca-rcd**

RateMan is an interface to utilize the control and monitoring capabilities of the Open-source 
Resource Control API (ORCA). It facilitates WiFi resource control on a per-station basis for 
real WiFi networks using COTS hardware. Researchers have unprecedented freedom to implement 
their new rate and power adaptation algorithms using RateMan.  

## Highlights

- Allows handling of resource control over multiple accesspoints on a per-station basis.
- Wide range of trace information including attempt and success counts for transmitted frames.
- User space execution of control algorithms. 
- Passive trace collection for offline analysis. 

## Overview

We implemented RateMan to simplify and speed-up the process of developing novel WiFi resource 
control algorithms. Much of the state-of-the-art rate control algorithms are evaluated using 
simulation tools. This is arguably insufficient for practical research. We sort to address this 
gap through our work.

### Authors

We are a team of researchers at Hochschule Nordhausen, Fraunhofer HHI, TU Braunschweig, BISDN, New 
Media Net, etc.

## ⬇️ Installation

This package is compatible with Python 3.11 and above.

After cloning this repository run,

```bash
pip install -e <scnx-rateman directory>
```

## Testing your setup

In order to quickly see if rateman is able to connect to [orca-rcd](https://github.com/SupraCoNeX/orca-rcd) instances in your network, 
you can run rateman as a package:
```
python -m rateman --show-state <NAME>:<IPADDR>:<RCDPORT> [<NAME>:<IPADDR>:<RCDPORT> ...]
```
where

- `NAME` is an arbitrary name used to identify the device on which orca-rcd runs,
- `IPADDR` is that device's IP address, and
- `RCDPORT` is the port orca-rcd listens on. If you omit this option, it will default to 21059.

This will make rateman connect to the given device\[s\] and print information about their state.

## Usage

In order to perform user space rate and power control, the station has to be switched into the 
appropriate mode. There are two parameters, rate control and power control, and both can either be 
in `auto` mode or `manual` mode.In auto mode control of the parameter in question is left to the 
wireless device's kernel and/or chipset driver while manual mode enables us to control it directly. 
Configuring the modes is done using the functions `Station::set_manual_rc_mode()` and 
`Station::set_manual_tpc_mode()`. In order to write a user space resource control scheme, 
one simply needs to create a python module exposing two functions: `configure()` and `run()`.

- `configure()` has the following signature: `async def configure(sta: rateman.Station, **rc_opts: dict) -> object`. It receives as arguments the station for which the resource control scheme is to be started as well as configuration options in the form of a python dictionary. `configure()` is expected to initialize the resource control scheme and configure the station. For example, if the scheme only performs rate control and leaves transmit power control to the device, `configure()` would contain the following lines.

  ```
  async def configure(sta: rateman.Station, **rc_opts: dict) -> object:
        sta.set_manual_rc_mode(True)  # enable manual rate control
        sta.set_manual_tpc_mode(False)  # enable automatic transmit power control

        # ...
  ```

  `configure()` is expected to terminate and return anything that the resource control scheme needs 
- for operation. Its returned `object` is passed to `run()` as argument directly.

- `run()` has the following signature `async def run(args: object) -> None:` and is intended to run 
- indefinitely. To this end, it gets scheduled in its own `asyncio` task after `configure()` returns 
- and should contain some form of infinite loop.

In addition to `configure()` and `run()`, resource control schemes can optionally expose two 
additional functions, `pause()` and `resume()`. As the names suggest, these permit to stop the 
resource control mechanism without destroying its state so that operation can resume at a later time. 
Their function signatures are the same as for `run()`. While the resource control scheme is paused, 
resource control for the station is handled as though it was in automatic rate and power control 
mode. In order to make rateman pause the resource control scheme instead of stopping it when the 
station disassociates, mark the station for pause/resume operation by setting 
`sta.pause_rc_on_disassoc = True`. Note, that rateman will automatically switch rate and power 
control to `auto` for the station when the resource control scheme is paused. However, it is up to 
the resource control scheme's `resume()` function to re-enable the appropriate rate and/or power 
control modes as in `configure()`.

### User Space Resource Control Functions
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

The examples directory contains simple examples showcasing Rateman's capabilities and its interface. 
To run them you require a wireless device running [orca-rcd](https://github.com/SupraCoNeX/orca-rcd) with at least one associated station. 
For example, to run the `basic.py` example, execute
```
python scnx-rateman/examples/basic.py <NAME>:<IPADDR>:<RCDPORT>
```

where

- `NAME` is an arbitrary name used to identify the device on which orca-rcd runs,
- `IPADDR` is that device's IP address, and
- `RCDPORT` is the port orca-rcd listens on. If you omit this option, it will default to 21059.

On the console, you should see detailed logs about rateman's actions as well as the raw event data rateman receives from orca-rcd. Take a look at the other examples showcasing different capabilities. The files contain extensive comments explaining what is being done.

## Citing ORCA-based WiFi Resource Control Toolchain 

If you use ORCA, RateMan and its toolchain in your research, please cite our work using the 
following reference.

```bibtex
@inproceedings{orcawifirc,
	title        = {Open-source Resource Control API for real IEEE 802.11 Networks},
	author       = {Sankalp Prakash Pawar and Prashiddha Dhoj Thapa and Jonas Jelonek and Martin Le and Arne Kappen and Nick Hainke and Thomas Huehn and Julius Schulz-Zander and Henrike Wissing and Felix Fietkau},
	year         = 2024,
	booktitle    = {The 30th Annual International Conference on Mobile Computing and Networking (ACM MobiCom '24), November 18--22, 2024, Washington D.C., DC, USA},
	location     = {Washington D.C., DC, USA},
	publisher    = {ACM},
	address      = {New York, NY, USA},
	doi          = {10.1145/3636534.3697314},
	isbn         = {979-8-4007-0489-5/24/11}
}
```
