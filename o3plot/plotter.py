from PyQt5 import QtCore, QtWidgets
from pyqtgraph.Qt import QtGui
import sys
import pyqtgraph as pg
import pyqtgraph.exporters
import numpy as np
from bwplot import cbox, colors
from o3plot import color_grid
import os
from o3plot import tools as o3ptools


class bidict(dict):  # unused?
    def __init__(self, *args, **kwargs):
        super(bidict, self).__init__(*args, **kwargs)
        self.inverse = {}
        for key, value in self.items():
            self.inverse.setdefault(value, []).append(key)

    def __setitem__(self, key, value):
        if key in self:
            self.inverse[self[key]].remove(key)
        super(bidict, self).__setitem__(key, value)
        self.inverse.setdefault(value, []).append(key)

    def __delitem__(self, key):
        self.inverse.setdefault(self[key], []).remove(key)
        if self[key] in self.inverse and not self.inverse[self[key]]:
            del self.inverse[self[key]]
        super(bidict, self).__delitem__(key)


class FEMGUI(QtGui.QWidget):
    def __init__(self):
        super(FEMGUI, self).__init__()
        hbox = self.mainLayout

        self.plotwidget = pg.PlotWidget()
        hbox.addWidget(self.plotwidget)

        self.increasebutton = QtGui.QPushButton("Increase Amplitude")
        self.decreasebutton = QtGui.QPushButton("Decrease Amplitude")

        hbox.addWidget(self.increasebutton)
        hbox.addWidget(self.decreasebutton)


class FEMWindow(pg.GraphicsWindow):  # TODO: consider switching to pandas.read_csv(ffp, engine='c')
    started = 0

    def __init__(self, parent=None):
        self.app = QtWidgets.QApplication([])
        super().__init__(parent=parent)
        #
        # pg.setConfigOptions(antialias=False)  # True seems to work as well
        # self.app.aboutToQuit.connect(self.stop)
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.mainLayout)
        self.timer = QtCore.QTimer(self)

        self.plotItem = self.addPlot(title="Nodes")
        self.fem_plot = FEMPlot(self.plotItem, self.timer)

    def init_model(self, coords, ele2node_tags=None):
        self.fem_plot.init_model(coords, ele2node_tags=ele2node_tags)

    def plot_dynamic(self, x, y, dt, xmag=10.0, ymag=10.0, node_c=None, ele_c=None, t_scale=1):
        self.fem_plot.plot_dynamic(x, y, dt, xmag=xmag, ymag=ymag, node_c=node_c, ele_c=ele_c, t_scale=t_scale)

    def start(self):
        if not self.started:
            self.started = 1
            self.raise_()
            self.app.exec_()

    # def stop(self):
    #     print('Exit')
    #     self.status = False
    #     self.app.close()
    #     pg.close()


