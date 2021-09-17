import argparse
from pathlib import Path
from check_data_demo import create_logger, check_data

if __name__ == "__main__":
    # Create Parser for directory
    parser = argparse.ArgumentParser(
        description="Run a script on all measurements (directories with `Meas_` prefix) in given directory and log all errors in the given logfile (default: error.log). Example: `python3 check_data_batch_demo.py ~/scnx-rateman/demo/collected_data`"
    )
    parser.add_argument(
        "directory", type=str, help="Path of directory where measurements are stored."
    )
    args = parser.parse_args()

    # Read directory from parser
    pstr = args.directory

    # Create a logger for logging exceptions and errors
    logger = create_logger()

    # Check if given path is a directory
    p = Path(pstr)
    if p.is_dir():
        num_files = len(list(p.glob("Meas_*/data/data_Mesh_*.csv")))
        file_counter = 0
        for meas_dir in p.glob("Meas_*"):
            data_dir = meas_dir / "data"
            if data_dir.is_dir():
                for meas_file in data_dir.glob("data_Mesh_*.csv"):
                    file_counter += 1
                    print(f"{file_counter}/{num_files}")
                    check_data(str(meas_file), logger)
