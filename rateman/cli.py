import argparse
import sys
import asyncio
import logging
import rateman


def dump_stas(ap, radio, interface):
    for sta in [sta for sta in ap.stations(radio) if sta.interface == interface]:
        print(f"        + {sta.mac_addr}"
              f" [rc={sta.rc_mode} tpc={sta.tpc_mode} rc_alg={sta.rate_control[0]}]"
        )


def dump_interfaces(ap, radio):
    print("      interfaces:")
    for iface in ap.interfaces(radio):
        print(f"      - {iface}")
        dump_stas(ap, radio, iface)


def dump_radios(ap):
    for radio in ap.radios:
        print("""  - %(radio)s
      driver: %(drv)s
      events: %(ev)s
      features: %(features)s""" % dict(
                radio=radio,
                drv=ap.get_radio_driver(radio),
                ev=",".join(ap.enabled_events(radio)),
                features=", ".join([
                    f"{f}={'on' if s else 'off'}"
                    for f, s in ap._radios[radio]["features"].items()
                ])
            )
        )
        dump_interfaces(ap, radio)


def show_state(rm):
    for ap in rm.accesspoints:
        print("""
%(name)s:
  connected: %(conn)s
  radios:""" % dict(name=ap.name, conn=("yes" if ap.connected else "no")))
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
        help="Rate control algorithm to run."
    )
    arg_parser.add_argument(
        "-o", "--options",
        type=dict,
        default=None,
        help="Rate control algorithm configuration options"
    )
    arg_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="debug logging"
    )
    arg_parser.add_argument(
        "-A",
        "--ap-file",
        metavar="AP_FILE",
        type=str,
        help="Path to a csv file where each line contains information about an access point "
        + "in the format: NAME,ADDR,RCDPORT.",
    )
    arg_parser.add_argument(
        "-e", "--events", action="store_true", help="Print the events rateman receives"
    )
    arg_parser.add_argument(
        "--show-state", action="store_true",
        help="Connect to APs and output their state. This is useful for testing"
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

    if args.ap_file:
        aps += accesspoint.from_file(args.ap_file, logger=logger)

    if len(aps) == 0:
        print("ERROR: No accesspoints given", file=sys.stderr)
        sys.exit(1)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    rm = rateman.RateMan(loop=loop, logger=logger)

    for ap in aps:
        rm.add_accesspoint(ap)

    print("Initializing rateman...", end="")
    loop.run_until_complete(rm.initialize())
    print("OK")

    if args.show_state:
        show_state(rm)
        loop.run_until_complete(rm.stop())
        loop.close()
        return 0

    for ap in rm.accesspoints:
        for sta in ap.stations():
            print(f"Starting rate control scheme '{args.algorithm}' for {sta}")
            loop.run_until_complete(sta.start_rate_control(args.algorithm, args.options))

    print("Running rateman... (Press CTRL+C to stop)")

    if args.events:
        # add a simple print callback to see the incoming data
        rm.add_data_callback(lambda ap, line, **kwargs: print(f"{ap.name}> {';'.join(line)}"))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        loop.run_until_complete(rm.stop())
        loop.close()
        print("DONE")