class FEMPlot(object):
    selected_nodes = None

    def __init__(self, plot_item, timer):
        self.plotItem = plot_item
        self.timer = timer
        self.x_coords = None
        self.y_coords = None
        self.x = None
        self.y = None
        self.time = None
        self.i = 0
        self.node_points_plot = None
        self.ele_lines_plot = {}
        self.ele2node_tags = {}
        self.mat2node_tags = {}
        self.ele_x_coords = {}
        self.ele_y_coords = {}
        self.ele_connects = {}
        # self._mat2ele = bidict({})
        self._mat2ele = {}
        self.show_nodes = 1

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
                self.ele_connects[mat] = connect
                nl = len(self.ele2node_tags[eles[0]])
                if nl == 2:
                    pen = 'b'
                else:
                    pen = 'w'
                brush = pg.mkBrush(cbox(i, as255=True, alpha=80))
                self.ele_lines_plot[mat] = self.plotItem.plot(ele_x_coords, ele_y_coords, pen=pen,
                                                              connect=self.ele_connects[mat].flatten(), fillLevel='enclosed',
                                                              fillBrush=brush)
        if self.show_nodes:
            self.node_points_plot = self.plotItem.plot([], pen=None,
                                                       symbolBrush=(255, 0, 0), symbolSize=5, symbolPen=None)
            self.node_points_plot.setData(self.x_coords, self.y_coords)
        self.plotItem.autoRange(padding=0.05)  # TODO: depends on xmag
        self.plotItem.disableAutoRange()

    def plot_dynamic(self, x, y, dt, xmag=10.0, ymag=10.0, node_c=None, ele_c=None, t_scale=1):
        self.timer.setInterval(1000. * dt * t_scale)  # in milliseconds
        self.timer.start()
        self.node_c = node_c
        self.ele_c = ele_c
        self.x = np.array(x) * xmag
        self.y = np.array(y) * ymag
        if self.x_coords is not None:
            self.x += self.x_coords
            self.y += self.y_coords

        self.time = np.arange(len(self.x)) * dt

        # Prepare node colors
        if self.node_c is not None:
            ncol = colors.get_len_red_to_yellow()
            self.node_brush_list = [pg.mkColor(colors.red_to_yellow(i, as255=True)) for i in range(ncol)]

            y_max = np.max(self.node_c)
            y_min = np.min(self.node_c)
            inc = (y_max - y_min) * 0.001
            node_bis = (self.node_c - y_min) / (y_max + inc - y_min) * ncol
            self.node_bis = np.array(node_bis, dtype=int)

        if self.ele_c is not None:
            ecol = colors.get_len_red_to_yellow()
            self.ele_brush_list = [pg.mkColor(colors.red_to_yellow(i, as255=True)) for i in range(ecol)]
            active_eles = np.array(list(self.ele2node_tags))
            y_max = np.max(self.ele_c[active_eles])
            y_min = np.min(self.ele_c[active_eles])
            inc = (y_max - y_min) * 0.001
            print('ymin, ymax: ', y_min, y_max)

            ele_bis = (self.ele_c - y_min) / (y_max + inc - y_min) * ecol
            self.ele_bis = np.array(ele_bis, dtype=int)

        self.timer.timeout.connect(self.updater)

    def updater(self):
        if self.ele_c is not None:
            return self.updater_w_ele_c()
        self.i = self.i + 1
        if self.i == len(self.time) - 1:
            self.timer.stop()

        if self.node_c is not None:
            blist = np.array(self.node_brush_list)[self.node_bis[self.i]]
            # TODO: try using ScatterPlotWidget and colorMap
            if self.show_nodes:
                self.node_points_plot.setData(self.x[self.i], self.y[self.i], brush='g', symbol='o', symbolBrush=blist)
        elif self.show_nodes:
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
            self.ele_lines_plot[mat].setData(ele_x_coords, ele_y_coords, pen=pen, connect=self.ele_connects[mat].flatten(),
                                         fillLevel='enclosed', fillBrush=brush)
        self.plotItem.setTitle(f"Nodes time: {self.time[self.i]:.4g}s")

    def updater_w_ele_c(self):
        self.i = self.i + 1
        if self.i == len(self.time) - 1:
            self.timer.stop()

        if self.node_c is not None:
            blist = np.array(self.node_brush_list)[self.node_bis[self.i]]
            # TODO: try using ScatterPlotWidget and colorMap
            if self.show_nodes:
                self.node_points_plot.setData(self.x[self.i], self.y[self.i], brush='g', symbol='o', symbolBrush=blist)
        elif self.show_nodes:
            self.node_points_plot.setData(self.x[self.i], self.y[self.i], brush='g', symbol='o')
        for i, mat in enumerate(self.mat2node_tags):
            nl = len(self.ele2node_tags[self.mat2ele[mat][0]])
            if nl == 2:
                pen = 'b'
            else:
                pen = 'w'
        bis = self.ele_bis[self.mat2ele[mat], self.i]  # TODO: need ele
        unique_bis = list(set(list(bis.flatten())))
        unique_bis = np.arange(colors.get_len_red_to_yellow())
        print(self.i, 'unique_bis: ', unique_bis)

        if self.i == 1:
            self.p_items = {}
            for i, mat in enumerate(self.mat2node_tags):
                self.plotItem.removeItem(self.ele_lines_plot[mat])
                self.p_items[mat] = {}
                for bi in unique_bis:
                    brush = pg.mkBrush(self.ele_brush_list[bi])

                    self.p_items[mat][bi] = self.plotItem.plot([], [], pen=pen, connect=[], fillLevel='enclosed',
                                                                  fillBrush=brush)

        for i, mat in enumerate(self.mat2node_tags):
            nl = len(self.ele2node_tags[self.mat2ele[mat][0]])
            if nl == 2:
                pen = pg.mkPen([0, 0, 250, 80], width=0.7)
            else:
                pen = pg.mkPen([200, 200, 200, 80], width=0.7)

            for bi in unique_bis:
                inds = np.where(bis == bi)
                if len(inds[0]):
                    brush = pg.mkBrush(self.ele_brush_list[bi])
                    w = self.mat2node_tags[mat]
                    r = self.mat2node_tags[mat][inds]
                    cons1 = self.ele_connects[mat]
                    cons = self.ele_connects[mat][inds]
                    ele_x_coords1 = self.x[self.i][(self.mat2node_tags[mat] - 1)]
                    ele_x_coords = self.x[self.i][(self.mat2node_tags[mat][inds] - 1)]
                    ele_y_coords = (self.y[self.i])[(self.mat2node_tags[mat][inds] - 1)]
                    ele_x_coords = np.insert(ele_x_coords, len(ele_x_coords[0]), ele_x_coords[:, 0], axis=1).flatten()
                    ele_y_coords = np.insert(ele_y_coords, len(ele_y_coords[0]), ele_y_coords[:, 0], axis=1).flatten()
                    self.p_items[mat][bi].setData(ele_x_coords, ele_y_coords, pen=pen, connect=cons.flatten(),
                                         fillLevel='enclosed', fillBrush=brush)
                else:
                    self.p_items[mat][bi].setData([], [])


