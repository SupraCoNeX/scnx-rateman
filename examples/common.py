import argparse

from rateman.accesspoint import AccessPoint


def parse_aps(apstrs):
    aps = []

    for apstr in apstrs:
        fields = apstr.split(":")
        if len(fields) < 2:
            print(f"Invalid access point: '{apstr}'", file=sys.stderr)
            continue

        ap_id = fields[0]
        addr = fields[1]

        try:
            rcd_port = int(fields[2])
        except (IndexError, ValueError):
            rcd_port = 21059

        aps.append(AccessPoint(ap_id, addr, rcd_port))

    return aps


def setup_argparser():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "algorithm",
        type=str,
        choices=["minstrel_ht_kernel_space", "minstrel_ht_user_space"],
        default="minstrel_ht_kernel_space",
        help="Rate control algorithm to run.",
    )
    arg_parser.add_argument(
        "-A",
        "--ap-file",
        metavar="AP_FILE",
        type=str,
        help="Path to a csv file where each line contains information about an access point "
        + "in the format: ID,ADDR,RCDPORT.",
    )
    arg_parser.add_argument(
        "accesspoints",
        metavar="AP",
        nargs="*",
        type=str,
        help="Accesspoint to connecto to. Format: 'ID:ADDR:RCDPORT'. "
        + "RCDPORT is optional and defaults to 21059.",
    )

    return arg_parser
