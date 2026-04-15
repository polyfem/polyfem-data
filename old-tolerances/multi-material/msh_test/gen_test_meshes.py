import numpy
import meshio


def gmsh_dim_tags(points, cells, tags):
    dim_tags = numpy.tile([3, 1], [points.shape[0], 1])
    for i, cell in enumerate(cells):
        for vi in cell:
            dim_tags[vi, 1] = tags[i]
    return dim_tags


def gmsh_cell_tags(tags):
    cell_tags = [[tags[0]]]
    for tag in tags[1:]:
        if tag == cell_tags[-1][-1]:
            cell_tags[-1].append(tag)
        else:
            cell_tags.append([tag])
    return cell_tags


def split_cells_by_tags(tags, cells):
    assert(len(tags) == len(cells))
    split_cells = [[cells[0]]]
    for i, tag in enumerate(tags[1:]):
        if tag == tags[i]:
            split_cells[-1].append(cells[i + 1])
        else:
            split_cells.append([cells[i + 1]])
    return split_cells


points = numpy.array([
    [-1.5, 0, 0],
    [-0.5, 0, 0.5],
    [0.5, 0, 0.5],
    [1.5, 0, 0],
    [-0.5, 1, 0],
    [0.5, 1, 0],
    [-0.5, 0, -0.5],
    [0.5, 0, -0.5],
])

tets = numpy.array([
    [1, 0, 4, 6],
    [6, 1, 7, 4],
    [7, 1, 5, 4],
    [1, 2, 7, 5],
    [3, 2, 5, 7],
])

tags = numpy.array([1, 2, 2, 2, 3])

dim_tags = gmsh_dim_tags(points, tets, tags)
cell_tags = gmsh_cell_tags(tags)

mesh = meshio.Mesh(
    points,
    [("tetra", cells) for cells in split_cells_by_tags(tags, tets)],
    point_data={"gmsh:dim_tags": dim_tags},
    cell_data={"gmsh:physical": cell_tags, "gmsh:geometrical": cell_tags}
)

meshio.write("22_ascii.msh", mesh, binary=False, file_format="gmsh22")
meshio.write("22_binary.msh", mesh, binary=True, file_format="gmsh22")
meshio.write("41_ascii.msh", mesh, binary=False, file_format="gmsh")
meshio.write("41_binary.msh", mesh, binary=True, file_format="gmsh")
