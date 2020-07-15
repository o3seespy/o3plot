from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg
import numpy as np
from bwplot import cbox, colors
import os
import o3seespy as o3


class bidict(dict):
    def __init__(self, *args, **kwargs):
        super(bidict, self).__init__(*args, **kwargs)
        self.inverse = {}
        for key, value in self.items():
            self.inverse.setdefault(value,[]).append(key)

    def __setitem__(self, key, value):
        if key in self:
            self.inverse[self[key]].remove(key)
        super(bidict, self).__setitem__(key, value)
        self.inverse.setdefault(value,[]).append(key)

    def __delitem__(self, key):
        self.inverse.setdefault(self[key],[]).remove(key)
        if self[key] in self.inverse and not self.inverse[self[key]]:
            del self.inverse[self[key]]
        super(bidict, self).__delitem__(key)


class Window(pg.GraphicsWindow):  # TODO: consider switching to pandas.read_csv(ffp, engine='c')
    started = 0
    selected_nodes = None

    def __init__(self, parent=None):
        self.app = QtWidgets.QApplication([])
        super().__init__(parent=parent)
        #
        # pg.setConfigOptions(antialias=False)  # True seems to work as well
        # self.app.aboutToQuit.connect(self.stop)
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.mainLayout)
        self.timer = QtCore.QTimer(self)
        self.x_coords = None
        self.y_coords = None
        self.x = None
        self.y = None
        self.time = None
        self.i = 0
        self.plotItem = self.addPlot(title="Nodes")
        self.node_points_plot = None
        self.ele_lines_plot = {}
        self.ele2node_tags = {}
        self.mat2node_tags = {}
        self.ele_x_coords = {}
        self.ele_y_coords = {}
        self.ele_connects = {}
        # self._mat2ele = bidict({})
        self._mat2ele = {}

    @property
    def mat2ele(self):
        return self._mat2ele

    @mat2ele.setter
    def mat2ele(self, m2e_list):
        
        # self._mat2ele = bidict(m2e_dict)
        for line in m2e_list:
            if line[0] not in self._mat2ele:
                self._mat2ele[line[0]] = []
            self._mat2ele[line[0]].append(line[1])

    def renumber_nodes_and_eles(self):  # if selected nodes used
        empty_eles = []
        ele_node_strs = []
        for ele in self.ele2node_tags:
            new_tags = []
            for tag in self.ele2node_tags[ele]:
                try:
                    new_tags.append(np.where(tag == self.selected_nodes)[0][0] + 1)
                except IndexError:
                    continue
            self.ele2node_tags[ele] = self.reorder_node_tags_in_anticlockwise_direction(new_tags)
            # remove if empty
            if not len(new_tags):
                empty_eles.append(ele)
                continue
            # remove if already in
            ele_node_str = ' '.join(np.array(self.ele2node_tags[ele], dtype=str))
            if ele_node_str not in ele_node_strs:
                ele_node_strs.append(ele_node_str)
            else:
                empty_eles.append(ele)
        for ele in empty_eles:
            del self.ele2node_tags[ele]  # TODO: remove eles from mat2eles

    def reorder_node_tags_in_anticlockwise_direction(self, node_tags):
        node_tags = np.array(node_tags, dtype=int)
        x = self.x_coords[node_tags - 1]
        y = self.y_coords[node_tags - 1]
        xc = np.mean(x)
        yc = np.mean(y)
        angle = np.arctan2((y - yc), (x - xc))
        inds = np.argsort(angle)
        return np.array(node_tags)[inds[::-1]]

    def get_reverse_ele2node_tags(self):
        return list(self.ele2node_tags)[::-1]

    def init_model(self, coords, ele2node_tags=None):
        self.x_coords = np.array(coords)[:, 0]
        self.y_coords = np.array(coords)[:, 1]

        if ele2node_tags is not None:
            self.ele2node_tags = ele2node_tags
            self.mat2node_tags = {}
            if self.selected_nodes is not None:
                self.renumber_nodes_and_eles()

            if not len(self.mat2ele):  # then arrange by node len
                for ele in self.ele2node_tags:
                    n = len(self.ele2node_tags[ele]) - 1
                    if f'{n}-all' not in self.mat2ele:
                        self.mat2ele[f'{n}-all'] = []
                    self.mat2ele[f'{n}-all'].append(ele)

            for i, mat in enumerate(self.mat2ele):
                self.mat2ele[mat] = np.array(self.mat2ele[mat], dtype=int)
                eles = self.mat2ele[mat]
                # TODO: handle when mats assigned to eles of different node lens - not common by can be 8-node and 4-n
                self.mat2node_tags[mat] = np.array([self.ele2node_tags[ele] for ele in eles], dtype=int)
                ele_x_coords = self.x_coords[self.mat2node_tags[mat] - 1]
                ele_y_coords = self.y_coords[self.mat2node_tags[mat] - 1]
                ele_x_coords = np.insert(ele_x_coords, len(ele_x_coords[0]), ele_x_coords[:, 0], axis=1)
                ele_y_coords = np.insert(ele_y_coords, len(ele_y_coords[0]), ele_y_coords[:, 0], axis=1)
                connect = np.ones_like(ele_x_coords, dtype=np.ubyte)
                connect[:, -1] = 0
                ele_x_coords = ele_x_coords.flatten()
                ele_y_coords = ele_y_coords.flatten()
                self.ele_connects[mat] = connect.flatten()
                nl = len(self.ele2node_tags[eles[0]])
                if nl == 2:
                    pen = 'b'
                else:
                    pen = 'w'
                brush = pg.mkBrush(cbox(i, as255=True, alpha=80))
                self.ele_lines_plot[mat] = self.plotItem.plot(ele_x_coords, ele_y_coords, pen=pen,
                                                         connect=self.ele_connects[mat], fillLevel='enclosed',
                                                         fillBrush=brush)

        self.node_points_plot = self.plotItem.plot([], pen=None,
                                                   symbolBrush=(255, 0, 0), symbolSize=5, symbolPen=None)
        self.node_points_plot.setData(self.x_coords, self.y_coords)
        self.plotItem.autoRange(padding=0.05)  # TODO: depends on xmag
        self.plotItem.disableAutoRange()

    def start(self):
        if not self.started:
            self.started = 1
            self.raise_()
            self.app.exec_()

    def plot(self, x, y, dt, xmag=10.0, ymag=10.0, node_c=None, t_scale=1):
        self.timer.setInterval(1000. * dt * t_scale)  # in milliseconds
        self.timer.start()
        self.node_c = node_c
        self.x = np.array(x) * xmag
        self.y = np.array(y) * ymag
        if self.x_coords is not None:
            self.x += self.x_coords
            self.y += self.y_coords

        self.time = np.arange(len(self.x)) * dt

        # Prepare node colors
        if self.node_c is not None:
            ncol = colors.get_len_red_to_yellow()
            self.brush_list = [pg.mkColor(colors.red_to_yellow(i, as255=True)) for i in range(ncol)]

            y_max = np.max(self.node_c)
            y_min = np.min(self.node_c)
            inc = (y_max - y_min) * 0.001
            bis = (self.node_c - y_min) / (y_max + inc - y_min) * ncol
            self.bis = np.array(bis, dtype=int)

        self.timer.timeout.connect(self.updater)

    def updater(self):
        self.i = self.i + 1
        if self.i == len(self.time) - 1:
            self.timer.stop()

        if self.node_c is not None:
            blist = np.array(self.brush_list)[self.bis[self.i]]
            # TODO: try using ScatterPlotWidget and colorMap
            self.node_points_plot.setData(self.x[self.i], self.y[self.i], brush='g', symbol='o', symbolBrush=blist)
        else:
            self.node_points_plot.setData(self.x[self.i], self.y[self.i], brush='g', symbol='o')
        for i, mat in enumerate(self.mat2node_tags):
            nl = len(self.ele2node_tags[self.mat2ele[mat][0]])
            if nl == 2:
                pen = 'b'
            else:
                pen = 'w'
            brush = pg.mkBrush(cbox(i, as255=True, alpha=80))
            ele_x_coords = self.x[self.i][self.mat2node_tags[mat] - 1]
            ele_y_coords = (self.y[self.i])[self.mat2node_tags[mat] - 1]
            ele_x_coords = np.insert(ele_x_coords, len(ele_x_coords[0]), ele_x_coords[:, 0], axis=1).flatten()
            ele_y_coords = np.insert(ele_y_coords, len(ele_y_coords[0]), ele_y_coords[:, 0], axis=1).flatten()
            self.ele_lines_plot[mat].setData(ele_x_coords, ele_y_coords, pen=pen, connect=self.ele_connects[mat],
                                             fillLevel='enclosed', fillBrush=brush)
        self.plotItem.setTitle(f"Nodes time: {self.time[self.i]:.4g}s")

    def stop(self):
        print('Exit')
        self.status = False
        self.app.close()
        pg.close()
        # sys.exit()


