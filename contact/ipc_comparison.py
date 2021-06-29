import sys
import os
import pathlib
import argparse
import subprocess
import json
from datetime import datetime

import pandas


def get_time_stamp():
    return datetime.now().strftime("%Y-%b-%d-%H-%M-%S")

current_parents = pathlib.Path(__file__).parents

if len(current_parents) > 3 and pathlib.Path(current_parents[2] / "polyfem").exists() and pathlib.Path(current_parents[3] / "collisions" / "ipc").exists():
    polyfem_root = pathlib.Path(__file__).parents[2] / "polyfem"
    ipc_root = pathlib.Path(__file__).parents[3] / "collisions" / "ipc"
else:
    polyfem_root = pathlib.Path(__file__)
    ipc_root = pathlib.Path(__file__)


def find_bin(root, bin_name):
    build_dir = root / "build"
    for sub_dir in "", "release", "debug":
        bin = build_dir / sub_dir / bin_name
        if bin.is_file():
            return bin.resolve()
    return None


def get_remote_storage():
    for remote_name in "google-drive", "nyu-gdrive", None:
        if remote_name is None:
            print("Unable to find remote storage using rclone! "
                  "Videos will not be uploaded")
            return None
        r = subprocess.run(["rclone", "about", f"{remote_name}:"],
                           capture_output=True, text=True)
        print(r.stdout)
        print(r.stderr)
        if (r.stderr.strip() == ""):
            break
    return f"{remote_name}:polyfem/ipc-comparison/"


def create_parser():
    parser = argparse.ArgumentParser(
        description="Run a comparison between PolyFEM and IPC.")
    parser.add_argument(
        "--polyfem-bin", metavar=f"path/to/PolyFEM_bin",
        type=pathlib.Path, default=find_bin(polyfem_root, "PolyFEM_bin"),
        help="path to PolyFEM binary")
    parser.add_argument(
        "--ipc-bin", metavar=f"path/to/IPC_bin",
        type=pathlib.Path, default=find_bin(ipc_root, "IPC_bin"),
        help="path to IPC binary")
    parser.add_argument(
        "-i", "--input", metavar="path/to/input", type=pathlib.Path,
        dest="input", default=None, help="path to input txt(s)", nargs="+")
    parser.add_argument(
        "-o", "--output", metavar="path/to/output.csv", type=pathlib.Path,
        dest="output", default=pathlib.Path("polyfem-vs-ipc.csv"),
        help="path to output CSV")
    parser.add_argument(
        "--no-ipc", action="store_true", default=False,
        help="do not run the IPC simulation")
    parser.add_argument(
        "--no-polyfem", action="store_true", default=False,
        help="do not run the PolyFEM simulation")
    parser.add_argument(
        "--video-fps", default=40, type=int,
        help="FPS of rendered video (ideally 1/h)")
    parser.add_argument(
        "--no-video", action="store_true", default=False,
        help="do not render a video of the sim")
    parser.add_argument(
        "--loglevel", default=3, type=int, choices=range(7),
        help="set log level 0=trace, 1=debug, 2=info, 3=warn, 4=error, 5=critical, 6=off")
    parser.add_argument(
        "--polyfem-args", default="", help=f"arguments to PolyFEM_bin")
    parser.add_argument(
        "--with-viewer", action="store_true", default=False,
        help="run simulation through the viewer")
    return parser


def parse_arguments():
    parser = create_parser()
    args = parser.parse_args()
    if not args.no_ipc and (args.ipc_bin is None or not args.ipc_bin.exists()):
        parser.exit(1, f"IPC binary not found!\n")
    if not args.no_polyfem and (args.polyfem_bin is None or not args.polyfem_bin.exists()):
        parser.exit(1, f"PolyFEM binary not found!\n")
    if args.input is None:
        args.input = [pathlib.Path(__file__).resolve().parent / "ipc-scripts"]
    input_scripts = []
    for input_file in args.input:
        if input_file.is_file() and input_file.suffix == ".txt":
            input_scripts.append(input_file.resolve())
        elif input_file.is_dir():
            for script_file in input_file.glob('**/*.txt'):
                input_scripts.append(script_file.resolve())
    args.input = input_scripts
    return args


def append_stem(p, stem_suffix):
    # return p.with_stem(p.stem + stem_suffix)
    return p.parent / (p.stem + stem_suffix + p.suffix)


