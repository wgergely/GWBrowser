# -*- coding: utf-8 -*-
"""
"""
import re
import sys
import zipfile

from PySide2 import QtCore, QtWidgets, QtGui

import gwbrowser.common as common
import gwbrowser.common_ui as common_ui
from gwbrowser._scanbookmark import scanbookmark as scanbookmark_it
from gwbrowser._scandir import scandir as scandir_it
from gwbrowser.imagecache import ImageCache
from gwbrowser.basecontextmenu import BaseContextMenu, contextmenu
from gwbrowser.addfilewidget import NameBase


class TemplateContextMenu(BaseContextMenu):

    def __init__(self, index, parent=None):
        super(TemplateContextMenu, self).__init__(index, parent=parent)
        self.add_refresh_menu()
        if not index:
            return
        self.add_new_template_menu()

        self.add_separator()
        self.add_remove_menu()

    @contextmenu
    def add_remove_menu(self, menu_set):
        pixmap = ImageCache.get_rsc_pixmap(
            u'close', common.REMOVE, common.INLINE_ICON_SIZE)

        @QtCore.Slot()
        def delete():
            mbox = QtWidgets.QMessageBox(parent=self)
            mbox.setWindowTitle(u'Delete template')
            mbox.setIcon(QtWidgets.QMessageBox.Warning)
            mbox.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            mbox.setDefaultButton(QtWidgets.QMessageBox.No)
            mbox.setText(u'Are you sure you want to delete this template?')
            res = mbox.exec_()

            if res == QtWidgets.QMessageBox.No:
                return
            if QtCore.QFile.remove(self.index.data(QtCore.Qt.UserRole + 1)):
                self.parent().load_templates()

        menu_set[u'Delete'] = {
            u'action': delete,
            u'icon': pixmap
        }

        return menu_set

    @contextmenu
    def add_refresh_menu(self, menu_set):
        pixmap = ImageCache.get_rsc_pixmap(
            u'refresh', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        add_pixmap = ImageCache.get_rsc_pixmap(
            u'add', common.ADD, common.INLINE_ICON_SIZE)

        parent = self.parent().parent().parent().parent()
        menu_set[u'Import a new {} template...'.format(parent.mode())] = {
            u'action': parent.add_new_template,
            u'icon': add_pixmap
        }

        menu_set[u'Refresh'] = {
            u'action': self.parent().load_templates,
            u'icon': pixmap
        }
        return menu_set

    @contextmenu
    def add_new_template_menu(self, menu_set):
        pixmap = ImageCache.get_rsc_pixmap(
            u'folder', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)

        menu_set[u'Show in file explorer...'] = {
            u'icon': pixmap,
            u'action': lambda: common.reveal(self.index.data(QtCore.Qt.UserRole + 1)),
        }
        return menu_set


class ZipListDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super(ZipListDelegate, self).__init__(parent=parent)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent=parent)
        editor.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        editor.setStyleSheet(u'padding: 0px; margin: 0px; border-radius: 0px;')
        validator = QtGui.QRegExpValidator(parent=editor)
        validator.setRegExp(QtCore.QRegExp(ur'[\_\-a-zA-z0-9]+'))
        editor.setValidator(validator)
        return editor


