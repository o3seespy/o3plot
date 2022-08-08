

def add_color_bar(win, view, lut, vmin, vmax, label='', n_cols=10, units='', bal=0, copts=None, cb_coords=None):

    import numpy as np
    import pyqtgraph as pg
    from PyQt5 import QtWidgets
    from pyqtgraph import QtCore, QtGui
    # Create a viewbox to hold image item
    col_scale_vb = pg.ViewBox(enableMenu=False, border=None)
    col_scale_vb.disableAutoRange(pg.ViewBox.XYAxes)
    col_scale_vb.setMouseEnabled(x=False, y=False)
    col_scale_vb.setMinimumWidth(10)
    col_scale_vb.setMaximumWidth(20)
    # col_scale_vb.setBackgroundColor((220, 220, 220, 80))  # no affect
    win.addItem(col_scale_vb)  # Was addItem
    if copts is None:
        copts = {}
    leg_pen = copts.setdefault('leg_pen', 'w')

    # define matrix for colors and set it as an image item
    bar_width = 1
    img_ax_order = pg.getConfigOption('imageAxisOrder')
    img = np.linspace(vmin, vmax, n_cols) * np.ones((bar_width, n_cols))
    if img_ax_order == 'row-major':
        img = img.T
    color_scale_image_item = pg.ImageItem(img)
    color_scale_image_item.setLookupTable(lut)
    color_scale_image_item.setLevels([vmin, vmax])
    # col_scale_vb.setPen(leg_pen)

    col_scale_vb.addItem(color_scale_image_item)
    col_scale_vb.setZValue(101)

    # overlay_vb = pg.ViewBox(enableMenu=False)
    # overlay_vb.setZValue(100)

    axis_item = pg.AxisItem(orientation='right', showValues=True, width=400)
    axis_item.setRange(vmin, vmax)
    if units != '':
        label += f' [{units}]'
    labelStyle = {'color': leg_pen, 'font-size': '10pt'}
    axis_item.setLabel(text=label, units='', **labelStyle)
    axis_item.setZValue(101)
    # axis_item.textWidth = 8
    axis_item.enableAutoSIPrefix(False)  # TODO: should be a copts
    
    # axis_item.setPen(leg_pen)
    axis_item.setTextPen(leg_pen)
    axis_item.setStyle(autoExpandTextSpace=True, tickLength=3)
    if bal:
        axis_item.setTicks([[(vmin, f'{vmin: .3g}'), (0, '0'), (vmax, f'{vmax: .3g}')]])
    else:
        axis_item.setTicks([[(vmin, f'{vmin: .3g}'), (vmax, f'{vmax: .3g}')]])
    # axis_item.setTickSpacing(levels=[(3, 0), (3, 1)])
    axis_item.setGeometry(10, 10, 1000, 50)

    main_layout = QtWidgets.QGraphicsGridLayout()
    pg_wid = pg.GraphicsWidget(parent=view)
    # p = QtGui.QPainter()
    # p.setBrush(pg.mkBrush('w'))
    # pg_wid.paint(p, QtGui.QStyleOptionGraphicsItem())
    # geom = view.getGeometry()
    pg_wid.setLayout(main_layout)

    if cb_coords is None:
        cb_coords = [10, 10]
    else:
        cb_coords = list(cb_coords)
    if cb_coords[0] < 0:
        cb_coords[0] = view.size().width() + cb_coords[0]
    if cb_coords[1] < 0:
        cb_coords[1] = view.size().height() + cb_coords[1]
    print('cb_coords: ', cb_coords)
    pg_wid.setGeometry(cb_coords[0], cb_coords[1], 220, 50)
    # view.addItem(pg_wid)
    main_layout.setContentsMargins(10, 10, 10, 0)
    main_layout.setSpacing(0)
    main_layout.addItem(col_scale_vb, 0, 1)
    main_layout.addItem(axis_item, 0, 2)
    # overlay_vb.setParentItem(col_scale_vb.parentItem())
    col_scale_vb.setRange(xRange=[0, bar_width], yRange=[0, n_cols], padding=0.0, update=False, disableAutoRange=True)
    return pg_wid


def _load_mod_dat():
    import os
    folder_path = os.path.dirname(os.path.realpath(__file__))
    return open(os.path.join(folder_path, 'models_data.dat'))

