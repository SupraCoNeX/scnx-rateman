import argparse
import sys

from rateman.accesspoint import AccessPoint


def setup_argparser():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "-rc-alg",
        metavar="RC_ALG",
        type=str,
        choices=["minstrel_ht_kernel_space", "py_minstrel_ht", "manual_mrr_setter"],
        default="minstrel_ht_kernel_space",
        help="Rate control algorithm to run.",
    )

    arg_parser.add_argument(
        "-rc-opts",
        metavar="RC_OPTS",
        default="{}",
        help="Rate control options",
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
        help="Accesspoint to connect to. Format: 'ID:ADDR:RCDPORT'. "
        + "RCDPORT is optional and defaults to 21059.",
    )

    return arg_parser
