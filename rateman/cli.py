import argparse
import sys
import asyncio
import rateman

def parse_aps(apstrs):
    aps = []

    for apstr in apstrs:
        fields = apstr.split(":")
        if len(fields) < 2:
            print(f"Inval access point: '{apstr}'", file=sys.stderr)
            continue

        name = fields[0]
        addr = fields[1]

        try:
            rcd_port = int(fields[2])
        except (IndexError, ValueError):
            rcd_port = 21059

        aps.append(rateman.accesspoint.AccessPoint(name, addr, rcd_port))

    return aps

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
        "-A",
        "--ap-file",
        metavar="AP_FILE",
        type=str,
        help="Path to a csv file where each line contains information about an access point "
        + "in the format: NAME,ADDR,RCDPORT.",
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
    aps = parse_aps(args.accesspoints)

    if args.ap_file:
        aps += accesspoint.from_file(args.ap_file)

    if len(aps) == 0:
        print("ERROR: No accesspoints given", file=sys.stderr)
        sys.exit(1)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    rm = rateman.RateMan(loop=loop)

    for ap in aps:
        rm.add_accesspoint(ap)

    loop.run_until_complete(rm.initialize())

    print("Running rateman...")
    # add a simple print callback to see the incoming data
    rm.add_data_callback(lambda ap, line, **kwargs: print(f"{ap.name}> {';'.join(line)}"))

    try:
        loop.run_forever()
    except (OSError, KeyboardInterrupt):
        print("Stopping...")
    finally:
        loop.run_until_complete(rm.stop())
        print("DONE")
