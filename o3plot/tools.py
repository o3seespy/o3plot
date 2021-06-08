

def add_color_bar(win, view, lut, vmin, vmax, label='', n_cols=10, units='', bal=0, copts=None):
    import numpy as np
    import pyqtgraph as pg
    from PyQt5 import QtWidgets
    # Create a viewbox to hold image item
    col_scale_vb = pg.ViewBox(enableMenu=False, border=None)
    col_scale_vb.disableAutoRange(pg.ViewBox.XYAxes)
    col_scale_vb.setMouseEnabled(x=False, y=False)
    col_scale_vb.setMinimumWidth(10)
    col_scale_vb.setMaximumWidth(20)
    win.addItem(col_scale_vb)
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

    col_scale_vb.addItem(color_scale_image_item)
    col_scale_vb.setZValue(101)

    overlay_vb = pg.ViewBox(enableMenu=False)
    overlay_vb.setZValue(100)

    axis_item = pg.AxisItem(orientation='right', showValues=True, width=400)
    axis_item.setRange(vmin, vmax)
    if units != '':
        label += f' [{units}]'
    axis_item.setLabel(text=label, units='')
    axis_item.setZValue(101)
    # axis_item.textWidth = 8
    axis_item.enableAutoSIPrefix(False)  # TODO: should be a copts
    
    axis_item.setPen(leg_pen)
    axis_item.setStyle(autoExpandTextSpace=True, tickLength=3)
    if bal:
        axis_item.setTicks([[(vmin, f'{vmin: .3g}'), (0, '0'), (vmax, f'{vmax: .3g}')]])
    else:
        axis_item.setTicks([[(vmin, f'{vmin: .3g}'), (vmax, f'{vmax: .3g}')]])
    # axis_item.setTickSpacing(levels=[(3, 0), (3, 1)])
    axis_item.setGeometry(10, 10, 1000, 50)

    main_layout = QtWidgets.QGraphicsGridLayout()
    pg_wid = pg.GraphicsWidget(parent=view)
    # geom = view.getGeometry()
    pg_wid.setLayout(main_layout)
    pg_wid.setGeometry(50, 5, 220, 50)
    main_layout.setContentsMargins(10, 10, 10, 0)
    main_layout.setSpacing(0)
    main_layout.addItem(col_scale_vb, 0, 1)
    main_layout.addItem(axis_item, 0, 2)
    overlay_vb.setParentItem(col_scale_vb.parentItem())
    col_scale_vb.setRange(xRange=[0, bar_width], yRange=[0, n_cols], padding=0.0, update=False, disableAutoRange=True)


def _load_mod_dat():
    import os
    folder_path = os.path.dirname(os.path.realpath(__file__))
    return open(os.path.join(folder_path, 'models_data.dat'))

