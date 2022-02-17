"""Compare PolyFEM and IPC."""
import pathlib
import argparse
import json

import numpy
import plotly.graph_objects as go

current_parents = pathlib.Path(__file__).resolve().parents


def sum_times(sim_dict, key, is_avg=True):
    total = 0
    for step in sim_dict["solver_info"]:
        info = step["info"]
        total += info[key] * (info["iterations"] if is_avg else 1)
    return total


def plot_sim_json(sim_json, output):
    with open(sim_json) as sim:
        sim_dict = json.load(sim)

    # print(sim_dict["solver_info"][0]["info"].keys())

    total_time = sum_times(sim_dict, "total_time", is_avg=False)

    total_iterations = sum_times(sim_dict, "iterations", False)

    line_search_iterations = (
        sum_times(sim_dict, "line_search_iterations", False) / total_iterations)

    timings = {
        "Compute + Assemble Hessian": sum_times(sim_dict, "time_assembly"),
        "BP CCD": sum_times(sim_dict, "time_broad_phase_ccd"),
        "NP CCD": sum_times(sim_dict, "time_ccd"),
        f"Linear Solve<br>({sim_dict['solver_type']})": sum_times(sim_dict, "time_inverting"),
        "Compute Gradient": sum_times(sim_dict, "time_grad"),
        "Compute Objective": sum_times(sim_dict, "time_obj_fun"),
        "Constraint Set Update": sum_times(sim_dict, "time_constraint_set_update"),
        f"Line-Search Constraint Set Update<br>(n/iter={line_search_iterations:.1f})": sum_times(sim_dict, "time_line_search_constraint_set_update"),
        "Inversion Checking": sum_times(sim_dict, "time_checking_for_nan_inf"),
        "Classical Line-Search": sum_times(sim_dict, "time_classical_line_search"),
    }
    timings["Misc."] = total_time - sum(timings.values())

    print(f"extra_time={sim_dict['time_solving'] - total_time}s")

    fig = go.Figure(go.Pie(
        labels=list(timings.keys()),
        values=list(timings.values()),
        texttemplate='%{label}<br>%{percent}<br>%{value:.2f}s',
    ))

    scale = 1.25
    fig.update_layout(dict(
        title="{} (|V|={}) [{:.2f}s; {:d} iters; {} threads; {} MB]".format(
            sim_json.parent.name.title(),
            sim_dict["num_vertices"],
            total_time,
            total_iterations,
            sim_dict["num_threads"],
            sim_dict["peak_memory"]
        ),
        width=700 * scale, height=500 * scale,
        showlegend=False,
        # font=dict(
        #     size=9
        # )
    ))

    fig.write_image(output)
    print(f"Results written to {output}")


def create_parser():
    parser = argparse.ArgumentParser(
        description="Plot sim output JSON.")
    parser.add_argument(
        "-i", "--input", dest="input", metavar="path/to/sim.json",
        type=pathlib.Path)
    parser.add_argument(
        "-o", "--output", metavar="path/to/plot.png", type=pathlib.Path,
        dest="output", default=pathlib.Path("plot.png"),
        help="path to output plot")
    return parser


def parse_arguments():
    parser = create_parser()
    return parser.parse_args()


def main():
    args = parse_arguments()
    plot_sim_json(args.input, args.output)


if __name__ == "__main__":
    main()