def get_app_and_window():
    app = QtWidgets.QApplication([])
    pg.setConfigOptions(antialias=False)  # True seems to work as well
    return app, FEMWindow()


def create_scaled_window_for_tds(tds, title='', max_px_width=1000, max_px_height=700, y_sf=1):
    win = pg.plot()
    img_height = max(tds.y_surf) + tds.height
    img_width = tds.width
    sf = min([max_px_width / img_width, max_px_height / img_height])
    win.setGeometry(100, 100, tds.width * sf, int(max(tds.y_surf) + tds.height) * sf * y_sf)
    win.setWindowTitle(title)
    win.setXRange(0, tds.width)
    win.setYRange(-tds.height, max(tds.y_surf))
    return win


def plot_two_d_system(tds, win=None, c2='w', cs='b'):
    if win is None:
        win = pg.plot()
    # import sfsimodels as sm
    # assert isinstance(tds, sm.TwoDSystem)
    y_sps_surf = np.interp(tds.x_sps, tds.x_surf, tds.y_surf)
    win.plot(tds.x_surf, tds.y_surf, pen=c2)
    for i in range(len(tds.sps)):
        x0 = tds.x_sps[i]
        if i == len(tds.sps) - 1:
            x1 = tds.width
        else:
            x1 = tds.x_sps[i + 1]
        xs = np.array([x0, x1])
        x_angles = list(tds.sps[i].x_angles)
        sp = tds.sps[i]
        for ll in range(1, sp.n_layers + 1):
            if x_angles[ll - 1] is not None:
                ys = y_sps_surf[i] - sp.layer_depth(ll) + x_angles[ll - 1] * (xs - x0)
                win.plot(xs, ys, pen=cs)
        win.plot([x0, x0], [y_sps_surf[i], -tds.height], pen=c2)
    win.plot([0, 0], [-tds.height, tds.y_surf[0]], pen=c2)
    win.plot([tds.width, tds.width], [-tds.height, tds.y_surf[-1]], pen=c2)
    win.plot([0, tds.width], [-tds.height, -tds.height], pen=c2)
    for i, bd in enumerate(tds.bds):
        fd = bd.fd
        fcx = tds.x_bds[i] + bd.x_fd
        fcy = np.interp(fcx, tds.x_surf, tds.y_surf)
        print(fcx, fcy)
        x = [fcx - fd.width / 2, fcx + fd.width / 2, fcx + fd.width / 2, fcx - fd.width / 2, fcx - fd.width / 2]
        y = [fcy - fd.depth, fcy - fd.depth, fcy - fd.depth + fd.height, fcy - fd.depth + fd.height, fcy - fd.depth]
        win.plot(x, y, pen=c2)