def get_app_and_window():
    app = QtWidgets.QApplication([])
    pg.setConfigOptions(antialias=False)  # True seems to work as well
    return app, Window()


def plot_two_d_system(win, tds):
    # import sfsimodels as sm
    # assert isinstance(tds, sm.TwoDSystem)
    y_sps_surf = np.interp(tds.x_sps, tds.x_surf, tds.y_surf)

    for i in range(len(tds.sps)):
        x0 = tds.x_sps[i]
        if i == len(tds.sps) - 1:
            x1 = tds.width
        else:
            x1 = tds.x_sps[i + 1]
        xs = np.array([x0, x1])
        win.plot(tds.x_surf, tds.y_surf, pen='w')
        x_angles = [0] + list(tds.sps[i].x_angles)
        sp = tds.sps[i]
        for ll in range(2, sp.n_layers + 1):
            ys = y_sps_surf[i] - sp.layer_depth(ll) + x_angles[ll - 1] * (xs - x0)
            win.plot(xs, ys, pen='w')
    win.plot([0, 0], [-tds.height, tds.y_surf[0]], pen='w')
    win.plot([tds.width, tds.width], [-tds.height, tds.y_surf[-1]], pen='w')
    win.plot([0, tds.width], [-tds.height, -tds.height], pen='w')
    for i, bd in enumerate(tds.bds):
        fd = bd.fd
        fcx = tds.x_bds[i] + bd.x_fd
        fcy = np.interp(fcx, tds.x_surf, tds.y_surf)
        print(fcx, fcy)
        x = [fcx - fd.width / 2, fcx + fd.width / 2, fcx + fd.width / 2, fcx - fd.width / 2, fcx - fd.width / 2]
        y = [fcy - fd.depth, fcy - fd.depth, fcy - fd.depth + fd.height, fcy - fd.depth + fd.height, fcy - fd.depth]
        win.plot(x, y, pen='r')


