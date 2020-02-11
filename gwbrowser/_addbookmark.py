# -*- coding: utf-8 -*-
"""
"""
import re
import os
from gwbrowser.imagecache import ImageCache
import gwbrowser.common as common
import gwbrowser.common_ui as common_ui
from PySide2 import QtCore, QtWidgets, QtGui
from _scanbookmark import scanbookmark as scanbookmark_it
from _scandir import scandir as scandir_it


class ServerEditor(QtWidgets.QGroupBox):
    serversChanged = QtCore.Signal()

    BUTTON_SIZE = 18

    def __init__(self, parent=None):
        super(ServerEditor, self).__init__(parent=parent)
        self._rows = []
        self.add_button = None

        self.createUI()
        self.add_rows()

    def createUI(self):
        QtWidgets.QVBoxLayout(self)
        self.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        o = common.INDICATOR_WIDTH * 2
        self.layout().setContentsMargins(o,o,o,o)
        self.layout().setSpacing(0)

        row = common_ui.add_row(None, padding=0, parent=self)
        self.add_button = common_ui.ClickableIconButton(
            u'add',
            (common.ADD, common.ADD),
            self.BUTTON_SIZE,
            description=u'Add a new server',
            parent=row
        )
        self.add_button.clicked.connect(self.add_row)
        row.layout().addWidget(self.add_button)
        row.layout().addStretch(1)

    def add_row(self, server=u'', read_only=False):
        """"""
        def remove_button():
            button = common_ui.ClickableIconButton(
                u'close',
                (common.REMOVE, common.REMOVE),
                self.BUTTON_SIZE,
                description=u'Remove this server',
                parent=self
            )
            button.clicked.connect(remove_server)
            return button

        @QtCore.Slot()
        def remove_server():
            if row in self._rows:
                self._rows.remove(row)
            self.parent().data.remove_server(server)
            row.deleteLater()
            self.update()

        @QtCore.Slot()
        def add_server():
            file_info = QtCore.QFileInfo(label.text())
            if file_info.exists():
                color = common.ADD
                label.setReadOnly(True)
                label.setStyleSheet(
                    u'background-color: rgba(0,0,0,20);color: rgba({});'.format(common.rgb(color)))
            else:
                color = common.REMOVE
                label.setStyleSheet(
                    u'color: rgba({})'.format(common.rgb(color)))
                return

            path = file_info.absoluteFilePath()
            label.setText(path)
            self.parent().data.add_server(path)

            row.findChild(QtWidgets.QLabel).deleteLater()
            row.layout().addWidget(remove_button())

        def get_label():
            label = QtWidgets.QLineEdit(parent=self)
            label.setText(server)
            label.setReadOnly(read_only)
            if read_only:
                label.setStyleSheet(
                    u'background-color: rgba(0,0,0,20);color: rgba(255,255,255,100);')
            return label


        row = common_ui.add_row(None, padding=0, parent=self)
        if row not in self._rows:
            self._rows.append(row)

        label = get_label()

        if read_only:
            button = remove_button()
        else:
            button = common_ui.ClickableIconButton(
                u'Check',
                (common.ADD, common.ADD),
                self.BUTTON_SIZE,
                description=u'Save server',
                parent=self
            )
            button.clicked.connect(add_server)
            label.returnPressed.connect(add_server)

        button.clicked.connect(self.parent().init_select_server_combobox)
        label.returnPressed.connect(self.parent().init_select_server_combobox)

        row.layout().addWidget(label)
        row.layout().addWidget(button)

        label.setFocusPolicy(QtCore.Qt.StrongFocus)
        label.setFocus()

    def add_rows(self):
        for server in self.parent().data.get_saved_servers():
            self.add_row(server=server, read_only=True)


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
            return [val.encode(u'utf-8').lower(),]
        return sorted([r(f).encode(u'utf-8').lower() for f in val])

    def add_server(self, val):
        s = self.get_saved_servers()
        s.append(val.lower())
        self._settings.setValue(self.SERVER_KEY, list(set(s)))

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
        res = [f.dirpath.replace(path, u'').encode('utf-8') for f in self._bookmarks_it(path, recurse_limit)]
        return sorted(res)


