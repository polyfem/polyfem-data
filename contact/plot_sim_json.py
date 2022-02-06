"""Compare PolyFEM and IPC."""
import pathlib
import argparse
import json
import numpy
import plotly.graph_objects as go

current_parents = pathlib.Path(__file__).resolve().parents

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

    with open(args.input) as sim:
        sim_dict = json.load(sim)

    def sum_times(key, is_avg=True):
        total = 0
        for step in sim_dict["solver_info"]:
            info = step["info"]
            total += info[key] * (info["iterations"] if is_avg else 1) 
        return total

    # print(sim_dict["solver_info"][0]["info"].keys())
    
    total_time = sum_times("total_time", is_avg=False)

    line_search_iterations = sum_times("line_search_iterations", False) / sum_times("iterations", False)

    timings = {
        "Compute + Assemble Hessian": sum_times("time_assembly"),
        "BP CCD": sum_times("time_broad_phase_ccd"),
        "NP CCD": sum_times("time_ccd"),
        f"Linear Solve<br>({sim_dict['solver_type']})": sum_times("time_inverting"),
        "Compute Gradient": sum_times("time_grad"),
        "Compute Objective": sum_times("time_obj_fun"),
        "Constraint Set Update": sum_times("time_constraint_set_update"),
        f"Line-Search Constraint Set Update<br>(n/iter={line_search_iterations:.1f})": sum_times("time_line_search_constraint_set_update"),
        "Inversion Checking": sum_times("time_checking_for_nan_inf"),
        "Classical Line-Search": sum_times("time_classical_line_search"),
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
        title="{} (|V|={}) [{:.2f}s; {} threads; {} MB]".format(
            args.input.parent.name.title(), 
            sim_dict["num_vertices"],
            total_time, 
            sim_dict["num_threads"],
            sim_dict["peak_memory"]
        ),
        width=700 * scale, height=500 * scale,
        showlegend=False, 
        # font=dict(
        #     size=9
        # )
    ))

    fig.write_image(args.output)
    print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()