def plot_finite_element_mesh(win, femesh):
    """
    Plots a finite element mesh object

    :param win:
    :param femesh:
    :return:
    """
    x_all = femesh.x_nodes
    y_all = femesh.y_nodes
    x_inds = []
    y_inds = []
    if hasattr(y_all[0], '__len__'):  # can either have varying y-coordinates or single set
        n_y = len(y_all[0])
    else:
        n_y = 0
    ed = {}
    for xx in range(len(femesh.soil_grid)):
        x_ele = [xx, xx + 1, xx + 1, xx, xx]
        x_inds += x_ele * (n_y - 1)
        for yy in range(len(femesh.soil_grid[xx])):
            sl_ind = femesh.soil_grid[xx][yy]
            if sl_ind > 1000:
                sl_ind = -1
            if sl_ind not in ed:
                ed[sl_ind] = [[], []]

            y_ele = [yy + xx * n_y, yy + (xx + 1) * n_y, yy + 1 + (xx + 1) * n_y, yy + 1 + xx * n_y, yy + xx * n_y]
            ed[sl_ind][0] += x_ele
            ed[sl_ind][1] += y_ele
            y_inds += y_ele

    yc = y_all.flatten()
    for sl_ind in ed:
        ed[sl_ind][0] = np.array(ed[sl_ind][0])
        ed[sl_ind][1] = np.array(ed[sl_ind][1])
        if sl_ind < 0:
            pen = pg.mkPen([200, 200, 200, 10])
            brush = pg.mkBrush([255, 255, 255, 20])
        else:
            pen = 'k'
            brush = pg.mkBrush(cbox(sl_ind, as255=True, alpha=90))
        ele_x_coords = x_all[ed[sl_ind][0]]
        ele_y_coords = yc[ed[sl_ind][1]]
        ele_connects = np.array([1, 1, 1, 1, 0] * int(len(ed[sl_ind][0]) / 5))
        win.plotItem.plot(ele_x_coords, ele_y_coords, pen=pen,
                                                  connect=ele_connects, fillLevel='enclosed',
                                                  fillBrush=brush)

