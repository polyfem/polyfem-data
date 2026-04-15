"""Compare PolyFEM and IPC."""
import pathlib
import argparse
import subprocess
import json
from datetime import datetime

import pandas

from plot_sim_json import plot_sim_json, sum_times


def get_time_stamp():
    """Get a formatted time stamp."""
    return datetime.now().strftime("%Y-%b-%d-%H-%M-%S")


current_parents = pathlib.Path(__file__).resolve().parents

# Find the path to PolyFEM
if (len(current_parents) > 2
        and pathlib.Path(current_parents[2] / "polyfem").exists()):
    polyfem_root = current_parents[2] / "polyfem"
else:
    polyfem_root = pathlib.Path(__file__).parent


def find_bin(root, bin_name, debug=False):
    """Find a binary file with the name bin_name in a build subdirectory."""
    if pathlib.Path(bin_name).exists():
        return pathlib.Path(bin_name).resolve()
    build_dir = root / "build"
    for sub_dir in ["debug" if debug else "release", ""]:
        bin = build_dir / sub_dir / bin_name
        if bin.is_file():
            return bin.resolve()
    return None


def create_parser():
    parser = argparse.ArgumentParser(
        description="Run a 3D unit tests.")
    parser.add_argument(
        "--polyfem-bin", metavar="path/to/PolyFEM_bin",
        type=pathlib.Path, default=None, help="path to PolyFEM binary")
    parser.add_argument(
        "-o", "--output", metavar="path/to/output.csv", type=pathlib.Path,
        dest="output", default=pathlib.Path("polyfem-unit-tests.csv"),
        help="path to output CSV")
    parser.add_argument(
        "--loglevel", default="warning",
        choices=[
            "trace", "debug", "info", "warning", "error", "critical", "off"],
        help="set log level {trace, debug, info, warning, error, critical, off}")
    parser.add_argument(
        "--debug", default=False, action="store_true", help="run with debugger")
    return parser


def parse_arguments():
    parser = create_parser()
    args = parser.parse_args()
    if args.polyfem_bin is None:
        args.polyfem_bin = find_bin(polyfem_root, "PolyFEM_bin", args.debug)
    if args.polyfem_bin is None or not args.polyfem_bin.exists():
        parser.exit(1, "PolyFEM binary not found!\n")
    else:
        args.polyfem_bin = args.polyfem_bin.resolve()
    return args


def append_stem(p, stem_suffix):
    return p.parent / (p.stem + stem_suffix + p.suffix)


def main():
    args = parse_arguments()

    examples_dir = (
        pathlib.Path(__file__).resolve().parent / "examples")

    df = pandas.DataFrame(
        columns=["Scene", "Success", "Runtime", "Iterations"])

    unit_tests = list((examples_dir / "3D" / "unit-tests").rglob("*.json"))
    unit_tests += list(
        (examples_dir / "3D" / "friction").rglob("high-school*.json"))
    unit_tests.append(
        examples_dir / "3D" / "large-ratios" / "large-mass-ratio.json")

    for test in unit_tests:
        rel = test.relative_to(examples_dir)
        output = args.output.parent / "output" / rel.parent / rel.stem
        df_row = {"Scene": str(rel.parent / rel.stem)}

        #######################################################################
        # Run the PolyFEM sim
        print(f"Running {test} in PolyFEM")

        tmp = [str(args.polyfem_bin),
               "-j", str(test),
               "-o", str(output),
               "--log_level", str(args.loglevel),
               "--log_file", str(output / "log.txt"),
               "--bp", "STQ",
               "--ngui"]
        if args.debug:
            tmp = "lldb --".split() + tmp
        try:
            subprocess.run(tmp, check=True)
        except subprocess.CalledProcessError:
            df_row["Success"] = False
        else:
            df_row["Success"] = True

        if df_row["Success"]:
            with open(output / "sim.json") as sim:
                sim_dict = json.load(sim)
            df_row["Runtime"] = sum_times(sim_dict, "total_time", is_avg=False)
            df_row["Iterations"] = sum_times(
                sim_dict, "iterations", is_avg=False)
            plot_sim_json(output / "sim.json", output / "sim.png")

        #######################################################################
        df.loc[df_row["Scene"]] = df_row
        df.to_csv(args.output, index=False)
        print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()
