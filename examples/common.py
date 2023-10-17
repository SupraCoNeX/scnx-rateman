import argparse
import sys
import logging

from rateman.accesspoint import AccessPoint


def parse_arguments():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-v", "--verbose", action="store_true")
    arg_parser.add_argument(
        "-A",
        "--ap-file",
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


def setup_logger(name, verbose=False):
    logging.basicConfig(format="[LOG] %(asctime)s - %(name)s - %(message)s")
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    return logger
