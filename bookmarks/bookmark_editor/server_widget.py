# -*- coding: utf-8 -*-
"""Sub-editor widget used by the Bookmark Editor to add and select jobs on on a
server.

"""
import functools

from PySide2 import QtCore, QtGui, QtWidgets

from .. import common
from .. import settings
from .. import common_ui
from .. import images
from .. import contextmenu
from .. import shortcuts
from .. import actions

from . import list_widget


class AddServerEditor(QtWidgets.QDialog):
    """Dialog used to add a new server to `local_settings`.

    """
    def __init__(self, parent=None):
        super(AddServerEditor, self).__init__(parent=parent)
        self.ok_button = None
        self.pick_button = None
        self.editor = None

        self._create_ui()
        self._connect_signals()
        self._add_completer()

    def _create_ui(self):
        if not self.parent():
            common.set_custom_stylesheet(self)

        QtWidgets.QVBoxLayout(self)

        o = common.MARGIN()
        self.layout().setSpacing(o)
        self.layout().setContentsMargins(o, o, o, o)

        self.ok_button = common_ui.PaintedButton(u'Done', parent=self)
        self.ok_button.setFixedHeight(common.ROW_HEIGHT())
        self.pick_button = common_ui.PaintedButton(u'Pick', parent=self)

        self.editor = common_ui.LineEdit(parent=self)
        self.editor.setPlaceholderText(u'Enter the path to a server, eg. \'//my_server/jobs\'')
        self.setFocusProxy(self.editor)
        self.editor.setFocusPolicy(QtCore.Qt.StrongFocus)

        row = common_ui.add_row(None, parent=self)
        row.layout().addWidget(self.editor, 1)
        row.layout().addWidget(self.pick_button, 0)

        row = common_ui.add_row(None, parent=self)
        row.layout().addWidget(self.ok_button, 1)

    def _add_completer(self):
        items = []
        for info in QtCore.QStorageInfo.mountedVolumes():
            if info.isValid():
                items.append(info.rootPath())
        items += common.SERVERS

        completer = QtWidgets.QCompleter(items, parent=self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        common.set_custom_stylesheet(completer.popup())
        self.editor.setCompleter(completer)

    def _connect_signals(self):
        self.ok_button.clicked.connect(lambda: self.done(QtWidgets.QDialog.Accepted))
        self.pick_button.clicked.connect(self.pick)
        self.editor.textChanged.connect(lambda: self.editor.setStyleSheet('color: rgba({});'.format(common.rgb(common.ADD))))

    @QtCore.Slot()
    def pick(self):
        _dir = QtWidgets.QFileDialog.getExistingDirectory(parent=self)
        if not _dir:
            return

        file_info = QtCore.QFileInfo(_dir)
        if file_info.exists():
            self.editor.setText(file_info.absoluteFilePath())

    def done(self, result):
        if result == QtWidgets.QDialog.Rejected:
            super(AddServerEditor, self).done(result)
            return

        if not self.text():
            return

        v = self.text()
        file_info = QtCore.QFileInfo(v)

        def invalid():
            self.editor.setStyleSheet('color: rgba({});'.format(common.rgb(common.REMOVE)))
            self.editor.blockSignals(True)
            self.editor.setText(v)
            self.editor.blockSignals(False)


        if not file_info.exists() or not file_info.isReadable() or v in common.SERVERS:
            invalid()
            return

        settings.local_settings.set_servers(common.SERVERS + [v,])
        super(AddServerEditor, self).done(QtWidgets.QDialog.Accepted)


    def text(self):
        v = self.editor.text()
        return settings.strip(v) if v else u''

    def showEvent(self, event):
        self.editor.setFocus(QtCore.Qt.NoFocusReason)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH(), common.ROW_HEIGHT() * 2)


class ServerContextMenu(contextmenu.BaseContextMenu):
    """Custom context menu used to control the list of saved servers.

    """

    def setup(self):
        self.add_menu()
        self.separator()
        if isinstance(self.index, QtWidgets.QListWidgetItem) and self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.reveal_menu()
            self.remove_menu()
        elif isinstance(self.index, QtWidgets.QListWidgetItem) and not self.index.flags() & QtCore.Qt.ItemIsEnabled:
            self.remove_menu()
        self.separator()
        self.refresh_menu()


    def add_menu(self):
        self.menu[u'Add server...'] = {
            u'action': self.parent().add,
            u'icon': self.get_icon(u'add', color=common.ADD)
        }

    def reveal_menu(self):
        self.menu[u'Reveal...'] = {
            u'action': lambda: actions.reveal(self.index.text() + '/.'),
            u'icon': self.get_icon(u'reveal_folder'),
        }

    def remove_menu(self):
        self.menu[u'Remove'] = {
            u'action': self.parent().remove,
            u'icon': self.get_icon(u'remove', color=common.REMOVE)
        }

    def refresh_menu(self):
        self.menu[u'Refresh'] = {
            u'action': (self.parent().init_data, self.parent().restore_current),
            u'icon': self.get_icon(u'refresh')
        }


