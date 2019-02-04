from PySide2 import QtCore, QtGui, QtNetwork, QtWidgets


class FileDownloader(QtCore.QObject):
    """Downloads and saves the given url."""
    # Signals
    downloaded = QtCore.Signal(QtCore.QByteArray)

    def __init__(self, url, parent=None):
        super(FileDownloader, self).__init__(parent=parent)
        self.url = url
        self.manager = QtNetwork.QNetworkAccessManager(parent=self)
        self.request = QtNetwork.QNetworkRequest(self.url)
        self.manager.finished.connect(lambda reply: self.downloaded.emit(reply.readAll()))

    def get(self):
        self.manager.get(self.request)


def save_image(data, path=None):
    image = QtGui.QImage()
    loaded = image.loadFromData(data)
    if not loaded:
        return

    image = image.convertToFormat(QtGui.QImage.Format_RGB32)
    image.save(path)
    QtCore.QCoreApplication.instance().quit()


app = QtCore.QCoreApplication([])
url = QtCore.QUrl(r'https://i2.wp.com/treasuresncreations.com/wp-content/uploads/2018/02/DSC_0157.jpg')
app.f = FileDownloader(url)
app.f.downloaded.connect(save_image)
app.f.get()
app.exec_()
