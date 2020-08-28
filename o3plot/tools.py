

def add_color_bar(win, view, lut, vmin, vmax, label=''):
    import numpy as np
    import pyqtgraph as pg
    from PyQt5 import QtWidgets
    # Create a viewbox to hold image item
    col_scale_vb = pg.ViewBox(enableMenu=False, border=None)
    col_scale_vb.disableAutoRange(pg.ViewBox.XYAxes)
    col_scale_vb.setMouseEnabled(x=False, y=False)
    col_scale_vb.setMinimumWidth(10)
    col_scale_vb.setMaximumWidth(25)
    win.addItem(col_scale_vb)

    # define matrix for colors and set it as an image item
    bar_width = 1
    img_ax_order = pg.getConfigOption('imageAxisOrder')
    n_cols = 10
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

    axis_item = pg.AxisItem(orientation='right', showValues=True)
    axis_item.setRange(vmin, vmax)
    axis_item.setTicks([[(vmin, f'{vmin: .3g}'), (vmax, f'{vmax: .3g}')]])
    axis_item.setLabel(label)
    axis_item.setZValue(101)

    main_layout = QtWidgets.QGraphicsGridLayout()
    pg_wid = pg.GraphicsWidget(parent=view)
    pg_wid.setLayout(main_layout)
    main_layout.setContentsMargins(7, 7, 7, 7)
    main_layout.setSpacing(0)
    main_layout.addItem(col_scale_vb, 0, 1)
    main_layout.addItem(axis_item, 0, 2)
    overlay_vb.setParentItem(col_scale_vb.parentItem())
    col_scale_vb.setRange(xRange=[0, bar_width], yRange=[0, n_cols], padding=0.0, update=False, disableAutoRange=True)