#
# class O3Results(object):
#     cache_path = ''
#     coords = None
#     ele2node_tags = None
#     x_disp = None
#     y_disp = None
#     node_c = None
#     dynamic = True
#     used_r_starter = 0
#
#     def start_recorders(self, osi):
#         self.used_r_starter = 1
#         self.coords = o3.get_all_node_coords(osi)
#         self.ele2node_tags = o3.get_all_ele2node_tags_as_dict(osi)
#         if self.dynamic:
#             o3.recorder.NodesToFile(osi, self.cache_path + 'x_disp.txt', 'all', [o3.cc.DOF2D_X], 'disp', nsd=4)
#             o3.recorder.NodesToFile(osi, self.cache_path + 'y_disp.txt', 'all', [o3.cc.DOF2D_Y], 'disp', nsd=4)
#
#     def wipe_old_files(self):
#         for node_len in [2, 4, 8]:
#             ffp = self.cache_path + f'ele2node_tags_{node_len}.txt'
#             if os.path.exists(ffp):
#                 os.remove(ffp)
#         if not self.used_r_starter:
#             try:
#                 os.remove(self.cache_path + 'x_disp.txt')
#             except FileNotFoundError:
#                 pass
#             try:
#                 os.remove(self.cache_path + 'y_disp.txt')
#             except FileNotFoundError:
#                 pass
#         try:
#             os.remove(self.cache_path + 'node_c.txt')
#         except FileNotFoundError:
#             pass
#
#     def save_to_cache(self):
#         self.wipe_old_files()
#         np.savetxt(self.cache_path + 'coords.txt', self.coords)
#         for node_len in self.ele2node_tags:
#             np.savetxt(self.cache_path + f'ele2node_tags_{node_len}.txt', self.ele2node_tags[node_len], fmt='%i')
#         if self.dynamic:
#             if not self.used_r_starter:
#                 np.savetxt(self.cache_path + 'x_disp.txt', self.x_disp)
#                 np.savetxt(self.cache_path + 'y_disp.txt', self.y_disp)
#             if self.node_c is not None:
#                 np.savetxt(self.cache_path + 'node_c.txt', self.node_c)
#
#     def load_from_cache(self):
#         self.coords = np.loadtxt(self.cache_path + 'coords.txt')
#         self.ele2node_tags = {}
#         for node_len in [2, 4, 8]:
#             try:
#                 self.ele2node_tags[node_len] = np.loadtxt(self.cache_path + f'ele2node_tags_{node_len}.txt', ndmin=2)
#             except OSError:
#                 continue
#
#         if self.dynamic:
#             self.x_disp = np.loadtxt(self.cache_path + 'x_disp.txt')
#             self.y_disp = np.loadtxt(self.cache_path + 'y_disp.txt')
#             try:
#                 self.node_c = np.loadtxt(self.cache_path + 'node_c.txt')
#                 if len(self.node_c) == 0:
#                     self.node_c = None
#             except OSError:
#                 pass


def replot(out_folder='', dynamic=0, dt=0.01, xmag=1, ymag=1, t_scale=1):
    o3res = o3.results.Results2D()
    o3res.dynamic = dynamic
    o3res.cache_path = out_folder
    o3res.load_from_cache()

    win = Window()
    win.resize(800, 600)
    win.mat2ele = o3res.mat2ele_tags
    win.init_model(o3res.coords, o3res.ele2node_tags)

    if dynamic:
        win.plot(o3res.x_disp, o3res.y_disp, node_c=o3res.node_c, dt=dt, xmag=xmag, ymag=ymag, t_scale=t_scale)
    win.start()

def plot_2dresults(o3res, xmag=1, ymag=1, t_scale=1):

    win = Window()
    win.resize(800, 600)
    if o3res.mat2ele_tags is not None:
        win.mat2ele = o3res.mat2ele_tags
    win.init_model(o3res.coords, o3res.ele2node_tags)

    if o3res.dynamic:
        win.plot(o3res.x_disp, o3res.y_disp, node_c=o3res.node_c, dt=o3res.dt, xmag=xmag, ymag=ymag, t_scale=t_scale)
    win.start()

def replot(o3res, xmag=1, ymag=1, t_scale=1):
    # if o3res.coords is None:
    o3res.load_from_cache()

    win = Window()
    win.resize(800, 600)
    if o3res.mat2ele_tags is not None:
        win.mat2ele = o3res.mat2ele_tags
    win.init_model(o3res.coords, o3res.ele2node_tags)

    if o3res.dynamic:
        win.plot(o3res.x_disp, o3res.y_disp, node_c=o3res.node_c, dt=o3res.dt, xmag=xmag, ymag=ymag, t_scale=t_scale)
    win.start()


# if __name__ == '__main__':
#
#     app = QtWidgets.QApplication([])
#     pg.setConfigOptions(antialias=False)  # True seems to work as well
#     x = np.arange(0, 100)[np.newaxis, :] * np.ones((4, 100)) * 0.01 * np.arange(1, 5)[:, np.newaxis]
#     x = x.T
#     y = np.sin(x)
#     coords = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
#     win = Window()
#     win.init_model(coords)
#     win.plot(x, y, dt=0.01)
#     win.show()
#     win.resize(800, 600)
#     win.raise_()
#     app.exec_()
