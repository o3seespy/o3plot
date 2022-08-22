import sfsimodels as sm
import o3plot as o3p
import numpy as np
from o3plot import plot_pyvista


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
    plotter = o3p.plot_pyvista.plot_regular_3dgrid(xs, ys, zs, aeles)
    plotter.show()
    plotter.clear()


def single_footing():
    fd = sm.RaftFoundation(length=3.5, width=1.2, height=0.8, depth=0.6)
    fd.ip_axis = 'length'
    fd.x = 0
    fd.y = 0

    xs = np.array([-fd.lip / 2 + fd.x, fd.lip / 2 + fd.x])
    ys = np.array([-fd.loop / 2 + fd.y, fd.loop / 2 + fd.y])
    zs = np.array([-fd.depth, fd.height - fd.depth])
    aeles = np.ones((len(xs) - 1, len(ys) - 1, len(zs) - 1))
    plotter = o3p.plot_pyvista.plot_regular_3dgrid(xs, ys, zs, aeles)
    plotter.show()
    plotter.clear()


def wall_and_footing():
    wb = sm.WallBuilding(n_storeys=3)
    wb.interstorey_heights = np.ones(wb.n_storeys) * 3.4
    wb.wall_depth = 2.1
    wb.wall_width = 0.3
    wb.floor_width = 10.0
    wb.floor_length = 20.0
    wb.n_walls = 4
    wb.floor_thickness = 0.3
    wb.wall_norm_coords = [(0, 0.2), (0, 0.8), (1, 0.2), (1, 0.8)]
    plotter = o3p.plot_pyvista.get_plotter()
    fd = sm.RaftFoundation(length=3.5, width=1.2, height=0.8, depth=0.6)
    fd.ip_axis = 'length'
    fd_top = fd.height - fd.depth
    for wc in wb.wall_norm_coords:

        yw = wb.floor_width * wc[0]
        xw = wb.floor_length * wc[1]
        if wc[0] == 0:
            yw += wb.wall_width / 2
        elif wc[0] == 0:
            yw -= wb.wall_width / 2
        ys = np.array([yw - wb.wall_width / 2, yw + wb.wall_width / 2])
        xs = np.array([xw - wb.wall_depth / 2, xw + wb.wall_depth / 2])
        zs = np.array([fd_top, wb.heights[-1] + fd_top])
        o3p.plot_pyvista.plot_regular_3dgrid(xs, ys, zs, plotter=plotter)

        fd.x = xw
        fd.y = yw

        xs = np.array([-fd.lip / 2 + fd.x, fd.lip / 2 + fd.x])
        ys = np.array([-fd.loop / 2 + fd.y, fd.loop / 2 + fd.y])
        zs = np.array([-fd.depth, fd.height - fd.depth])
        o3p.plot_pyvista.plot_regular_3dgrid(xs, ys, zs, plotter=plotter)
    hfloors = wb.heights
    hfloors = np.insert(hfloors, 0, 0)
    hfloors += fd_top
    for nn in range(wb.n_storeys + 1):
        xs = np.array([0, wb.floor_length])
        ys = np.array([0, wb.floor_width])
        zs = np.array([hfloors[nn], hfloors[nn]-wb.floor_thickness])
        # print(xs, ys, zs)
        o3p.plot_pyvista.plot_regular_3dgrid(xs, ys, zs, plotter=plotter)

    fb = sm.FrameBuilding(n_storeys=wb.n_storeys, n_bays=2)
    fb.n_gravity_frames = 5
    fb.n_seismic_frames = 0
    fb.interstorey_heights = wb.interstorey_heights
    fb.floor_length = wb.floor_width  # note: switched
    fb.floor_width = wb.floor_length
    col_d = 0.5
    fb.bay_lengths = (fb.floor_length - col_d) / fb.n_bays * np.ones(fb.n_bays)
    fb.set_beam_prop('depth', 0.45, 'all')
    fb.set_beam_prop('width', 0.35, 'all')
    fb.set_column_prop('depth', col_d, 'all')
    fb.set_column_prop('width', 0.5, 'all')
    fb.frame_norm_coords = np.linspace(0, 1, fb.n_frames)
    foot = sm.PadFooting()
    foot.width = 1.5
    foot.length = 1.5
    foot.depth = fd.depth
    foot.height = fd.height
    ybeams = np.cumsum(fb.bay_lengths) + col_d / 2
    ycols = np.insert(ybeams, 0, col_d / 2)
    for nn in range(1, wb.n_storeys+1):
        for ff in range(fb.n_frames):
            for bb in range(fb.n_bays):

                beam = fb.beams[nn-1][bb].s[0]
                xf = fb.floor_width * fb.frame_norm_coords[ff]
                yb = ybeams[bb]
                xs = np.array([xf - beam.width / 2, xf + beam.width / 2])
                ys = np.array([yb - fb.bay_lengths[bb], yb])
                zs = np.array([hfloors[nn] - beam.depth, hfloors[nn]])
                print(xs, ys, zs)
                o3p.plot_pyvista.plot_regular_3dgrid(xs, ys, zs, plotter=plotter)
            for cc in range(fb.n_cols):
                col = fb.columns[nn-1][cc].s[0]
                xf = fb.floor_width * fb.frame_norm_coords[ff]
                yc = ycols[cc]
                xs = np.array([xf - col.width / 2, xf + col.width / 2])
                ys = np.array([yc - col.depth / 2, yc + col.depth / 2])
                zs = np.array([hfloors[nn], hfloors[nn-1]])
                print(xs, ys, zs)
                o3p.plot_pyvista.plot_regular_3dgrid(xs, ys, zs, plotter=plotter)

                if nn == 1:
                    xf = fb.floor_width * fb.frame_norm_coords[ff]
                    yc = ycols[cc]

                    xs = np.array([xf - foot.width / 2, xf + foot.width / 2])
                    ys = np.array([yc - foot.length / 2, yc + foot.length / 2])
                    zs = np.array([-fd.depth, fd.height - fd.depth])
                    print(xs, ys, zs)
                    o3p.plot_pyvista.plot_regular_3dgrid(xs, ys, zs, plotter=plotter)


    plotter.show()
    plotter.clear()

if __name__ == '__main__':
    # run_example()
    wall_and_footing()