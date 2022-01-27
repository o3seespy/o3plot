import numpy as np
import pyvista as pv
# from pyvista import set_plot_theme
# set_plot_theme('document')


def plot_regular_3dgrid(xs, ys, zs, active=None):
    if active is None:
        active = np.ones((len(xs)-1, len(ys)-1, len(zs)-1))
    xn = (xs[:, np.newaxis, np.newaxis] * np.ones((len(xs), len(ys), len(zs)))).flatten()
    yn = (ys[np.newaxis, :, np.newaxis] * np.ones((len(xs), len(ys), len(zs)))).flatten()
    zn = (zs[np.newaxis, np.newaxis, :] * np.ones((len(xs), len(ys), len(zs)))).flatten()
    tags = np.arange(len(xn))
    ts = tags.reshape((len(xs), len(ys), len(zs)))
    all_ele_node_tags = []
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            for k in range(len(zs) - 1):
                if not active[i][j][k]:
                    continue
                ele_node_tags = [ts[i][j][k], ts[i + 1][j][k], ts[i + 1][j + 1][k], ts[i][j + 1][k],
                                 ts[i][j][k + 1], ts[i + 1][j][k + 1], ts[i + 1][j + 1][k + 1], ts[i][j + 1][k + 1],
                                 ]
                all_ele_node_tags.append(ele_node_tags)
    plot_eles3d(all_ele_node_tags, xn, yn, zn)


def plot_eles3d(all_ele_node_tags, xn, yn, zn):
    all_ele_verts = []
    for ele_node_tags in all_ele_node_tags:
        ele_verts = []
        for tag in ele_node_tags:
            ele_verts.append([xn[tag], yn[tag], zn[tag]])
        ele_verts = np.array(ele_verts)
        all_ele_verts.append(ele_verts)

    points = np.array(all_ele_verts).reshape((-1, 3))
    cells_hex = np.arange(len(points)).reshape((-1, 8))
    grid = pv.UnstructuredGrid({pv._vtk.VTK_HEXAHEDRON: cells_hex}, points)

    # plot the grid (and suppress the camera position output)
    _ = grid.plot(show_edges=True)


def run_example():
    nnx = 3
    nny = 5
    nnz = 9
    xs = np.linspace(0, 5, nnx)
    ys = np.linspace(0, 5, nny)
    zs = np.linspace(0, 5, nnz)
    aeles = np.ones((len(xs)-1, len(ys)-1, len(zs)-1))
    aeles[0][0][0] = 0
    aeles[-1][0][0] = 0
    aeles[0][2][-1] = 0
    plot_regular_3dgrid(xs, ys, zs, aeles)

if __name__ == '__main__':
    run_example()



