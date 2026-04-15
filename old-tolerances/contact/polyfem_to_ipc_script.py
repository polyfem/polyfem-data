import sys
import os
import pathlib
import json
import textwrap
import argparse

import numpy
from scipy.spatial.transform import Rotation


def polyfem_to_ipc_script(polyfem_json, input_path, output_path):
    if polyfem_json["tensor_formulation"] != "NeoHookean":
        raise Exception("IPC only supports NeoHookean!")
    if not polyfem_json["problem_params"]["is_time_dependent"]:
        raise Exception("IPC only supports time dependent simulation!")
    if polyfem_json.get("normalize_mesh", True):
        raise Exception("Normalize mesh not supported!")

    max_time = polyfem_json["tend"]
    if "dt" in polyfem_json:
        timestep = polyfem_json["dt"]
    else:
        timestep = max_time / polyfem_json["time_steps"]

    dhat = polyfem_json.get("dhat", 1e-3)

    meshes = polyfem_json["meshes"]
    obstacles = polyfem_json.get("obstacles", [])

    dirichlet_bc = {}
    for bc in polyfem_json["problem_params"].get("dirichlet_boundary", []):
        dirichlet_bc[bc["id"]] = bc

    materials = {}
    for mat in polyfem_json["body_params"]:
        materials[mat["id"]] = mat

    shapes = []
    disabled_shapes = []
    for i, mesh in enumerate(meshes + obstacles):
        mesh_path = pathlib.Path(mesh["mesh"])
        if not mesh_path.is_absolute():
            mesh_path = input_path.resolve().parent / mesh_path
            mesh_path = os.path.relpath(
                mesh_path.resolve(), output_path.resolve().parent)

        position = mesh.get("position", [0, 0, 0])

        if "dimensions" in mesh:
            raise NotImplementedError("Dimensions not implemented!")
        else:
            scale = mesh.get("scale", [1, 1, 1])
            if isinstance(scale, int) or isinstance(scale, float):
                scale = [scale] * 3

        if "rotation" in mesh:
            rotation_mode = mesh.get("rotation_mode", "xyz")
            rotation = (
                Rotation.from_euler(
                    rotation_mode, mesh["rotation"], degrees=True)
                .as_euler("zyx", degrees=True))
        else:
            rotation = [0, 0, 0]

        bc_id = mesh.get("boundary_id", 0)
        is_static = False
        if bc_id in dirichlet_bc:
            try:
                is_static = sum(dirichlet_bc[bc_id]["value"]) == 0
            except:
                is_static = False
            # if not is_static:
            #     raise NotImplementedError(
            #         "Non-static DBC are not implemented!")
        elif i >= len(meshes):
            is_static = True

        # linear_velocity = mesh.get("linear_velocity", [0, 0, 0])
        # angular_velocity = mesh.get("angular_velocity", [0, 0, 0])
        # force = mesh.get("force", [0, 0, 0])
        # if "force" in mesh:
        #     nbc = ("  NBC 0 0 0  1 1 1  {:g} {:g} {:g}".format(*mesh["force"]))
        # else:
        nbc = ""
        # if "torque" in mesh:
        #     print("External torque is not supported in IPC! Dropping it!")

        velocity_str = ""
        if is_static:
            velocity_str = "linearVelocity 0 0 0"
        # elif is_kinematic:
        #     velocity_str = (
        #         "linearVelocity {:g} {:g} {:g}  angularVelocity {:g} {:g} {:g}".format(
        #             *linear_velocity, *angular_velocity))
        # else:
        #     velocity_str = (
        #         "initVel {:g} {:g} {:g}  {:g} {:g} {:g}".format(
        #             *linear_velocity, *angular_velocity))

        mat = materials.get(mesh.get("body_id", 0),
                            dict(rho=8050, nu=0.3, E=2e11))
        rho = mat["rho"]
        E = mat["E"]
        nu = mat["nu"]

        shape_line = "{}  {:.16g} {:.16g} {:.16g}  {:.16g} {:.16g} {:.16g}  {:.16g} {:.16g} {:.16g} material {:g} {:g} {:g}  {}{}".format(
            mesh_path, *position, *rotation, *scale, rho, E, nu, velocity_str, nbc)
        if mesh.get("enabled", True):
            shapes.append(shape_line)
        else:
            disabled_shapes.append(f"# {shape_line}")

    mu = polyfem_json.get("mu", 0)
    epsv = polyfem_json.get("epsv", 1e-3)
    friction_iterations = polyfem_json.get("friction_iterations", 1)

    gravity = ""
    if sum(polyfem_json["problem_params"].get("rhs", [0, 0, 0])) == 0:
        gravity = "turnOffGravity"

    assert(not polyfem_json.get("solver_params", {}).get("useGradNorm", False))
    velocity_conv_tol = polyfem_json.get(
        "solver_params", {}).get("gradNorm", 1e-5)

    return textwrap.dedent(f"""\
        energy NH
        warmStart 0
        time {max_time:g} {timestep:g}
        {gravity}

        CCDMethod TightInclusion

        shapes input {len(shapes):d}
        {{}}
        {{}}

        selfCollisionOn
        selfFric {mu:g}

        constraintSolver interiorPoint
        dHat {dhat:g}
        epsv {epsv:g}
        useAbsParameters
        fricIterAmt {friction_iterations:d}
        tol 1
        {velocity_conv_tol}
        """).format("\n".join(shapes), "\n".join(disabled_shapes))


def main():
    parser = argparse.ArgumentParser(
        description="Convert a PolyFEM JSON file to an IPC script")
    parser.add_argument(
        "-i", "--input", metavar="path/to/input", type=pathlib.Path,
        dest="input", required=True, help="path to input json(s)", nargs="+")
    args = parser.parse_args()

    ipc_scripts_path = pathlib.Path(__file__).resolve().parent / "ipc-scripts"
    polyfem_examples_path = (
        pathlib.Path(__file__).resolve().parent / "examples")

    for input in args.input:
        assert(input.exists())

        try:
            output = input.with_suffix(".txt").resolve()
            output = (
                ipc_scripts_path / output.relative_to(polyfem_examples_path))
            output.parent.mkdir(parents=True, exist_ok=True)
        except:
            output = input.with_suffix(".txt")

        print(f"Converting {input} → {output}")

        with open(input) as input_file:
            polyfem_json = json.load(input_file)

        ipc_script = polyfem_to_ipc_script(polyfem_json, input, output)

        with open(output, 'w') as ipc_script_file:
            ipc_script_file.write(ipc_script)


if __name__ == "__main__":
    main()
