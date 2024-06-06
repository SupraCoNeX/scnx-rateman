import argparse
import sys
import asyncio
import logging
import rateman
import traceback
from contextlib import suppress
import ast
from .accesspoint import *


def dump_sta_rate_set(sta):
    supported = sta.supported_rates
    begin = None
    prev = None
    ranges = []
    for grp, info in sta.accesspoint.all_rate_info.items():
        for rate in info["rate_inds"]:
            if rate in supported:
                if not begin:
                    begin = rate
            else:
                if begin:
                    ranges.append(f"{begin}-{prev}")

                begin = None

            prev = rate

    if prev in supported:
        if begin:
            ranges.append(f"{begin}-{prev}")

    print("          supported rates: " + ", ".join(ranges))


def dump_stas(ap, radio, interface):
    for sta in [sta for sta in ap.stations(radio) if sta.interface == interface]:
        rc = sta.rate_control[0]
        if rc == "minstrel_ht_kernel_space":
            update_freq = sta.kernel_stats_update_freq
            sample_freq = sta.kernel_sample_freq
            rc += f" (update_freq={update_freq}Hz sample_freq={sample_freq}Hz)"
        elif sta.rc_paused:
            rc += " (paused)"

        print(f"        + {sta.mac_addr} [rc={sta.rc_mode} tpc={sta.tpc_mode} rc_alg={rc}]")
        dump_sta_rate_set(sta)


def dump_interfaces(ap, radio):
    print("      interfaces:")
    for iface in ap.interfaces(radio):
        print(f"      - {iface}")
        dump_stas(ap, radio, iface)


def format_tpc_info(ap, radio):
    if ap.radios[radio]["tpc"] is None:
        return "type=not"

    info = f"type={ap.radios[radio]['tpc']['type']}"

    txpowers = ap.txpowers(radio)
    info += f", txpowers=(0..{len(txpowers) - 1}) {txpowers}"

    return info


def dump_radios(ap):
    for radio in ap.radios:
        print(
            """  - %(radio)s
      driver: %(drv)s
      events: %(ev)s
      tpc: %(tpc)s
      features: %(features)s"""
            % dict(
                radio=radio,
                drv=ap.driver(radio),
                ev=",".join(ap.enabled_events(radio)),
                tpc=format_tpc_info(ap, radio),
                features=", ".join([f"{f}={s}" for f, s in ap._radios[radio]["features"].items()]),
            )
        )

        dump_interfaces(ap, radio)


def show_state(rm):
    for ap in rm.accesspoints:
        version = ap.api_version
        print(
            """
%(name)s:
  connected: %(conn)s
  version: %(version)s
  radios:"""
            % dict(
                name=ap.name,
                conn=("yes" if ap.connected else "no"),
                version=f"{version[0]}.{version[1]}.{version[2]}" if version else "N/A",
            )
        )
        dump_radios(ap)


def setup_logger(verbose):
    logging.basicConfig(format="[LOG] %(asctime)s - %(name)s - %(message)s")
    logger = logging.getLogger("rateman")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    return logger


def main():
    arg_parser = argparse.ArgumentParser(prog="rateman")
    arg_parser.add_argument(
        "-g",
        "--algorithm",
        type=str,
        default="minstrel_ht_kernel_space",
        help="Rate control algorithm to run.",
    )
    arg_parser.add_argument(
        "-o",
        "--options",
        type=str,
        default=None,
        help="Rate control algorithm configuration options",
    )
    arg_parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    arg_parser.add_argument(
        "-A",
        "--ap-file",
        metavar="AP_FILE",
        type=str,
        help="Path to a csv file where each line contains information about an access point "
        + "in the format: NAME,ADDR,RCDPORT.",
    )
    arg_parser.add_argument("-E", "--enable-events", nargs="+", action="extend")
    arg_parser.add_argument(
        "-r",
        "--record-trace",
        action="store_true",
        help="Store incoming events in trace files named after the accesspoints",
    )
    arg_parser.add_argument(
        "--show-state",
        action="store_true",
        help="Connect to APs and output their state. This is useful for testing",
    )
    arg_parser.add_argument(
        "-t", "--time", type=float, default=0.0, help="run for the given number of seconds and exit"
    )
    arg_parser.add_argument(
        "accesspoints",
        metavar="AP",
        nargs="*",
        type=str,
        help="Accesspoint to connecto to. Format: 'NAME:ADDR:RCDPORT'. "
        + "RCDPORT is optional and defaults to 21059.",
    )
    args = arg_parser.parse_args()
    logger = setup_logger(args.verbose)

    aps = rateman.accesspoint.from_strings(args.accesspoints, logger=logger)

    options_str = args.options
    if options_str is not None:
        try:
            options = ast.literal_eval(options_str)
        except ValueError:
            print("Error: Invalid dictionary format provided.")
            exit(1)
    else:
        options = None

    if args.ap_file:
        aps += from_file(args.ap_file, logger=logger)

    if len(aps) == 0:
        print("ERROR: No accesspoints given", file=sys.stderr)
        sys.exit(1)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    rm = rateman.RateMan(loop=loop, logger=logger)

    for ap in aps:
        rm.add_accesspoint(ap)

        if args.record_trace:
            ap.start_recording_rcd_trace(f"{ap.name}_trace.csv")

    print("Initializing rateman...", end="")
    loop.run_until_complete(rm.initialize())
    print("OK")

    if args.enable_events:
        loop.run_until_complete(ap.enable_events(events=args.enable_events))

    if args.show_state:
        show_state(rm)
        loop.run_until_complete(rm.stop())
        loop.close()
        return 0

    for ap in rm.accesspoints:
        for sta in ap.stations():
            print(f"Starting rate control scheme '{args.algorithm}' for {sta}")
            try:
                loop.run_until_complete(sta.start_rate_control(args.algorithm, options))
            except Exception as e:
                tb = traceback.extract_tb(e.__traceback__)[-1]
                logger.error(
                    f"Error starting rc algorithm '{args.algorithm}' for {sta}: "
                    f"{e} (({tb.filename}:{tb.lineno}))"
                )

    print("Running rateman... (Press CTRL+C to stop)")

    try:
        if not args.time:
            loop.run_forever()
        else:
            loop.run_until_complete(asyncio.sleep(args.time))
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        with suppress(KeyboardInterrupt):
            loop.run_until_complete(rm.stop())
        loop.close()
        print("DONE")