class ZipListWidget(QtWidgets.QListWidget):
    ROW_SIZE = 28

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

        path = self.templates_dir_path()
        _dir = QtCore.QDir(path)
        if not _dir.exists():
            _dir.mkpath(u'.')

    def mode(self):
        return self._mode

    @QtCore.Slot()
    def dataChanged(self, index, bottomRight, vector, roles=None):
        oldpath = index.data(QtCore.Qt.UserRole + 1)
        oldname = QtCore.QFileInfo(oldpath).baseName()
        name = index.data(QtCore.Qt.DisplayRole)
        name = name.replace(u'.zip', u'')

        newpath = u'{}/{}.zip'.format(
            self.templates_dir_path(),
            name
        )
        if QtCore.QFile.rename(oldpath, newpath):
            self.model().setData(index, name, QtCore.Qt.DisplayRole)
            self.model().setData(index, newpath, QtCore.Qt.UserRole + 1)
        else:
            self.model().setData(index, oldname, QtCore.Qt.DisplayRole)
            self.model().setData(index, oldpath, QtCore.Qt.UserRole + 1)

    def load_templates(self):
        self.clear()
        dir_ = QtCore.QDir(self.templates_dir_path())
        dir_.setNameFilters([u'*.zip', ])

        size = QtCore.QSize(1, self.ROW_SIZE)
        pixmap = ImageCache.get_rsc_pixmap(
            u'custom', common.SECONDARY_BACKGROUND, self.ROW_SIZE)
        icon = QtGui.QIcon(pixmap)

        for f in dir_.entryList():
            if u'zip' not in f.lower():
                continue
            item = QtWidgets.QListWidgetItem(parent=self)
            item.setData(QtCore.Qt.DisplayRole, f.replace(u'.zip', u''))
            item.setData(QtCore.Qt.SizeHintRole, size)
            item.setData(QtCore.Qt.DecorationRole, icon)

            path = u'{}/{}'.format(dir_.path(), f)
            with zipfile.ZipFile(path) as zip:
                namelist = [f.strip(u'/') for f in sorted(zip.namelist())]
                item.setData(QtCore.Qt.UserRole, namelist)
                item.setData(QtCore.Qt.UserRole + 1, path)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            self.addItem(item)

    def templates_dir_path(self):
        path = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation)
        path = u'{}/{}/{}_templates'.format(path, common.PRODUCT, self.mode())
        return path

    def showEvent(self, event):
        self.load_templates()

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        menu = TemplateContextMenu(item, parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()


class TemplatesWidget(QtWidgets.QWidget):
    templateCreated = QtCore.Signal()
    ROW_SIZE = 24
    BUTTON_SIZE = 18

    def __init__(self, mode, parent=None):
        super(TemplatesWidget, self).__init__(parent=parent)
        self._path = None
        self._mode = mode
        self.ziplist_widget = None
        self.zipcontents_widget = None
        self.add_button = None

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum,
        )
        effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.fade_in = QtCore.QPropertyAnimation(effect, 'opacity')
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        self.fade_in.setDuration(500)

        self.fade_out = QtCore.QPropertyAnimation(effect, 'opacity')
        self.fade_out.setStartValue(1)
        self.fade_out.setEndValue(0)
        self.fade_out.setDuration(200)
        self.fade_out.finished.connect(self.hide)

        self.setWindowTitle(u'Template Browser')

        self._createUI()
        self._connectSignals()

    def showEvent(self, event):
        self.fade_in.start()

    def mode(self):
        return self._mode

    def path(self):
        return self._path

    def set_path(self, val):
        self._path = val

    def _createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.INDICATOR_WIDTH * 2
        self.layout().setContentsMargins(0, o, 0, o)
        self.layout().setSpacing(o)
        # Name
        row = common_ui.add_row(u'{} name'.format(self.mode().title()), padding=None, parent=self)
        row.layout().setContentsMargins(0,0,0,0)
        row.layout().setSpacing(0)

        self.name_widget = NameBase(parent=self)
        self.name_widget.set_transparent()
        self.name_widget.setFont(common.PrimaryFont)
        self.name_widget.setPlaceholderText(u'Enter the name here...')
        regex = QtCore.QRegExp(ur'[a-zA-Z0-9\_\-]+')
        validator = QtGui.QRegExpValidator(regex, parent=self)
        self.name_widget.setValidator(validator)
        row.layout().addWidget(self.name_widget, 1)
        self.add_button = common_ui.ClickableIconButton(
            u'add',
            (common.ADD, common.ADD),
            self.BUTTON_SIZE,
            description=u'Add new {}'.format(self.mode().title()),
            parent=row
        )
        row.layout().addWidget(self.add_button)

        # Template Header
        row = common_ui.add_row(u'Select template', height=None, padding=None, parent=self)
        row.layout().setContentsMargins(0,0,0,0)
        row.layout().setSpacing(0)
        splitter = QtWidgets.QSplitter(parent=self)
        self.ziplist_widget = ZipListWidget(self.mode(), parent=self)
        self.ziplist_widget.setMinimumHeight(120)
        self.zipcontents_widget = QtWidgets.QListWidget(parent=self)
        splitter.addWidget(self.ziplist_widget)
        splitter.addWidget(self.zipcontents_widget)
        splitter.setSizes([60, 30])

        row.layout().addWidget(splitter, 1)
        self.layout().addStretch(1)

    def _connectSignals(self):
        self.ziplist_widget.selectionModel().selectionChanged.connect(self.itemActivated)
        self.add_button.clicked.connect(self.create_template)

    @QtCore.Slot()
    def create_template(self):
        """Verifies the user choices and expands the selected template to the
        currently set `path`.

        """
        mbox = QtWidgets.QMessageBox(parent=self)
        mbox.setWindowTitle(u'Error')
        mbox.setIcon(QtWidgets.QMessageBox.Warning)
        mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        mbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
        mbox.setFixedWidth(500)
        mbox.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

        if not self.path():
            mbox.setText(
                u'Unable to create {}.'.format(self.mode().lower()))
            mbox.setInformativeText(
                u'The parent path has not yet been set.')
            return mbox.exec_()

        file_info = QtCore.QFileInfo(self.path())
        if not file_info.exists():
            mbox.setText(
                u'Unable to create {}.'.format(self.mode().lower()))
            mbox.setInformativeText(
                u'The root "{}" does not exist.'.format(file_info.filePath()))
            return mbox.exec_()

        if not self.name_widget.text():
            mbox.setText(
                u'Must enter a name before adding an asset.')
            self.name_widget.setFocus()
            return mbox.exec_()

        file_info = file_info = QtCore.QFileInfo(
            u'{}/{}'.format(self.path(), self.name_widget.text()))

        if file_info.exists():
            mbox.setText(
                u'Unable to create {}.'.format(self.mode().lower()))
            mbox.setInformativeText(
                u'"{}" already exists.'.format(self.name_widget.text()))
            return mbox.exec_()

        model = self.ziplist_widget.selectionModel()
        if not model.hasSelection():
            mbox.setText(
                u'Must select a {} template before adding'.format(self.mode()))
            return mbox.exec_()

        index = model.selectedIndexes()[0]
        if not index.isValid():
            return

        source = index.data(QtCore.Qt.UserRole + 1)
        try:
            with zipfile.ZipFile(source, 'r', zipfile.ZIP_DEFLATED) as f:
                f.extractall(file_info.absoluteFilePath(), members=None, pwd=None)
            common.reveal(file_info.filePath())
            self.templateCreated.emit()
        except Exception as err:
            mbox.setText(u'An error occured when creating the {}'.format(self.mode()))
            mbox.setInformativeText('{}'.format(err))
            return mbox.exec_()
        finally:
            self.name_widget.setText(u'')

    @QtCore.Slot()
    def add_new_template(self):
        dialog = QtWidgets.QFileDialog(parent=self)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilters([u'*.zip', ])
        dialog.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dialog.setLabelText(QtWidgets.QFileDialog.Accept, u'Select {} Template'.format(self.mode().title()))
        dialog.setWindowTitle(u'Select a zip file containing the {m} folder hierarchy'.format(m=self.mode().lower()))
        if not dialog.exec_():
            return

        templates_dir = self.ziplist_widget.templates_dir_path()
        for source in dialog.selectedFiles():
            file_info = QtCore.QFileInfo(source)
            destination = u'{}/{}'.format(templates_dir, file_info.fileName())
            res = QtCore.QFile.copy(source, destination)
            if res:
                self.ziplist_widget.load_templates()

    @QtCore.Slot()
    def itemActivated(self, selectionList):
        self.zipcontents_widget.clear()
        if not selectionList:
            return
        index = selectionList.first().topLeft()
        if not index.isValid():
            return

        size = QtCore.QSize(0, self.ROW_SIZE)
        folder_pixmap = ImageCache.get_rsc_pixmap(
            u'folder', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        folder_icon = QtGui.QIcon(folder_pixmap)
        file_pixmap = ImageCache.get_rsc_pixmap(
            u'files', common.ADD, common.INLINE_ICON_SIZE)
        file_icon = QtGui.QIcon(file_pixmap)

        for f in index.data(QtCore.Qt.UserRole):
            if QtCore.QFileInfo(f).suffix():
                icon = file_icon
            else:
                icon = folder_icon
            item = QtWidgets.QListWidgetItem(parent=self)
            item.setData(QtCore.Qt.FontRole, common.SecondaryFont)
            item.setData(QtCore.Qt.DisplayRole, f)
            item.setData(QtCore.Qt.SizeHintRole, size)
            item.setData(QtCore.Qt.DecorationRole, icon)
            item.setFlags(QtCore.Qt.ItemIsSelectable)
            self.zipcontents_widget.addItem(item)


class ServerEditor(QtWidgets.QWidget):
    serversChanged = QtCore.Signal()

    BUTTON_SIZE = 18

    def __init__(self, parent=None):
        super(ServerEditor, self).__init__(parent=parent)
        self._rows = []
        self.add_server_button = None

        effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        self.fade_in = QtCore.QPropertyAnimation(effect, 'opacity')
        self.fade_in.setStartValue(0)
        self.fade_in.setEndValue(1)
        self.fade_in.setDuration(500)

        self.fade_out = QtCore.QPropertyAnimation(effect, 'opacity')
        self.fade_out.setStartValue(1)
        self.fade_out.setEndValue(0)
        self.fade_out.setDuration(200)
        self.fade_out.finished.connect(self.hide)

        self.createUI()
        self.add_rows()

    def showEvent(self, event):
        self.fade_in.start()

    def createUI(self):
        QtWidgets.QVBoxLayout(self)
        self.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        o = 0
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)

        row = common_ui.add_row(None, padding=0, parent=self)
        self.add_server_button = common_ui.ClickableIconButton(
            u'add',
            (common.ADD, common.ADD),
            self.BUTTON_SIZE,
            description=u'Add a new server',
            parent=row
        )
        self.add_server_label = QtWidgets.QLineEdit(parent=self)
        self.add_server_label.returnPressed.connect(self.add_server)
        self.add_server_button.clicked.connect(lambda: self.add_row(insert=True))

        row.layout().addWidget(self.add_server_button)
        row.layout().addWidget(self.add_server_label, 1)


    @QtCore.Slot()
    def add_server(self):
        label = self.add_server_label
        if not self.add_server_label.text():
            return

        file_info = QtCore.QFileInfo(label.text())
        if file_info.exists():
            server = file_info.absoluteFilePath()
            res = self.parent().data.add_server(server)
            label.setText(u'')
            if not res:
                return
            color = common.ADD
            label = self.add_row(server, insert=True)
            label.setReadOnly(True)
            label.setText(server)
            self.parent().init_select_server_combobox()
            return

        color = common.REMOVE
        label.setStyleSheet(
            u'color: rgba({})'.format(common.rgb(color)))

    def add_row(self, server, insert=False):
        """"""
        @QtCore.Slot()
        def remove_server():
            if row in self._rows:
                self._rows.remove(row)
            self.parent().data.remove_server(server)
            row.deleteLater()
            self.update()

        if insert:
            row = common_ui.add_row(None, padding=0, parent=None)
            self.layout().insertWidget(1, row)
        else:
            row = common_ui.add_row(None, padding=0, parent=self)

        if row not in self._rows:
            if insert:
                self._rows.insert(0, row)
            else:
                self._rows.append(row)

        label = QtWidgets.QLineEdit(parent=self)
        label.setText(server)
        label.setReadOnly(True)
        label.setStyleSheet(
            u'background-color: rgba(0,0,0,20);color: rgba(255,255,255,100);')
        button = common_ui.ClickableIconButton(
            u'close',
            (common.REMOVE, common.REMOVE),
            self.BUTTON_SIZE,
            description=u'Remove this server',
            parent=self
        )
        button.clicked.connect(remove_server)
        button.clicked.connect(self.parent().init_select_server_combobox)
        row.layout().addWidget(button)
        row.layout().addWidget(label)

        return label


    def add_rows(self):
        for server in self.parent().data.get_saved_servers():
            self.add_row(server=server)


