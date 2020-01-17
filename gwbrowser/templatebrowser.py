# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets, QtGui
import zipfile

from gwbrowser.basecontextmenu import BaseContextMenu, contextmenu
import gwbrowser.common as common
import gwbrowser.common_ui as common_ui
from gwbrowser.imagecache import ImageCache


class TemplateContextMenu(BaseContextMenu):

    def __init__(self, index, parent=None):
        super(TemplateContextMenu, self).__init__(index, parent=parent)
        self.add_refresh_menu()
        if not index:
            return
        self.add_template_menu()

    @contextmenu
    def add_refresh_menu(self, menu_set):
        menu_set[u'Refresh'] = {
            u'action': self.parent().load_templates,
        }
        return menu_set

    @contextmenu
    def add_template_menu(self, menu_set):
        pixmap = ImageCache.get_rsc_pixmap(
            u'folder', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)

        menu_set[u'Reveal'] = {
            u'icon': pixmap,
            u'action': lambda: common.reveal(self.index.data(QtCore.Qt.UserRole + 1)),
        }
        return menu_set


class TemplatesWidget(QtWidgets.QWidget):
    def __init__(self, mode, parent=None):
        super(TemplatesWidget, self).__init__(parent=parent)
        self._mode = mode
        self.ziplist_widget = None
        self.zipcontents_widget = None
        self.add_button = None

        self.setWindowTitle(u'Template Browser')
        self.setObjectName(u'TemplateBrowser')

        self._createUI()
        self._connectSignals()

    def mode(self):
        return self._mode

    def _createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = 6
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        row = QtWidgets.QWidget(parent=self)
        QtWidgets.QHBoxLayout(row)
        self.layout().addWidget(row)
        row.layout().setContentsMargins(0, 0, 0, 0)
        row.layout().setSpacing(0)
        row.layout().setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignHCenter)

        self.add_button = common_ui.ClickableIconButton(
            u'add',
            [common.ADD, common.ADD],
            common.INLINE_ICON_SIZE,
            parent=self
        )
        row.layout().addWidget(self.add_button)

        row = QtWidgets.QWidget(parent=self)
        QtWidgets.QHBoxLayout(row)
        self.layout().addWidget(row, 1)
        row.layout().setContentsMargins(0, 0, 0, 0)
        row.layout().setSpacing(0)

        self.ziplist_widget = ZipListWidget(self.mode(), parent=self)
        row.layout().addWidget(self.ziplist_widget)
        self.zipcontents_widget = ZipContentsWidget(parent=self)
        row.layout().addWidget(self.zipcontents_widget)

    def _connectSignals(self):
        self.ziplist_widget.selectionModel().selectionChanged.connect(self.itemActivated)
        self.add_button.clicked.connect(self.add_template)

    @QtCore.Slot()
    def add_template(self):
        dialog = QtWidgets.QFileDialog()
        common.set_custom_stylesheet(dialog)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilters([u'*.{}'.format(self.mode()), ])
        dialog.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dialog.setLabelText(QtWidgets.QFileDialog.Accept, u'Add template')
        dialog.setWindowTitle(u'Select a zipped asset template')
        dialog.exec_()

    @QtCore.Slot()
    def itemActivated(self, selectionList):
        self.zipcontents_widget.clear()
        if not selectionList:
            return
        index = selectionList.first().topLeft()
        if not index.isValid():
            return
        for f in index.data(QtCore.Qt.UserRole):
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, f)
            item.setFlags(QtCore.Qt.NoItemFlags)
            self.zipcontents_widget.addItem(item)


class ZipContentsWidget(QtWidgets.QListWidget):
    def __init__(self, parent=None):
        super(ZipContentsWidget, self).__init__(parent=parent)


class ZipListDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super(ZipListDelegate, self).__init__(parent=parent)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent=parent)
        editor.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        editor.setStyleSheet(u'padding: 0px; margin: 0px; border-radius: 0px;')
        validator = QtGui.QRegExpValidator(parent=editor)
        validator.setRegExp(QtCore.QRegExp(u'[\_\-a-zA-z0-9]+'))
        editor.setValidator(validator)
        return editor


class ZipListWidget(QtWidgets.QListWidget):
    def __init__(self, mode, parent=None):
        super(ZipListWidget, self).__init__(parent=parent)
        self._mode = mode
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked |
            QtWidgets.QAbstractItemView.EditKeyPressed |
            QtWidgets.QAbstractItemView.SelectedClicked
        )
        self.model().dataChanged.connect(self.dataChanged)
        self.setItemDelegate(ZipListDelegate(parent=self))

    def mode(self):
        return self._mode

    @QtCore.Slot()
    def dataChanged(self, index, bottomRight, vector, roles=None):
        oldpath = index.data(QtCore.Qt.UserRole + 1)
        name = index.data(QtCore.Qt.DisplayRole)
        name = name.replace(u'.{}'.format(self.mode()), '')
        self.model().setData(index, name, QtCore.Qt.DisplayRole)

        newpath = u'{}/{}.{}'.format(
            self.templates_dir_path(),
            name,
            self.mode()
        )
        if QtCore.QFile.rename(oldpath, newpath):
            self.model().setData(index, newpath, QtCore.Qt.UserRole + 1)

    def load_templates(self):
        self.clear()
        dir_ = self.templates_dir()
        for f in dir_.entryList():
            if self.mode().lower() not in f.lower():
                continue
            item = QtWidgets.QListWidgetItem(parent=self)
            item.setData(QtCore.Qt.DisplayRole, f.replace(u'.{}'.format(self.mode()), u''))

            path = u'{}/{}'.format(dir_.path(), f)
            with zipfile.ZipFile(path) as zip:
                namelist = [f.strip(u'/') for f in sorted(zip.namelist())]
                item.setData(QtCore.Qt.UserRole, namelist)
                item.setData(QtCore.Qt.UserRole + 1, path)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            self.addItem(item)

    def templates_dir_path(self):
        return u'{}/GWBrowser'.format(
            QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation))

    def templates_dir(self):
        dir_ = QtCore.QDir(self.templates_dir_path())
        dir_.setNameFilters([u'*.{}'.format(self.mode()), ])
        return dir_

    def showEvent(self, event):
        self.load_templates()

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        menu = TemplateContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = TemplatesWidget(u'asset')
    w.show()
    app.exec_()
