# -*- coding: UTF8 -*-
# Copyright SupraCoNeX
#     https://www.supraconex.org

import signal
import sys



__all__ = ["timedInput", "get_path_arg", "get_duration_arg"]


def _convert_timestamps_to_datetime(df):
    """Convert timestamps to datetime objects."""
    pass


def timedInput(prompt="", timeout=1, timeoutmsg=None):
    def timeout_error(*_):
        raise TimeoutError

    signal.signal(signal.SIGALRM, timeout_error)
    signal.alarm(timeout)
    try:
        answer = input(prompt)
        signal.alarm(0)
        return answer
    except TimeoutError:
        if timeoutmsg:
            print(timeoutmsg)
        signal.signal(signal.SIGALRM, signal.SIG_IGN)
        return None


def get_path_arg(parser):
    """
    Parses path argument provided in the exec command
    """

    args = parser.parse_args()

    if args.p:
        try:
            fileHandle = open(args.p)
            fileHandle.close()
        except IOError as errorDef:
            print(errorDef)
        else:
            path = args.p
            
            return path
    else:
        print(
            "Please specify a path, with -p, to the data file for minstrel-py to run!"
        )
        sys.exit(1)

    
def get_duration_arg(parser):
    
    """
    Parses duration argument provided in the exec command
    """
    
    args = parser.parse_args()
    
    if args.t:
        if args.t > 0:
            duration = args.t
            
            return duration
        else:
            print("Oops! Time duration cannot be negative.")
    else:
        print("Argument for duration not found.")        
            
            
    