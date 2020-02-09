import time
from PySide2 import QtWidgets, QtCore, QtGui
import OpenImageIO
import numpy as np


class OIIO_ImageViewer(QtWidgets.QGraphicsView):
    def __init__(self, parent=None):
        super(OIIO_ImageViewer, self).__init__(parent=parent)
        self._scene = QtWidgets.QGraphicsScene(parent=self)
        self._track = True

        self.setScene(self._scene)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setBackgroundBrush(QtGui.QColor(0,0,0,150))
        self.setInteractive(True)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        self.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setMouseTracking(True)
        self.setFixedSize(1024,1024)

    def set_image(self, path):
        image = self._oiio_get_qimage(path)
        item = QtWidgets.QGraphicsPixmapItem(QtGui.QPixmap.fromImage(image))
        item.setShapeMode(QtWidgets.QGraphicsPixmapItem.BoundingRectShape)
        item.setTransformationMode(QtCore.Qt.SmoothTransformation)
        self.scene().addItem(item)
        self.fitInView(item, QtCore.Qt.KeepAspectRatio)

    @classmethod
    def _oiio_get_qimage(cls, path):
        buf = OpenImageIO.ImageBuf(path)
        spec = buf.spec()
        if int(spec.nchannels) < 3:
            b = OpenImageIO.ImageBufAlgo.channels(
                b,
                (spec.channelnames[0], spec.channelnames[0], spec.channelnames[0]),
                ('R', 'G', 'B')
            )
        elif int(spec.nchannels) > 4:
            if spec.channelindex('A') > -1:
                b = OpenImageIO.ImageBufAlgo.channels(
                    b, ('R', 'G', 'B', 'A'), ('R', 'G', 'B', 'A'))
            else:
                b = OpenImageIO.ImageBufAlgo.channels(
                    b, ('R', 'G', 'B'), ('R', 'G', 'B'))

        np_arr = buf.get_pixels()
        np_arr = (np_arr / (1.0 / 255.0)).astype(np.uint8)
        image = QtGui.QImage(
            np_arr,
            spec.width,
            spec.height,
            spec.width * spec.nchannels,  # scanlines
            QtGui.QImage.Format_RGBA8888
        )

        # As soon as the numpy array is garbage collected, the QImage becomes
        # unuseable. By making a copy, the numpy array can safely be GC'd
        OpenImageIO.ImageCache().invalidate(path)
        return image.copy()



app = QtWidgets.QApplication([])
iv = OIIO_ImageViewer()
iv.show()
iv.set_image(ur'C:\Temp\CandleGlass.exr')
app.exec_()
