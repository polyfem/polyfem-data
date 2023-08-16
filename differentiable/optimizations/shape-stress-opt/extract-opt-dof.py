import meshio, json, igl
import numpy as np

mesh_path = "bridge-uniform.msh"
json_path = "state.json"

m = meshio.read(mesh_path)
v = m.points[:,:2]
f = m.cells[0].data

with open(json_path,'r') as infile:
    data = json.load(infile)
    surface_selection = data["geometry"][0]["surface_selection"]

vmin = np.amin(v,axis=0)
vmax = np.amax(v,axis=0)
v_norm = (v - vmin) / (vmax - vmin)

boundary_edges = igl.boundary_facets(f)

surface_ids = np.zeros((len(v)), dtype=int)
for selection in reversed(surface_selection):
    for edge in boundary_edges:
        if "relative" in selection and selection["relative"]:
            p = (v_norm[edge[0],:] + v_norm[edge[1],:]) / 2
        else:
            p = (v[edge[0],:] + v[edge[1],:]) / 2
        # if p[0] > 0.00755 and p[0] < 0.01 and abs(p[1] - 0.02) < 0.001:
        #     breakpoint()
        box = selection["box"]
        if np.amin(p - box[0]) >= 0 and np.amin(box[1] - p) >= 0:
            surface_ids[edge[0]] = selection["id"]
            surface_ids[edge[1]] = selection["id"]

num = 0
with open('opt-dof.txt','w') as outfile:
    for i in range(len(surface_ids)):
        if surface_ids[i] <= 1:
            for d in range(2):
                outfile.write(str(i * 2 + d) + "\n")
                num += 1

print(num)