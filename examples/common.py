import argparse
import sys
import logging

from rateman.accesspoint import AccessPoint


def parse_arguments():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "-g", "--rc-algorithm",
        metavar="RC_ALG",
        type=str,
        choices=["minstrel_ht_kernel_space", "py_minstrel_ht", "manual_mrr_setter"],
        default="minstrel_ht_kernel_space",
        help="Rate control algorithm to run.",
    )

    arg_parser.add_argument(
        "-o", "--rc-options",
        metavar="RC_OPTS",
        type=dict,
        default={},
        help="Rate control options",
    )

    arg_parser.add_argument(
        "-A", "--ap-file",
        metavar="AP_FILE",
        type=str,
        help="Path to a csv file where each line contains information about an access point "
        + "in the format: NAME,ADDR,RCDPORT",
    )
    arg_parser.add_argument(
        "accesspoints",
        metavar="AP",
        nargs="*",
        type=str,
        help="Accesspoint to connect to. Format: 'ID:ADDR:RCDPORT'. "
        + "RCDPORT is optional and defaults to 21059.",
    )

    return arg_parser.parse_args()


def setup_logger(name, log_lvl=logging.DEBUG):
    logging.basicConfig(format="[LOG] %(asctime)s - %(name)s - %(message)s")
    logger = logging.getLogger(name)
    logger.setLevel(log_lvl)

    return logger
