import sys
import numpy
import pymesh

n = 128
if len(sys.argv) > 1:
    n = int(sys.argv[1])
r = 0.5

angles = numpy.linspace(0, 2 * numpy.pi, n, endpoint=False).reshape(-1, 1)
x = r * numpy.cos(angles)
y = r * numpy.sin(angles)
z = numpy.zeros(x.shape)

V = numpy.hstack([x, y, z])

edge_len = numpy.linalg.norm(V[1] - V[0])
eq_area = numpy.sqrt(3) / 4 * edge_len**2

tri = pymesh.triangle()
tri.points = V
tri.max_area = 2 * eq_area
tri.split_boundary = False
tri.run()

num_faces = tri.mesh.faces.shape[0]

if num_faces > 1e9:
    suffix = f"{num_faces // int(1e9):d}G"
elif num_faces > 1e6:
    suffix = f"{num_faces // int(1e6):d}M"
elif num_faces > 1e3:
    suffix = f"{num_faces // int(1e3):d}K"
else:
    suffix = f"{num_faces:d}"

pymesh.save_mesh(f"circle{suffix}.obj", tri.mesh)