class JobEditor(QtWidgets.QGroupBox):
    def __init__(self, parent=None):
        super(JobEditor, self).__init__(parent=parent)


class BookmarksData(QtCore.QObject):
    BOOKMARK_KEY = u'bookmarks'
    SERVER_KEY = u'servers'

    def __init__(self, parent=None):
        super(BookmarksData, self).__init__(parent=parent)
        path = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation)
        path = u'{}/{}/settings.ini'.format(path, common.PRODUCT)
        # Let's make sure we can create the settings file
        if not QtCore.QFileInfo(path).dir().mkpath(u'.'):
            raise RuntimeError(u'Failed to create "settings.ini"')

        self._settings = QtCore.QSettings(
            path,
            QtCore.QSettings.IniFormat,
            parent=self
        )

    @staticmethod
    def key(*args):
        def r(s): return re.sub(ur'[\\]+', u'/',
                                s, flags=re.UNICODE | re.IGNORECASE)
        k = u'/'.join([r(f).rstrip(u'/') for f in args]).lower().rstrip(u'/')
        return k

    def get_saved_servers(self):
        def r(s):
            return re.sub(
                ur'[\\]', u'/', s, flags=re.UNICODE | re.IGNORECASE)
        val = self._settings.value(self.SERVER_KEY)
        if not val:
            return []
        if isinstance(val, unicode):
            return [val.encode(u'utf-8').lower(), ]
        return sorted([r(f).encode(u'utf-8').lower() for f in val])

    def add_server(self, val):
        s = self.get_saved_servers()
        if val.lower() in s:
            return False
        s.append(val.lower())
        self._settings.setValue(self.SERVER_KEY, list(set(s)))
        return True

    def remove_server(self, val):
        s = self.get_saved_servers()
        if val.lower() in s:
            s.remove(val.lower())
        self._settings.setValue(self.SERVER_KEY, list(set(s)))

    def get_saved_bookmarks(self):
        def r(s): return re.sub(ur'[\\]', u'/',
                                s, flags=re.UNICODE | re.IGNORECASE)
        d = {}
        for k, v in self._get_saved_bookmarks().iteritems():
            d[k.encode(u'utf-8')] = {}
            for _k, _v in v.iteritems():
                d[k.encode(u'utf-8')][_k] = r(_v.encode(u'utf-8'))
        return d

    def _get_saved_bookmarks(self):
        val = self._settings.value(self.BOOKMARK_KEY)
        if not val:
            return {}
        return val

    def save_bookmark(self, server, job, bookmark_folder, add_config_dir=True):
        k = self.key(server, job, bookmark_folder)
        if add_config_dir:
            if not QtCore.QDir(k).mkpath(u'.bookmark'):
                print u'# Error: Could not add "{}/.bookmark"'.format(k)

        d = self._get_saved_bookmarks()
        d[k] = {
            u'server': unicode(server).encode(u'utf-8'),
            u'job':  unicode(job).encode(u'utf-8'),
            u'bookmark_folder':  unicode(bookmark_folder).encode(u'utf-8')
        }
        self._settings.setValue(self.BOOKMARK_KEY, d)

    def remove_saved_bookmark(self, server, job, bookmark_folder):
        k = self.key(server, job, bookmark_folder)
        d = self._get_saved_bookmarks()
        if k in d:
            del d[k]
        self._settings.setValue(self.BOOKMARK_KEY, d)
        pass

    def _bookmarks_it(self, path, recurse_limit):
        """Generator expression to return bookmark folders inside the given
        job.

        Args:
            path (unicode): The path to find the bookmarks in.
            recurse_limit (int): The number of subfolders to scan. Defaults to 5.

        Yields:
            DirEntry: The DirEntry object pointing to the

        """
        if recurse_limit < 0:
            return
        recurse_limit -= 1

        try:
            path = unicode(path, u'utf-8')
        except TypeError as e:
            try:
                path = path.decode(sys.getfilesystemencoding())
            except:
                pass
        try:
            scandir_it = scanbookmark_it(path)
        except OSError as error:
            return

        while True:
            try:
                try:
                    entry = next(scandir_it)
                except StopIteration:
                    break
            except Exception:
                return
            if entry.name.lower() == u'.bookmark'.lower():
                yield entry

            for entry in self._bookmarks_it(entry.path, recurse_limit):
                yield entry

    def find_bookmarks(self, server, job, recurse_limit=5):
        path = self.key(server, job)
        res = [f.dirpath.replace(path, u'').encode('utf-8')
               for f in self._bookmarks_it(path, recurse_limit)]
        return sorted(res)


