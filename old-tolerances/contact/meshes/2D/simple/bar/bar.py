import sys
import numpy
import pymesh

h = 0.01

n = int(numpy.ceil(1 / h))
if len(sys.argv) > 1:
    n = int(sys.argv[1])

x = numpy.linspace(-0.5, 0.5, n)
y = numpy.array([-h / 2, h / 2])

V = numpy.zeros((x.size * y.size, 3))
for i in range(x.size):
    for j in range(y.size):
        V[i * y.size + j, :2] = [x[i], y[j]]

area = h * (x[1] - x[0]) / 2  # 1/2 * base * height

tri = pymesh.triangle()
tri.points = V
tri.max_area = 2 * area
tri.split_boundary = False
tri.run()

mesh = tri.mesh

mesh = pymesh.subdivide(mesh)

num_faces = mesh.faces.shape[0]

if num_faces > 1e9:
    suffix = f"{num_faces // int(1e9):d}G"
elif num_faces > 1e6:
    suffix = f"{num_faces // int(1e6):d}M"
elif num_faces > 1e3:
    suffix = f"{num_faces // int(1e3):d}K"
else:
    suffix = f"{num_faces:d}"

pymesh.save_mesh(f"bar{suffix}.obj", mesh)
