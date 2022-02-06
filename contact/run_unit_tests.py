"""Compare PolyFEM and IPC."""
import pathlib
import argparse
import subprocess
import json
from datetime import datetime

import pandas


def get_time_stamp():
    """Get a formatted time stamp."""
    return datetime.now().strftime("%Y-%b-%d-%H-%M-%S")


current_parents = pathlib.Path(__file__).resolve().parents

# Find the path to PolyFEM
if (len(current_parents) > 2
        and pathlib.Path(current_parents[2] / "polyfem").exists()):
    polyfem_root = current_parents[2] / "polyfem"
else:
    polyfem_root = pathlib.Path(__file__)


def find_bin(root, bin_name):
    """Find a binary file with the name bin_name in a build subdirectory."""
    build_dir = root / "build"
    for sub_dir in "", "release", "debug":
        bin = build_dir / sub_dir / bin_name
        if bin.is_file():
            return bin.resolve()
    return None


def create_parser():
    parser = argparse.ArgumentParser(
        description="Run a 3D unit tests.")
    parser.add_argument(
        "--polyfem-bin", metavar="path/to/PolyFEM_bin",
        type=pathlib.Path, default=find_bin(polyfem_root, "PolyFEM_bin"),
        help="path to PolyFEM binary")
    parser.add_argument(
        "-o", "--output", metavar="path/to/output.csv", type=pathlib.Path,
        dest="output", default=pathlib.Path("polyfem-unit-tests.csv"),
        help="path to output CSV")
    parser.add_argument(
        "--loglevel", default="warning",
        choices=[
            "trace", "debug", "info", "warning", "error", "critical", "off"],
        help="set log level {trace, debug, info, warning, error, critical, off}")
    return parser


def parse_arguments():
    parser = create_parser()
    args = parser.parse_args()
    if args.polyfem_bin is None or not args.polyfem_bin.exists():
        parser.exit(1, "PolyFEM binary not found!\n")
    return args


def append_stem(p, stem_suffix):
    return p.parent / (p.stem + stem_suffix + p.suffix)


def main():
    args = parse_arguments()

    examples_dir = (
        pathlib.Path(__file__).resolve().parent / "examples")

    df = pandas.DataFrame(columns=[
        "Scene", "Success", "Runtime", "Iterations", "Linear Solve Time",
        "BP CCD Time", "NP CCD Time", "Assembly Time"])

    for test in (examples_dir / "3D" / "unit-tests").rglob("*.json"):
        rel = test.relative_to(examples_dir)
        output = "output" / rel.parent / rel.stem
        df_row = {"Scene": str(rel.parent / rel.stem)}

        #######################################################################
        # Run the PolyFEM sim
        print(f"Running {test} in PolyFEM")

        tmp = [str(args.polyfem_bin),
               "-j", str(test),
               "-o", str(output),
               "--log_level", str(args.loglevel),
               "--solver", "Eigen::CholmodSupernodalLLT",
               "--log_file", str(output / "log.txt"),
               "--ngui"]
        try:
            subprocess.run(tmp, check=True)
        except subprocess.CalledProcessError:
            df_row["Success"] = False
        else:
            df_row["Success"] = True

        if df_row["Success"]:
            with open(output / "sim.json") as sim:
                sim_dict = json.load(sim)
                df_row["Runtime"] = sum(
                    [(
                        f["info"]["time_assembly"] +
                        f["info"]["time_line_search"] +
                        f["info"]["time_inverting"] +
                        f["info"]["time_grad"] +
                        f["info"]["time_obj_fun"] +
                        f["info"]["time_constraint_set_update"]
                    ) * f["info"]["iterations"]
                        for f in sim_dict["solver_info"]])

                df_row["Iterations"] = sum(
                    [f["info"]["iterations"] for f in sim_dict["solver_info"]])

                df_row["Linear Solve Time"] = sum(
                    [f["info"]["time_inverting"] * f["info"]["iterations"]
                     for f in sim_dict["solver_info"]])

                df_row["BP CCD Time"] = sum(
                    [f["info"]["time_broad_phase_ccd"]
                     * f["info"]["iterations"]
                     for f in sim_dict["solver_info"]])

                df_row["NP CCD Time"] = sum(
                    [f["info"]["time_ccd"] * f["info"]["iterations"]
                     for f in sim_dict["solver_info"]])

                df_row["Assembly Time"] = sum(
                    [f["info"]["time_assembly"] * f["info"]["iterations"]
                     for f in sim_dict["solver_info"]])

        #######################################################################
        df.loc[df_row["Scene"]] = df_row
        df.to_csv(args.output, index=False)
        print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()
