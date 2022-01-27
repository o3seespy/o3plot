import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui
import numpy as np

class ColorGrid(pg.GraphicsObject):
    def __init__(self, xdata, ydata, brushes=None, pen_col=None):
        pg.GraphicsObject.__init__(self)
        self.xdata = xdata
        self.ydata = ydata
        self.brushes = brushes
        if pen_col is None:
            self.pen_col = (180, 180, 180)
        else:
            self.pen_col = pen_col
        self.generatePicture()

    def generatePicture(self):
        """
        Pre-compute a QPicture object to allow paint() to run much more quickly,
        :return:
        """
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        p.setPen(pg.mkPen(self.pen_col))
        for i in range(len(self.xdata)):
            path = pg.arrayToQPath(self.xdata[i], self.ydata[i])
            p2 = QtGui.QPainterPath(path)
            if self.brushes is None:
                brush = pg.mkBrush((100, 100, 10 + i * 1))
            else:
                brush = self.brushes[i]
            p.fillPath(p2, brush)
            p.drawPath(p2)

        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        """
        indicate the entire area that will be drawn on
        or else we will get artifacts and possibly crashing.
        (in this case, QPicture does all the work of computing the bouning rect for us)
        :return:
        """
        return QtCore.QRectF(self.picture.boundingRect())

def run():
    x_all = []
    y_all = []
    for j in range(10):
        x = np.array([0, 1, 1, 0, 0]) + j * 2
        y = np.array([0, 0, 1, 1, 0]) + j * 2
        x_all.append(x)
        y_all.append(y)
    x_all = np.array(x_all)
    y_all = np.array(y_all)

    item = ColorGrid(x_all, y_all)
    plt = pg.plot()
    plt.addItem(item)
    plt.setWindowTitle('pyqtgraph example: customGraphicsItem')

    ## Start Qt event loop unless running in interactive mode or using pyside.
    if __name__ == '__main__':
        import sys

        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QApplication.instance().exec_()

if __name__ == '__main__':
    run()