class BookmarksWidget(QtWidgets.QWidget):
    ROW_HEIGHT = 36
    BUTTON_SIZE = 20

    def __init__(self, parent=None):
        super(BookmarksWidget, self).__init__(parent=parent)
        self.data = BookmarksData(parent=self)

        self._createUI()
        self._connectSignals()
        self.init_select_server_combobox()

    def _createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(o,o,o,o)

        row = common_ui.add_row(u'Select server', padding=0, parent=self)
        self.edit_servers_button = common_ui.PaintedButton(u'Edit...', parent=row)
        self.select_server_combobox = QtWidgets.QComboBox(parent=self)
        self.select_server_combobox.setDuplicatesEnabled(False)
        self.select_server_combobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)

        row.layout().addWidget(self.select_server_combobox, 1)
        row.layout().addWidget(self.edit_servers_button)
        self.server_editor = ServerEditor(parent=self)
        self.server_editor.setHidden(True)
        self.layout().addWidget(self.server_editor)

        row = common_ui.add_row(u'Select job', padding=0, parent=self)
        self.select_job_combobox = QtWidgets.QComboBox(parent=self)
        self.select_job_combobox.setDuplicatesEnabled(False)
        self.select_job_combobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.add_job_button = common_ui.ClickableIconButton(
            u'add',
            (common.ADD, common.ADD),
            self.BUTTON_SIZE,
            description=u'Add a new job to the current server',
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
        row.layout().addWidget(self.add_job_button, 0)
        row.layout().addWidget(self.reveal_job_button, 0)
        self.layout().addStretch(1)

        @QtCore.Slot()
        def toggle_server_editor():
            _bool = not self.server_editor.isHidden()
            self.server_editor.setHidden(_bool)
            self.edit_servers_button.setText(u'Edit...' if _bool else u'Done')
            if _bool:
                self.init_select_server_combobox()

        self.edit_servers_button.clicked.connect(toggle_server_editor)

        @QtCore.Slot()
        def reveal():
            idx = self.select_job_combobox.currentIndex()
            if idx < 0:
                return
            data = self.select_job_combobox.itemData(
                idx, role=QtCore.Qt.UserRole
            )
            common.reveal(data)

        self.reveal_job_button.clicked.connect(reveal)

    def _connectSignals(self):
        self.select_server_combobox.currentIndexChanged.connect(
            self.init_select_job_combobox)

    @QtCore.Slot()
    def init_select_server_combobox(self):
        n = 0
        idx = self.select_server_combobox.currentIndex()

        self.select_server_combobox.clear()
        for k in self.data.get_saved_servers():
            pixmap = ImageCache.get_rsc_pixmap(u'server', common.TEXT, self.ROW_HEIGHT)
            icon = QtGui.QIcon(pixmap)

            self.select_server_combobox.addItem(icon, k.upper(), userData=k)
            item = self.select_server_combobox.model().item(n)
            self.select_server_combobox.setItemData(n, QtCore.QSize(0, self.ROW_HEIGHT), QtCore.Qt.SizeHintRole)
            item.setData(common.TEXT, role=QtCore.Qt.TextColorRole)
            item.setData(common.BACKGROUND, role=QtCore.Qt.BackgroundColorRole)

            if not QtCore.QFileInfo(k).exists():
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)
                item.setData(common.TEXT_DISABLED, role=QtCore.Qt.TextColorRole)
                item.setData(common.SECONDARY_BACKGROUND, role=QtCore.Qt.BackgroundColorRole)
                # item.setData(common.SECONDARY_BACKGROUND, role=QtCore.Qt.BackgroundColorRole)
                _pixmap = ImageCache.get_rsc_pixmap(u'close', common.REMOVE, self.ROW_HEIGHT)
                self.select_server_combobox.setItemIcon(n, QtGui.QIcon(_pixmap))
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

        server = self.select_server_combobox.itemData(idx, role=QtCore.Qt.UserRole)

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

            pixmap = ImageCache.get_rsc_pixmap(u'folder', common.TEXT, self.ROW_HEIGHT)
            icon = QtGui.QIcon(pixmap)

            self.select_job_combobox.addItem(icon, entry.name.upper(), userData=entry.path)
            item = self.select_job_combobox.model().item(n)
            self.select_job_combobox.setItemData(n, QtCore.QSize(0, self.ROW_HEIGHT), QtCore.Qt.SizeHintRole)
            item.setData(common.TEXT, role=QtCore.Qt.TextColorRole)
            item.setData(common.BACKGROUND, role=QtCore.Qt.BackgroundColorRole)

            if not is_valid:
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)
                item.setData(common.TEXT_DISABLED, role=QtCore.Qt.TextColorRole)
                item.setData(common.SECONDARY_BACKGROUND, role=QtCore.Qt.BackgroundColorRole)
                # item.setData(common.SECONDARY_BACKGROUND, role=QtCore.Qt.BackgroundColorRole)
                _pixmap = ImageCache.get_rsc_pixmap(u'close', common.REMOVE, self.ROW_HEIGHT)
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
    widget = BookmarksWidget()
    widget.show()
    app.exec_()