def plot_finite_element_mesh_onto_win(win, femesh, ele_c=None, label='', alpha=255):
    """
    Plots a finite element mesh object

    :param win:
    :param femesh:
    :param ele_c: array_like or str or None
        Specifies how he elements are colored, if None the color based on soil index,
        if str, the str must must a soil property and the color is scaled based on the value of the property
        if array_like, if shape of soil_grid, then color scale based on value,
        if array_like, if shape[:2] == soil_grid.shape(), and shape[2:]==3, then last axis interpreted as color values
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
    cd = {}
    active_eles = np.where(femesh.soil_grid != femesh.inactive_value)
    for xx in range(len(femesh.soil_grid)):
        x_ele = [xx, xx + 1, xx + 1, xx, xx]
        x_inds += x_ele * (n_y - 1)
        for yy in range(len(femesh.soil_grid[xx])):
            sl_ind = femesh.soil_grid[xx][yy]
            if sl_ind == femesh.inactive_value:
                sl_ind = -1
            elif ele_c is not None:
                sl_ind = 1
            if sl_ind not in ed:
                ed[sl_ind] = [[], []]

            y_ele = [yy + xx * n_y, yy + (xx + 1) * n_y, yy + 1 + (xx + 1) * n_y, yy + 1 + xx * n_y, yy + xx * n_y]
            ed[sl_ind][0].append(x_ele)
            ed[sl_ind][1].append(y_ele)
            if ele_c is not None:
                if sl_ind not in cd:
                    cd[sl_ind] = []
                cd[sl_ind].append(ele_c[xx][yy])
            y_inds += y_ele
    ele_bis = {}
    if ele_c is not None:
        if len(ele_c.shape) == 2:
            ecol = colors.get_len_red_to_yellow()
            brush_list = [pg.mkColor(colors.red_to_yellow(i, as255=True, alpha=alpha)) for i in range(ecol)]

            y_max = np.max(ele_c[active_eles])
            y_min = np.min(ele_c[active_eles])
            inc = (y_max - y_min) * 0.001

            for sl_ind in cd:
                cd[sl_ind] = np.array(cd[sl_ind])
                if inc == 0.0:
                    ele_bis[sl_ind] = int(ecol / 2) * np.ones_like(cd[sl_ind], dtype=int)
                else:
                    ele_bis[sl_ind] = (cd[sl_ind] - y_min) / (y_max + inc - y_min) * ecol
                    ele_bis[sl_ind] = np.array(ele_bis[sl_ind], dtype=int)
        elif len(ele_c.shape) == 3:
            pass
        else:
            raise ValueError('ele_c must be same dimensions as soil_grid')
    yc = y_all.flatten()
    xc = x_all.flatten()
    if len(xc) == len(yc):  # then it is vary_xy
        for item in ed:
            ed[item][0] = ed[item][1]

    for sl_ind in ed:
        ed[sl_ind][0] = np.array(ed[sl_ind][0])
        ed[sl_ind][1] = np.array(ed[sl_ind][1])
        if sl_ind < 0:
            pen = pg.mkPen([200, 200, 200, 10], width=0.7)
        else:
            pen = pg.mkPen([200, 200, 200, 80], width=0.7)
            if ele_c is not None:

                if len(ele_c.shape) == 3:  # colors directly specified

                    # brushes = np.array(brush_list)[ele_bis[sl_ind]]
                    brushes_col = ele_c[active_eles]
                    brushes = np.array([pg.mkColor(col) for col in brushes_col])  # TODO: v. slow
                    # eles_x_coords = xc[ed[sl_ind][0]]
                    # eles_y_coords = yc[ed[sl_ind][1]]
                    # ele_ind = ele
                    # item = color_grid.ColorGrid(eles_x_coords, eles_y_coords, brushes)
                else:
                    brushes = np.array(brush_list)[ele_bis[sl_ind]]
                eles_x_coords = xc[ed[sl_ind][0]]
                eles_y_coords = yc[ed[sl_ind][1]]
                item = color_grid.ColorGrid(eles_x_coords, eles_y_coords, brushes)
                win.plotItem.addItem(item)
            else:
                ed[sl_ind][0] = np.array(ed[sl_ind][0]).flatten()
                ed[sl_ind][1] = np.array(ed[sl_ind][1]).flatten()
                if sl_ind < 0:
                    brush = pg.mkBrush([255, 255, 255, 20])
                else:
                    brush = pg.mkColor(cbox(sl_ind, as255=True, alpha=alpha))
                ele_x_coords = xc[ed[sl_ind][0]]
                # ele_x_coords = xc[ed[sl_ind][1]]
                ele_y_coords = yc[ed[sl_ind][1]]
                ele_connects = np.array([1, 1, 1, 1, 0] * int(len(ed[sl_ind][0]) / 5))
                win.plotItem.plot(ele_x_coords, ele_y_coords, pen=pen,
                                  connect=ele_connects, fillLevel='enclosed',
                                  fillBrush=brush)

    if ele_c is not None and len(ele_c.shape) != 3:
        lut = np.zeros((155, 3), dtype=np.ubyte)
        lut[:, 0] = np.arange(100, 255)
        lut = np.array([colors.red_to_yellow(i, as255=True) for i in range(ecol)], dtype=int)
        a_inds = np.where(femesh.soil_grid != femesh.inactive_value)
        o3ptools.add_color_bar(win, win.plotItem, lut, vmin=np.min(ele_c[a_inds]), vmax=np.max(ele_c[a_inds]),
                               label=label, n_cols=ecol)

    return win.plotItem


def plot_node_disps(femesh, win, x_disps, y_disps):
    node_connects = np.array([1, 1, 0] * np.size(x_disps))
    xi_flat = femesh.x_nodes.flatten()
    yi_flat = femesh.y_nodes.flatten()
    xd_flat = x_disps.flatten()
    yd_flat = y_disps.flatten()
    x_coords = np.array([xi_flat, xi_flat + xd_flat, xi_flat]).flatten(order='F')
    y_coords = np.array([yi_flat, yi_flat + yd_flat, yi_flat]).flatten(order='F')
    pen = pg.mkPen([200, 0, 0, 200])
    curve = win.plotItem.plot(x_coords, y_coords, pen=pen,
                              connect=node_connects)
    # pg.CurveArrow(curve)
    # win.plotItem.Cu(x_coords, y_coords, pen=pen,
    #                   connect=node_connects)


def plot_finite_element_mesh(femesh, win=None, ele_c=None, start=True):
    if win is None:
        win = FEMWindow()
        win.resize(800, 600)
    plot_finite_element_mesh_onto_win(win, femesh, ele_c=ele_c)
    if start:
        win.start()
    return win


def plot_2dresults(o3res, xmag=1, ymag=1, t_scale=1, show_nodes=1):
    win = FEMWindow()
    win.resize(800, 600)
    if o3res.mat2ele_tags is not None:
        win.mat2ele = o3res.mat2ele_tags
    win.fem_plot.show_nodes = show_nodes
    win.init_model(o3res.coords, o3res.ele2node_tags)

    if o3res.dynamic:
        win.plot_dynamic(o3res.x_disp, o3res.y_disp, node_c=o3res.node_c, ele_c=o3res.ele_c, dt=o3res.dt, xmag=xmag,
                         ymag=ymag, t_scale=t_scale)
    win.start()


def replot(o3res, xmag=1, ymag=1, t_scale=1, show_nodes=1):
    # if o3res.coords is None:
    # o3res.load_from_cache()

    win = FEMWindow()
    win.resize(800, 600)
    if o3res.mat2ele_tags is not None:
        win.mat2ele = o3res.mat2ele_tags
    win.fem_plot.show_nodes = show_nodes
    win.init_model(o3res.coords, o3res.ele2node_tags)

    if o3res.dynamic:
        win.plot_dynamic(o3res.x_disp, o3res.y_disp, node_c=o3res.node_c, ele_c=o3res.ele_c, dt=o3res.dt, xmag=xmag,
                         ymag=ymag, t_scale=t_scale)
    win.start()


def show_constructor(fc):
    femesh = fc.femesh
    win = pg.plot()
    win.setWindowTitle('ECP definition')
    win.setXRange(0, fc.tds.width)
    win.setYRange(-fc.tds.height, max(fc.tds.y_surf))

    plot_finite_element_mesh_onto_win(win, femesh)

    xcs = list(fc.yd)
    xcs.sort()
    xcs = np.array(xcs)
    for i in range(len(xcs)):
        win.addItem(pg.InfiniteLine(xcs[i], angle=90, pen=(0, 255, 0, 100)))

    for i, sp in enumerate(fc.tds.sps):
        if i == 0:
            x_curr = 0
        else:
            x_curr = fc.tds.x_sps[i]
        if i == len(fc.tds.sps) - 1:
            x_next = fc.tds.width - 0
        else:
            x_next = fc.tds.x_sps[i + 1]
        y_surf_lhs = np.interp(x_curr, fc.tds.x_surf, fc.tds.y_surf)
        for j in range(1, sp.n_layers):
            sl = sp.layer(j + 1)
            y_tl = y_surf_lhs - sp.layer_depth(j + 1)
            y_bl = y_tl - sp.layer_height(j + 1)
            y_tr = y_tl + (x_next - x_curr) * sp.x_angles[j - 1]
            y_br = y_bl + (x_next - x_curr) * sp.x_angles[j]
            pen = pg.mkPen(color=(20, 20, 20), width=2)
            win.plot(x=[x_curr, x_next], y=[y_tl, y_tr], pen=pen)

        for j in range(len(fc.sds)):
            pen = pg.mkPen(color=(200, 0, 0), width=2)
            win.plot(x=fc.sds[j][0], y=fc.sds[j][1], pen=pen)

    # o3plot.plot_two_d_system(win, tds)
    # #
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()


def show():
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()


def save(win, ffp, width=1000):
    exp = pg.exporters.ImageExporter(win.plotItem)
    exp.params['width'] = width
    exp.export(ffp)


def revamp_legend(leg):
    lab_names = []
    leg_items = []
    for item in leg.items:
        sample = item[0]
        label = item[1]
        if label.text not in lab_names:
            lab_names.append(label.text)
            leg_items.append(item)
        else:
            leg.layout.removeItem(sample)  # remove from layout
            sample.close()  # remove from drawing
            leg.layout.removeItem(label)
            label.close()
    leg.items = leg_items
    leg.updateSize()

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