def main():
    args = parse_arguments()
    remote_storage = None  # get_remote_storage()

    ipc_scripts_dir = pathlib.Path(__file__).resolve().parent / "ipc-scripts"
    polyfem_examples_dir = (
        pathlib.Path(__file__).resolve().parent / "examples")

    render_bin = args.polyfem_bin.parent / "tools" / "render_simulation"
    if not args.no_video and not render_bin.exists():
        print("Unable to find 'render_simulation' executable, disabling rendering.")
        args.no_video = True

    df = pandas.DataFrame(columns=[
        "Scene", "IPC Video", "PolyFEM Video", "IPC Runtime", "PolyFEM Runtime",
        "IPC Iterations", "PolyFEM Iterations",
        "IPC Linear Solve Time", "PolyFEM Linear Solve Time",
        "IPC CCD Time",  "PolyFEM CCD Time", "PolyFEM BCCD Time", "PolyFEM NCCD Time", "PolyFEM Ass Time"])

    combined_polyfem_profile = pandas.DataFrame()
    combined_polyfem_profile_filename = append_stem(
        args.output, "-polyfem-profile")

    for script in args.input:
        rel = script.relative_to(ipc_scripts_dir)
        output = "output" / rel.parent / rel.stem
        df_row = {"Scene": str(rel.parent / rel.stem)}
        #######################################################################
        # Run the IPC sim
        if not args.no_ipc:
            print(f"Running {script} in IPC")
            subprocess.run([args.ipc_bin, "10" if args.with_viewer else "100",
                            script.resolve(), "-o", output / "ipc",
                            "--logLevel", str(args.loglevel)])

            # Render the IPC sim
            if not args.no_video:
                print("Rendering IPC simulation")
                video_name = f"{script.stem}-{get_time_stamp()}-ipc.mp4"
                subprocess.run([str(render_bin), output / "ipc",
                                "-o", output / video_name,
                                "--loglevel", str(args.loglevel),
                                "--fps", str(args.video_fps)])
                if remote_storage is not None:
                    remote_path = (f"{remote_storage}{rel.parent}")
                    subprocess.run(
                        ["rclone", "copy", output / video_name, remote_path])
                    df_row["IPC Video"] = subprocess.run(
                        ["rclone", "link", f"{remote_path}/{video_name}"],
                        capture_output=True, text=True).stdout.strip()
                    print(f"Uploaded video to {df_row['IPC Video']}")
            else:
                df_row["IPC Video"] = "None"

            # Get running time from info.txt
            if not (output / "ipc" / "info.txt").exists():
                continue
            with open(output / "ipc" / "info.txt") as info:
                lines = info.readlines()
                df_row["IPC Runtime"] = float(lines[5].strip().split()[0])
                print("IPC finished (total_runtime={:g}s)".format(
                    df_row["IPC Runtime"]))
                df_row["IPC Iterations"] = int(lines[1].strip().split()[1])
                lin_solve_time = sum([
                    float(lines[i].strip().split()[0]) for i in (9, 10, 11)])
                # df_row["IPC Linear Solve Time"] = (
                #     f"{lin_solve_time / df_row['IPC Runtime'] * 100:g}%")
                df_row["IPC Linear Solve Time"] = lin_solve_time
                ccd_time = float(lines[20].strip().split()[0])
                # df_row["IPC CCD Time"] = (
                #     f"{ccd_time / df_row['IPC Runtime'] * 100:g}%")
                df_row["IPC CCD Time"] = ccd_time

        #######################################################################
        # Run the corresponding PolyFEM body sim
        if not args.no_polyfem:
            polyfem_script = polyfem_examples_dir / rel.with_suffix(".json")
            print(f"Running {polyfem_script} in PolyFEM")
            tmp = [str(args.polyfem_bin),
                   "-j", str(polyfem_script),
                   # "-o", str(output),
                   "--log_level", str(args.loglevel),
                   "--solver", "Eigen::CholmodSupernodalLLT",
                   "--lump_mass_mat",
                   "--output", str(output / "sim.json")]
            print(" ".join(tmp))
            tmp += ([] if args.with_viewer else ["--cmd"]) + \
                args.polyfem_args.split()
            subprocess.run(tmp)

            # Render the PolyFEM sim
            if not args.no_video:
                print("Rendering PolyFEM simulation")
                video_name = f"{script.stem}-{get_time_stamp()}-polyfem.mp4"
                subprocess.run([str(render_bin), output / "sim.json",
                                "-o", output / video_name,
                                "--loglevel", str(args.loglevel),
                                "--fps", str(args.video_fps)])
                if remote_storage is not None:
                    remote_path = (f"{remote_storage}{rel.parent}")
                    subprocess.run(
                        ["rclone", "copy", output / video_name, remote_path])
                    df_row["PolyFEM Video"] = subprocess.run(
                        ["rclone", "link", f"{remote_path}/{video_name}"],
                        capture_output=True, text=True).stdout.strip()
                    print(f"Uploaded video to {df_row['PolyFEM Video']}")
            else:
                df_row["PolyFEM Video"] = "None"

            with open(output / "sim.json") as sim:
                sim_dict = json.load(sim)
                df_row["PolyFEM Runtime"] = sum(
                    [(
                        f["info"]["time_assembly"] +
                        f["info"]["time_linesearch"] +
                        f["info"]["time_inverting"] +
                        f["info"]["time_grad"] +
                        f["info"]["time_obj_fun"] +
                        f["info"]["time_constrain_set_update"]
                    ) * f["info"]["iterations"] for f in sim_dict["solver_info"]])
                # sum([t["info"] for sim_dict["solver_info"]["step_timings"])
                df_row["PolyFEM Iterations"] = sum(
                    [f["info"]["iterations"] for f in sim_dict["solver_info"]])

                df_row["PolyFEM Linear Solve Time"] = sum(
                    [f["info"]["time_inverting"] * f["info"]["iterations"] for f in sim_dict["solver_info"]])

                df_row["PolyFEM CCD Time"] = sum(
                    [(f["info"]["time_ccd"] + f["info"]["time_broad_phase_ccd"]) * f["info"]["iterations"] for f in sim_dict["solver_info"]])

                df_row["PolyFEM BCCD Time"] = sum(
                    [f["info"]["time_broad_phase_ccd"] * f["info"]["iterations"] for f in sim_dict["solver_info"]])
                df_row["PolyFEM NCCD Time"] = sum(
                    [f["info"]["time_ccd"] * f["info"]["iterations"] for f in sim_dict["solver_info"]])

                df_row["PolyFEM Ass Time"] = sum(
                    [f["info"]["time_assembly"] * f["info"]["iterations"] for f in sim_dict["solver_info"]])

        #######################################################################
        df.loc[df_row["Scene"]] = df_row
        df.to_csv(args.output, index=False)
    print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()
