"""Benchmark linear solvers."""

import pathlib
import argparse
import subprocess
import json
from datetime import datetime

import pandas


def get_time_stamp():
    """Get formated timestamp."""
    return datetime.now().strftime("%Y-%b-%d-%H-%M-%S")


current_parents = pathlib.Path(__file__).resolve().parents

# Find the path to PolyFEM
if (len(current_parents) > 2
        and pathlib.Path(current_parents[2] / "polyfem").exists()):
    polyfem_root = current_parents[2] / "polyfem"
else:
    polyfem_root = pathlib.Path(__file__)


def find_bin(root, bin_name):
    """Find a binary with the name bin_name."""
    build_dir = root / "build"
    for sub_dir in "", "release", "debug":
        bin = build_dir / sub_dir / bin_name
        if bin.is_file():
            return bin.resolve()
    return None


def create_parser():
    parser = argparse.ArgumentParser(
        description="Run a comparison between PolyFEM and IPC.")
    parser.add_argument(
        "--polyfem-bin", metavar=f"path/to/PolyFEM_bin",
        type=pathlib.Path, default=find_bin(polyfem_root, "PolyFEM_bin"),
        help="path to PolyFEM binary")
    parser.add_argument(
        "-i", "--input", metavar="path/to/input", type=pathlib.Path,
        dest="input", default=None, help="path to input txt(s)", nargs="+")
    parser.add_argument(
        "-o", "--output", metavar="path/to/output.csv", type=pathlib.Path,
        dest="output", default=pathlib.Path("solver-benchmark.csv"),
        help="path to output CSV")
    parser.add_argument(
        "-s", "--solvers", dest="solvers", default=[
            # "AMGCL",
            "Eigen::CholmodSupernodalLLT",
            # "Eigen::ConjugateGradient",
            # "Eigen::SimplicialLDLT",
            # "Eigen::SparseLU",
            # "Hypre",
            # "Pardiso",
        ],
        help="list of linear solvers to benchmark", nargs="+")
    parser.add_argument(
        "--loglevel", default="info",
        choices=["trace", "debug", "info", "warn", "error", "critical", "off"],
        help="set log level {trace, debug, info, warn, error, critical, off}")
    parser.add_argument(
        "--polyfem-args", default="", help=f"arguments to PolyFEM_bin")
    return parser


def parse_arguments():
    parser = create_parser()
    args = parser.parse_args()
    if args.input is None:
        args.input = [pathlib.Path(__file__).resolve().parent / "examples"]
    input_scripts = []
    for input_file in args.input:
        if input_file.is_file() and input_file.suffix == ".json":
            input_scripts.append(input_file.resolve())
        elif input_file.is_dir():
            for script_file in input_file.glob('**/*.json'):
                input_scripts.append(script_file.resolve())
    args.input = input_scripts
    return args


def append_stem(p, stem_suffix):
    # return p.with_stem(p.stem + stem_suffix)
    return p.parent / (p.stem + stem_suffix + p.suffix)


def main():
    args = parse_arguments()

    polyfem_examples_dir = pathlib.Path(__file__).resolve().parent / "examples"

    columns = ["Scene", "Solver", "Runtime", "Iterations", "Linear Solve Time",
               "Broad-Phase CCD Time", "Narrow-Phase CCD Time",
               "Assembly Time"]
    df = pandas.DataFrame(columns=columns)

    for script in args.input:
        rel = script.relative_to(polyfem_examples_dir)
        df_row = {"Scene": str(rel.parent / rel.stem)}
        for solver in args.solvers:
            output = pathlib.Path(
                "output") / "solver-benchmark" / solver / rel.parent / rel.stem
            df_row = {}
            df_row["Scene"] = str(rel.parent / rel.stem)
            df_row["Solver"] = solver

            print(f"Running {script} with {solver}")
            subprocess.run([str(args.polyfem_bin),
                            "-j", str(script),
                            "-o", str(output),
                            "--log_level", str(args.loglevel),
                            "--solver", solver,
                            "--max_threads", "32",
                            "--log_file", str(output / "log.txt"),
                            "--ngui"])

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
                    ) * f["info"]["iterations"] for f in sim_dict["solver_info"]])

                df_row["Iterations"] = sum(
                    [f["info"]["iterations"] for f in sim_dict["solver_info"]])

                df_row["Linear Solve Time"] = sum(
                    [f["info"]["time_inverting"] * f["info"]["iterations"]
                     for f in sim_dict["solver_info"]])

                df_row["Broad-Phase CCD Time"] = sum(
                    [f["info"]["time_broad_phase_ccd"] * f["info"]["iterations"]
                     for f in sim_dict["solver_info"]])
                df_row["Narrow-Phase CCD Time"] = sum(
                    [f["info"]["time_ccd"] * f["info"]["iterations"]
                     for f in sim_dict["solver_info"]])

                df_row["Assembly Time"] = sum(
                    [f["info"]["time_assembly"] * f["info"]["iterations"]
                     for f in sim_dict["solver_info"]])

            df.loc[f"{df_row['Scene']} {df_row['Solver']}"] = df_row
            df.to_csv(args.output, index=False)
    print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()