class AddBookmarksWidget(QtWidgets.QWidget):
    ROW_HEIGHT = 36
    BUTTON_SIZE = 20

    def __init__(self, parent=None):
        super(AddBookmarksWidget, self).__init__(parent=parent)
        self.data = BookmarksData(parent=self)

        self._createUI()
        self._connectSignals()
        self.init_select_server_combobox()

    def _createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(o, o, o, o)

        row = common_ui.add_row(u'Select server', padding=0, parent=self)
        self.edit_servers_button = common_ui.PaintedButton(
            u'Edit...',
            width=80,
            parent=row
        )
        self.reveal_server_button = common_ui.ClickableIconButton(
            u'folder',
            (common.SECONDARY_BACKGROUND, common.SECONDARY_BACKGROUND),
            self.BUTTON_SIZE,
            description=u'Show the job in the explorer',
            parent=row
        )
        self.select_server_combobox = QtWidgets.QComboBox(parent=self)
        self.select_server_combobox.setDuplicatesEnabled(False)
        self.select_server_combobox.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToContents)

        row.layout().addWidget(self.select_server_combobox, 1)
        row.layout().addWidget(self.edit_servers_button)
        row.layout().addWidget(self.reveal_server_button)
        self.server_editor = ServerEditor(parent=self)
        self.server_editor.setHidden(True)
        self.layout().addWidget(self.server_editor)

        row = common_ui.add_row(u'Select job', padding=0, parent=self)
        self.select_job_combobox = QtWidgets.QComboBox(parent=self)
        self.select_job_combobox.setDuplicatesEnabled(False)
        self.select_job_combobox.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToContents)
        self.add_template_button = common_ui.PaintedButton(
            u'Edit...',
            width=80,
            parent=row
        )
        self.reveal_job_button = common_ui.ClickableIconButton(
            u'folder',
            (common.SECONDARY_BACKGROUND, common.SECONDARY_BACKGROUND),
            self.BUTTON_SIZE,
            description=u'Show the job in the explorer',
            parent=row
        )
        row.layout().addWidget(self.select_job_combobox, 1)
        row.layout().addWidget(self.add_template_button, 0)
        row.layout().addWidget(self.reveal_job_button, 0)

        @QtCore.Slot()
        def toggle_server_editor():
            is_hidden = self.server_editor.isHidden()
            if is_hidden:
                self.server_editor.setHidden(False)
                self.edit_servers_button.setText(u'Done')

                if not self.templates_widget.isHidden():
                    self.add_template_button.clicked.emit()
                return

            self.server_editor.fade_out.start()
            self.edit_servers_button.setText(u'Edit...')
            self.init_select_server_combobox()

        self.edit_servers_button.clicked.connect(toggle_server_editor)

        @QtCore.Slot()
        def reveal():
            idx = self.select_job_combobox.currentIndex()
            if idx < 0:
                return
            _data = self.select_job_combobox.itemData(
                idx, role=QtCore.Qt.UserRole
            )
            common.reveal(_data)

        self.reveal_job_button.clicked.connect(reveal)


        @QtCore.Slot()
        def toggle_template_editor():
            _bool = not self.templates_widget.isHidden()
            if _bool:
                self.templates_widget.fade_out.start()
            else:
                self.templates_widget.setHidden(_bool)

            self.add_template_button.setText(u'Edit...' if _bool else u'Done')


        self.add_template_button.clicked.connect(toggle_template_editor)
        self.templates_widget = TemplatesWidget(u'job', parent=self)
        self.templates_widget.setHidden(True)
        self.layout().addWidget(self.templates_widget)
        self.layout().addStretch(1)

    def _connectSignals(self):
        self.select_server_combobox.currentIndexChanged.connect(
            self.init_select_job_combobox)

    @QtCore.Slot()
    def init_select_server_combobox(self):
        n = 0
        idx = self.select_server_combobox.currentIndex()

        self.select_server_combobox.clear()
        for k in self.data.get_saved_servers():
            pixmap = ImageCache.get_rsc_pixmap(
                u'server', common.TEXT, self.ROW_HEIGHT)
            icon = QtGui.QIcon(pixmap)

            self.select_server_combobox.addItem(icon, k.upper(), userData=k)
            item = self.select_server_combobox.model().item(n)
            self.select_server_combobox.setItemData(
                n, QtCore.QSize(0, self.ROW_HEIGHT), QtCore.Qt.SizeHintRole)
            item.setData(common.TEXT, role=QtCore.Qt.TextColorRole)
            item.setData(common.BACKGROUND, role=QtCore.Qt.BackgroundColorRole)

            if not QtCore.QFileInfo(k).exists():
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)
                item.setData(common.TEXT_DISABLED,
                             role=QtCore.Qt.TextColorRole)
                item.setData(common.SECONDARY_BACKGROUND,
                             role=QtCore.Qt.BackgroundColorRole)
                # item.setData(common.SECONDARY_BACKGROUND, role=QtCore.Qt.BackgroundColorRole)
                _pixmap = ImageCache.get_rsc_pixmap(
                    u'close', common.REMOVE, self.ROW_HEIGHT)
                self.select_server_combobox.setItemIcon(
                    n, QtGui.QIcon(_pixmap))
            n += 1

        if idx >= 0:
            self.select_server_combobox.setCurrentIndex(idx)
        else:
            for n in xrange(self.select_server_combobox.count()):
                index = self.select_server_combobox.model().index(n, 0)
                if index.flags() & QtCore.Qt.ItemIsEnabled:
                    self.select_server_combobox.setCurrentIndex(n)
                    break

    @QtCore.Slot(int)
    def init_select_job_combobox(self, idx):
        self.select_job_combobox.clear()

        if idx < 0:
            return

        server = self.select_server_combobox.itemData(
            idx, role=QtCore.Qt.UserRole)

        file_info = QtCore.QFileInfo(server)
        if not file_info.exists():
            self.show_warning('"{}" does not exist'.format(server))
            return
        if not file_info.isReadable():
            self.show_warning('"{}" is not readable'.format(server))
            return

        n = 0
        for entry in scandir_it(server):
            # Let's explicitly check read access by trying to get the
            # files inside the folder
            is_valid = False
            try:
                next(scandir_it(entry.path))
                is_valid = True
            except StopIteration:
                is_valid = True
            except OSError:
                is_valid = False

            pixmap = ImageCache.get_rsc_pixmap(
                u'folder', common.TEXT, self.ROW_HEIGHT)
            icon = QtGui.QIcon(pixmap)

            self.select_job_combobox.addItem(
                icon, entry.name.upper(), userData=entry.path)
            item = self.select_job_combobox.model().item(n)
            self.select_job_combobox.setItemData(n, QtCore.QSize(
                0, self.ROW_HEIGHT), QtCore.Qt.SizeHintRole)
            item.setData(common.TEXT, role=QtCore.Qt.TextColorRole)
            item.setData(common.BACKGROUND, role=QtCore.Qt.BackgroundColorRole)

            if not is_valid:
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)
                item.setData(common.TEXT_DISABLED,
                             role=QtCore.Qt.TextColorRole)
                item.setData(common.SECONDARY_BACKGROUND,
                             role=QtCore.Qt.BackgroundColorRole)
                # item.setData(common.SECONDARY_BACKGROUND, role=QtCore.Qt.BackgroundColorRole)
                _pixmap = ImageCache.get_rsc_pixmap(
                    u'close', common.REMOVE, self.ROW_HEIGHT)
                self.select_job_combobox.setItemIcon(n, QtGui.QIcon(_pixmap))
            n += 1

    def show_warning(self, text):
        mbox = QtWidgets.QMessageBox(parent=self)
        mbox.setWindowTitle(u'Warning')
        mbox.setIcon(QtWidgets.QMessageBox.Warning)
        mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        mbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
        mbox.setText(text)
        mbox.exec_()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    data = BookmarksData()
    # data.add_server(u'C:/')
    # data.add_server(u'c:/')
    # data.add_server(u'd:/')
    # data.add_server(u'//sloth')
    widget = AddBookmarksWidget()
    widget.show()
    app.exec_()
