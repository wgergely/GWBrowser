from PySide2 import QtWidgets
from browser.bookmarkswidget import BookmarksWidget
from browser.assetwidget import AssetWidget
from browser.fileswidget import FilesWidget
from browser.listcontrolwidget import ListControlWidget, ListControlView

app = QtWidgets.QApplication([])

b = BookmarksWidget()
b.setFixedWidth(500)
b.show()
b.move(50, 50)

a = AssetWidget()
a.setFixedWidth(500)
a.show()
a.move(600, 50)

f = FilesWidget()
f.setFixedWidth(500)
f.show()
f.move(1150, 50)

b.model().sourceModel().modelReset.connect(
    lambda: a.model().sourceModel().set_active(b.model().sourceModel().active_index()))
b.model().sourceModel().modelReset.connect(
    a.model().sourceModel().modelDataResetRequested.emit)

b.model().sourceModel().activeChanged.connect(
    a.model().sourceModel().set_active)
b.model().sourceModel().activeChanged.connect(
    lambda x: a.model().sourceModel().modelDataResetRequested.emit())

a.model().sourceModel().modelReset.connect(
    lambda: f.model().sourceModel().set_active(a.model().sourceModel().active_index()))
a.model().sourceModel().modelReset.connect(
    f.model().sourceModel().modelDataResetRequested.emit)
a.model().sourceModel().modelReset.connect(f.model().invalidate)

a.model().sourceModel().activeChanged.connect(
    f.model().sourceModel().set_active)
a.model().sourceModel().activeChanged.connect(
    lambda x: f.model().sourceModel().modelDataResetRequested.emit())


l = ListControlView()
l.show()
l.setFixedWidth(500)
#


b.model().sourceModel().modelReset.connect(
    l.model().modelDataResetRequested.emit)

a.model().sourceModel().modelReset.connect(
    lambda: l.model().set_active(a.model().sourceModel().active_index()))
a.model().sourceModel().modelReset.connect(
    l.model().modelDataResetRequested.emit)

a.model().sourceModel().activeChanged.connect(
    l.model().set_active)
a.model().sourceModel().activeChanged.connect(
    lambda x: l.model().modelDataResetRequested.emit())


b.model().sourceModel().modelReset.connect(
    lambda: l.model().set_bookmark(b.model().sourceModel().active_index()))

b.model().sourceModel().activeChanged.connect(l.model().set_bookmark)
f.model().sourceModel().dataKeyChanged.connect(l.model().set_data_key)
f.model().sourceModel().modelReset.connect(
    lambda: l.model().set_data_key(f.model().sourceModel().data_key()))
f.model().sourceModel().dataTypeChanged.connect(l.model().set_data_type)


f.model().sourceModel().dataKeyChanged.connect(lambda x: l.model().modelDataResetRequested.emit())

# f.model().sourceModel().modelReset.connect(
#     lambda: l.model().set_data_key(f.model().sourceModel().data_key()))
# f.model().sourceModel().modelReset.connect(
#     lambda: l.model().set_data_type(f.model().sourceModel().data_type()))


app.processEvents()
b.model().sourceModel().modelDataResetRequested.emit()

app.exec_()