class ServerListWidget(list_widget.ListWidget):
    """Simple list widget used to add and remove servers to/from the local
    settings.

    """
    serverChanged = QtCore.Signal(unicode)

    def __init__(self, parent=None):
        super(ServerListWidget, self).__init__(
            default_message=u'No servers found.',
            parent=parent
        )

        self._init_timer = QtCore.QTimer(parent=self)
        self._init_timer.setSingleShot(True)
        self._init_timer.setInterval(333)

        self.setItemDelegate(list_widget.ListWidgetDelegate(parent=self))
        self.setWindowTitle(u'Server Editor')
        self.setObjectName(u'ServerEditor')

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.viewport().setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        self.setMinimumWidth(common.WIDTH() * 0.33)

        self._connect_signals()
        self.init_shortcuts()

    def init_shortcuts(self):
        shortcuts.add_shortcuts(self, shortcuts.BookmarkEditorShortcuts)
        connect = functools.partial(shortcuts.connect, shortcuts.BookmarkEditorShortcuts)
        connect(shortcuts.AddItem, self.add)
        connect(shortcuts.RemoveItem, self.remove)

    def _connect_signals(self):
        super(ServerListWidget, self)._connect_signals()
        self._init_timer.timeout.connect(self.init_data)
        self._init_timer.timeout.connect(self.restore_current)

        self.selectionModel().selectionChanged.connect(self.save_current)
        self.selectionModel().selectionChanged.connect(self.emit_server_changed)

        settings.local_settings.serversChanged.connect(self.init_data)
        settings.local_settings.serversChanged.connect(self.restore_current)

    @common.debug
    @common.error
    @QtCore.Slot()
    def remove(self, *args, **kwargs):
        if not self.selectionModel().hasSelection():
            return
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        v = index.data(QtCore.Qt.DisplayRole)
        v = settings.strip(v)

        if v in common.SERVERS:
            del common.SERVERS[common.SERVERS.index(v)]

        settings.local_settings.set_servers(common.SERVERS)

    @common.debug
    @common.error
    @QtCore.Slot()
    def add(self, *args, **kwargs):

        w = AddServerEditor(parent=self.window())
        pos = self.mapToGlobal(self.window().rect().topLeft())
        w.move(pos)
        if w.exec_() == QtWidgets.QDialog.Accepted:
            self.restore_current(current=w.text())
            self.save_current()

    @common.debug
    @common.error
    @QtCore.Slot()
    def emit_server_changed(self, *args, **kwargs):
        """Slot connected to the server editor's `serverChanged` signal.

        """
        if not self.selectionModel().hasSelection():
            self.serverChanged.emit(None)
            return
        index = self.selectionModel().currentIndex()
        if not index.isValid():
            self.serverChanged.emit(None)
            return
        self.serverChanged.emit(index.data(QtCore.Qt.DisplayRole))

    @common.debug
    @common.error
    @QtCore.Slot()
    def save_current(self, *args, **kwargs):
        if not self.selectionModel().hasSelection():
            return

        index = self.selectionModel().currentIndex()
        if not index.isValid():
            return

        v = index.data(QtCore.Qt.DisplayRole)
        settings.local_settings.setValue(
            settings.UIStateSection,
            settings.BookmarkEditorServerKey,
            v
        )

    @common.debug
    @common.error
    @QtCore.Slot()
    def restore_current(self, current=None):
        if current is None:
            current = settings.local_settings.value(
                settings.UIStateSection,
                settings.BookmarkEditorServerKey
            )
        if not current:
            self.serverChanged.emit(None)
            return

        for n in xrange(self.count()):
            if not current == self.item(n).text():
                continue
            index = self.indexFromItem(self.item(n))
            self.selectionModel().select(
                index,
                QtCore.QItemSelectionModel.ClearAndSelect
            )


            self.scrollToItem(
                self.item(n), QtWidgets.QAbstractItemView.EnsureVisible)
            self.selectionModel().emitSelectionChanged(
                QtCore.QItemSelection(index, index),
                QtCore.QItemSelection()
            )
            self.serverChanged.emit(self.item(n).data(QtCore.Qt.DisplayRole))
            return

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        menu = ServerContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def showEvent(self, event):
        super(ServerListWidget, self).showEvent(event)
        self._init_timer.start()

    @common.debug
    @common.error
    @QtCore.Slot()
    def init_data(self, *args, **kwargs):
        self.serverChanged.emit(None)

        self.blockSignals(True)
        self.selectionModel().blockSignals(True)

        self.clear()
        for server in common.SERVERS:
            item = QtWidgets.QListWidgetItem(server)
            size = QtCore.QSize(
                0,
                common.MARGIN() * 2
            )
            item.setSizeHint(size)
            self.validate_item(item)
            self.insertItem(self.count(), item)

        self.blockSignals(False)
        self.selectionModel().blockSignals(False)

    @QtCore.Slot(QtWidgets.QListWidgetItem)
    def validate_item(self, item):
        self.blockSignals(True)

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'server', common.TEXT, common.ROW_HEIGHT() * 0.8)
        pixmap_selected = images.ImageCache.get_rsc_pixmap(
            u'server', common.TEXT_SELECTED, common.ROW_HEIGHT() * 0.8)
        pixmap_disabled = images.ImageCache.get_rsc_pixmap(
            u'remove', common.REMOVE, common.ROW_HEIGHT() * 0.8)
        icon = QtGui.QIcon()

        file_info = QtCore.QFileInfo(item.text())
        if file_info.exists() and file_info.isReadable() and file_info.isWritable():
            icon.addPixmap(pixmap, QtGui.QIcon.Normal)
            icon.addPixmap(pixmap_selected, QtGui.QIcon.Selected)
            icon.addPixmap(pixmap_selected, QtGui.QIcon.Active)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Disabled)
            item.setFlags(
                QtCore.Qt.ItemIsEnabled |
                QtCore.Qt.ItemIsSelectable |
                QtCore.Qt.ItemIsEditable
            )
            r = True
        else:
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Normal)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Selected)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Active)
            icon.addPixmap(pixmap_disabled, QtGui.QIcon.Disabled)
            item.setFlags(
                QtCore.Qt.ItemIsEditable
            )
            r = False

        item.setData(QtCore.Qt.DecorationRole, icon)
        self.blockSignals(False)

        if r:
            index = self.indexFromItem(item)
            self.selectionModel().emitSelectionChanged(
                QtCore.QItemSelection(index, index),
                QtCore.QItemSelection()
            )

        return r
