"""The module contains the definition of `FilePropertiesWidget`, the main
widget used by Bookmarks to save files.

The suggested save destination will be partially dependent on the extension
selected, the current asset config values as well as the current bookmark and
assets.

File Name
---------

    The editor widgets defined in `file_properties.widget.py` are used to edit
    values needed to expand the tokens of in the file name
    templates. See the `asset_config.py` and `bookmark_properties_widget.py`
    modules for more information.


Example
-------

    code_block:: python

            editor = FilePropertiesWidget(
                server,
                job,
                root,
                asset=asset,
                extension=u'fbx'
            ).open()

"""
import os
import functools
import _scandir

from PySide2 import QtWidgets, QtGui, QtCore

from .. import common_ui
from .. import common
from .. import settings
from .. import bookmark_db
from .. import log
from .. import actions

from . import base
from . import asset_config
from . import file_properties_widgets


instance = None


def close():
    global instance
    if instance is None:
        return
    instance.close()
    instance.deleteLater()
    instance = None


def show(server, job, root, asset, extension=None, file=None):
    global instance

    close()
    instance = FilePropertiesWidget(
        server,
        job,
        root,
        asset,
        extension=extension,
        file=file
    )
    instance.open()
    return instance


LOCAL_KEYS = (
    u'folder',
    u'element',
    u'version',
    u'extension',
    u'user',
    u'template'
)

INACTIVE_KEYS = (
    u'bookmark',
    u'asset',
    u'folder',
    u'prefix',
    u'element',
    u'version',
    u'extension',
    u'user',
    u'template',
)


SECTIONS = {
    0: {
        'name': u'Save File',
        'icon': u'',
        'color': common.SECONDARY_BACKGROUND,
        'groups': {
            0: {
                0: {
                    'name': u'Bookmark',
                    'key': u'bookmark',
                    'validator': None,
                    'widget': file_properties_widgets.BookmarkComboBox,
                    'placeholder': None,
                    'description': u'The job\'s name, eg. \'MY_NEW_JOB\'.',
                },
                1: {
                    'name': u'Asset',
                    'key': u'asset',
                    'validator': None,
                    'widget': file_properties_widgets.AssetComboBox,
                    'placeholder': None,
                    'description': u'The job\'s name, eg. \'MY_NEW_JOB\'.',
                },
                2: {
                    'name': u'Task',
                    'key': u'folder',
                    'validator': None,
                    'widget': file_properties_widgets.TaskComboBox,
                    'placeholder': None,
                    'description': u'The job\'s name, eg. \'MY_NEW_JOB\'.',
                    'button': 'Pick'
                },
            },
            1: {
                0: {
                    'name': u'Description',
                    'key': 'description',
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'A short description, eg. \'My animation re-take\'',
                    'description': u'A short description of the file\'s contents.\nIndicate significant changes and notes here.',
                },
            },
            2: {
                0: {
                    'name': u'Prefix',
                    'key': 'prefix',
                    'validator': base.textvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Prefix not yet set!',
                    'description': u'A short prefix used to identify the job eg.\'MYB\'.',
                    'button': u'Edit'
                },
                1: {
                    'name': u'Element',
                    'key': 'element',
                    'validator': base.textvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Element being saved, eg. \'Tower\'',
                    'description': u'The name of the element being saved. Eg., \'ForegroundTower\', or \'Precomp\'',
                },
                2: {
                    'name': u'Version',
                    'key': 'version',
                    'validator': base.versionvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'A version number, eg. \'v001\'',
                    'description': u'A version number with, or without, a preceeding \'v\'. Eg. \'v001\'.',
                    'button': u'+',
                    'button2': u'-',
                },
                3: {
                    'name': u'User',
                    'key': 'user',
                    'validator': base.textvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Your name, eg. \'JohnDoe\'',
                    'description': u'The name of the current user, eg. \'JohnDoe\', or \'JD\'',
                },
                4: {
                    'name': u'Format',
                    'key': 'extension',
                    'validator': None,
                    'widget': file_properties_widgets.ExtensionComboBox,
                    'placeholder': u'File extension, eg. \'exr\'',
                    'description': u'A file extension, without the leading dot. Eg. \'ma\'',
                },
            },
            3: {
                0: {
                    'name': u'Template',
                    'key': 'template',
                    'validator': base.textvalidator,
                    'widget': file_properties_widgets.TemplateComboBox,
                    'placeholder': u'Custom prefix, eg. \'MYB\'',
                    'description': u'A short name of the bookmark (or job) used when saving files.\n\nEg. \'MYB_sh0010_anim_v001.ma\' where \'MYB\' is the prefix specified here.',
                    'button': u'Edit'
                },
                1: {
                    'name': u' ',
                    'key': u'filename',
                    'validator': None,
                    'widget': QtWidgets.QLabel,
                    # 'widget': common_ui.LineEdit,
                    'placeholder': u'Invalid file name...',
                    'description': u'The file name, based on the current template.',
                    'button': 'Reveal'
                },
            },
        },
    },
}



class FilePropertiesWidget(base.PropertiesWidget):
    """The widget used to create file name template compliant files.

    """
    def __init__(self, server, job, root, asset, extension=None, file=None, parent=None):
        super(FilePropertiesWidget, self).__init__(
            SECTIONS,
            server,
            job,
            root,
            asset=asset,
            alignment=QtCore.Qt.AlignLeft,
            fallback_thumb=u'file',
            db_table=bookmark_db.AssetTable,
            parent=parent
        )

        self._file = file
        self._extension = extension
        self._filelist = {}


        if self._file is not None:
            self.set_file()
            return

        self.update_timer = QtCore.QTimer(parent=self)
        self.update_timer.setInterval(250)
        self.update_timer.setSingleShot(False)
        self.update_timer.timeout.connect(self.set_name)
        self.update_timer.timeout.connect(self.set_source)
        self.update_timer.timeout.connect(self.verify_unique)

        if settings.ACTIVE[settings.TaskKey] is not None:
            self.add_task(settings.ACTIVE[settings.TaskKey])

    def set_file(self):
        self.thumbnail_editor.source = self._file
        self.thumbnail_editor.update()

        for k in INACTIVE_KEYS:
            if not hasattr(self, k + '_editor'):
                continue
            editor = getattr(self, k + '_editor')
            editor.parent().setDisabled(True)

        self.filename_editor.setText(QtCore.QFileInfo(self._file).fileName())

    def _connect(self, k):
        if not hasattr(self, k + '_editor'):
            return
        editor = getattr(self, k + '_editor')
        if hasattr(editor, 'currentTextChanged'):
            signal = getattr(editor, 'currentTextChanged')
        elif hasattr(editor, 'textChanged'):
            signal = getattr(editor, 'textChanged')
        else:
            return
        signal.connect(functools.partial(self.save_local_value, k))

    def _connect_signals(self):
        super(FilePropertiesWidget, self)._connect_signals()

        for k in LOCAL_KEYS:
            self._connect(k)

    def name(self):
        return self.filename_editor.text()

    @QtCore.Slot()
    def set_source(self):
        """Slot connected to the update timer and used to set the source value
        of the thumbnail editor.

        """
        source = self.thumbnail_editor.source
        _source = self.db_source()

        self.thumbnail_editor.source = _source
        if source != _source:
            self.thumbnail_editor.update()

    @QtCore.Slot()
    def set_name(self):
        """Slot connected to the update timer used to preview the current
        file name.

        """
        bookmark = u'/'.join((self.server, self.job, self.root))
        asset_root = u'/'.join((self.server, self.job, self.root, self.asset))

        template = self.template_editor.currentData(QtCore.Qt.UserRole)
        config = asset_config.get(self.server, self.job, self.root)

        def _strip(s):
            return (
                s.
                strip(u'-').
                strip(u'_').
                strip().
                replace(u'__', u'_').
                replace(u'_.', u'.')
            )

        def _get(k):
            if not hasattr(self, k + '_editor'):
                return u''
            editor = getattr(self, k + '_editor')
            if hasattr(editor, 'currentText'):
                v = editor.currentText()
            elif hasattr(editor, 'text'):
                v = editor.text()
            else:
                v = u''

            return _strip(v)

        v = config.expand_tokens(
            template,
            asset_root=asset_root,
            bookmark=bookmark,
            asset=_get('asset'),
            user=_get('user'),
            version=_get('version').lower(),
            task=_get('folder'),
            mode=_get('folder'),
            element=_get('element'),
            ext=_get('extension').lower()
        )
        v = _strip(v)
        v = v.replace(
            u'{invalid_token}', u'<span style="color:rgba({})">{{invalid_token}}</span>'.format(common.rgb(common.REMOVE)))

        self.filename_editor.setText(v)

    @QtCore.Slot()
    def verify_unique(self):
        """Checks if the proposed file name exists already, and if does,
        makes the output file name red.

        """
        if self.db_source() not in self._filelist:
            file_info = QtCore.QFileInfo(self.db_source())
            self._filelist[self.db_source()] = file_info.exists()

        if self._filelist[self.db_source()]:
            self.filename_editor.setStyleSheet(
                u'color:rgba({});'.format(common.rgb(common.REMOVE)))
        else:
            self.filename_editor.setStyleSheet(
                u'color:rgba({});'.format(common.rgb(common.ADD)))

    def parent_folder(self):
        """The folder where the new file is about to be saved.

        """
        folder = self.folder_editor.currentData(QtCore.Qt.UserRole)
        if not folder:
            return None
        return u'/'.join((self.server, self.job, self.root, self.asset, folder))

    def db_source(self):
        """The final file path."""
        if self._file is not None:
            return common.proxy_path(self._file)

        if not self.parent_folder():
            return None
        return self.parent_folder() + u'/' + self.name()

    def _set_local_value(self, k):
        v = settings.local_settings.value(
            settings.CurrentUserPicksSection,
            k
        )
        if not isinstance(v, unicode):
            return
        if not v:
            return
        if not hasattr(self, k + '_editor'):
            return
        editor = getattr(self, k + '_editor')
        if hasattr(editor, 'setCurrentText'):
            editor.blockSignals(True)
            editor.setCurrentText(v)
            editor.blockSignals(False)
        elif hasattr(editor, u'setText'):
            editor.blockSignals(True)
            editor.setText(v)
            editor.blockSignals(False)
        else:
            return

    @common.error
    @common.debug
    def init_data(self):
        """Initialises the default values of each editor.

        Some values are retrieved by the context the widget was called, and some
        are loaded from `local_settings` if the user has set a custom value
        previously.

        """
        if all((self.server, self.job, self.root)):
            bookmark = u'/'.join((self.server, self.job, self.root))
            self.bookmark_editor.setCurrentText(bookmark)
        if self.asset:
            self.asset_editor.setCurrentText(self.asset)

        self.user_editor.blockSignals(True)
        if self._file is not None:
            self.user_editor.setText(u'-')
        else:
            self.user_editor.setText(common.get_username())
        self.user_editor.blockSignals(False)

        if self._file is None:
            for k in LOCAL_KEYS:
                self._set_local_value(k)

        # Prefix
        self.prefix_editor.setReadOnly(True)
        if self._file is None:
            with bookmark_db.transactions(self.server, self.job, self.root) as db:
                prefix = db.value(
                    db.source(),
                    u'prefix',
                    table=bookmark_db.BookmarkTable
                )
            if prefix:
                self.prefix_editor.setText(prefix)

        if self._extension and self._file is None:
            self.extension_editor.setCurrentText(self._extension.upper())
            self.extension_editor.setDisabled(True)
            self.update_tasks(self._extension)

            if self.folder_editor.findText(self._extension.upper()) > 0:
                self.folder_editor.blockSignals(True)
                self.folder_editor.setCurrentText(self._extension.upper())
                self.folder_editor.blockSignals(False)

        # Description
        if self._file is not None:
            with bookmark_db.transactions(self.server, self.job, self.root) as db:
                v = db.value(
                    self.db_source(),
                    u'description',
                    table=bookmark_db.AssetTable
                )
            v = v if v else u''
            self.description_editor.setText(v)
            self.description_editor.setFocus()
            return

        # Increment the version if the source already exists
        self.set_name()
        if QtCore.QFileInfo(self.db_source()).exists():
            self._increment_version(max, 1)

        self.update_timer.start()

    @QtCore.Slot(unicode)
    def update_tasks(self, ext):
        """Update the available task folder options based on the given file extension."""
        ext = ext.lower()
        config = asset_config.get(self.server, self.job, self.root)
        if ext in config.get_extensions(asset_config.CacheFormat):
            self.folder_editor.set_mode(file_properties_widgets.CacheMode)
        elif ext in config.get_extensions(asset_config.SceneFormat):
            self.folder_editor.set_mode(file_properties_widgets.SceneMode)
        else:
            self.folder_editor.set_mode(file_properties_widgets.NoMode)

    def save_changes(self):
        """Creates a new empty file or updates and existing item.

        """
        if self._file is None:
            try:
                if not self.create_file():
                    return False
            except:
                s = u'Could not create file.'
                log.error(s)
                common_ui.ErrorBox('Error', s).open()
                return False

        try:
            self._save_db_data()
            v = self.description_editor.text()
            self.valueUpdated.emit(self.db_source(), common.DescriptionRole, v)
        except:
            s = u'Could not save properties to the database.'
            log.error(s)
            common_ui.ErrorBox('Error', s).open()
            return False

        try:
            self.thumbnail_editor.save_image()
            self.thumbnailUpdated.emit(self.db_source())
        except:
            s = u'Failed to save the thumbnail.'
            log.error(s)
            common_ui.ErrorBox('Error', s).open()
            return False

        self.itemUpdated.emit(self.db_source())
        return True

    def create_file(self):
        """Creates a new file on the disk.

        """
        if not self.parent_folder():
            return False
        _dir = self.parent_folder()

        name = self.name()
        if not name or not _dir or u'{invalid_token}' in name:
            common_ui.ErrorBox(
                u'Could not save the file',
                u'Looks like the output name is invalid.'
            ).open()
            return False

        _dir = QtCore.QDir(_dir)
        if not _dir.mkpath(u'.'):
            common_ui.ErrorBox(
                u'Error saving file',
                u'Could not create a missing folder.'
            ).open()
            return False

        file_info = QtCore.QFileInfo(self.db_source())
        if file_info.exists():
            common_ui.ErrorBox(
                u'File already exists.',
                u'{} already exists. Try incrementing the version number.'.format(
                    name)
            ).open()
            return False

        _path = file_info.absoluteFilePath()
        path = os.path.normpath(_path)
        try:
            open(path, 'a').close()
        except:
            common_ui.ErrorBox(
                u'Error saving the file.',
                u'Could not create the file.'
            ).open()
            return False

        self.itemCreated.emit(_path)
        return True

    def save_local_value(self, key, value):
        settings.local_settings.setValue(
            settings.CurrentUserPicksSection,
            key,
            value
        )

    @QtCore.Slot()
    def folder_button_clicked(self):
        """Lets the user select a custom save destination.

        The selection has to be inside the currently seleted asset, otherwise
        will be rejected. If the folder is not part of the current available
        options, it will be added as a new option.

        """
        source = u'/'.join((self.server, self.job, self.root, self.asset))
        _dir = QtWidgets.QFileDialog.getExistingDirectory(
            parent=self,
            caption=u'Select a folder...',
            dir=source,
            options=QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks | QtWidgets.QFileDialog.DontUseCustomDirectoryIcons
        )
        if not _dir:
            return

        if source not in _dir:
            common_ui.ErrorBox(
                u'Invalid selection',
                u'Make sure to select a folder inside the current asset.'
            ).open()
            return

        relative_path = _dir.replace(source, u'').strip(u'/')
        self.add_task(relative_path)

    def add_task(self, relative_path):
        """Adds a task folder to the folder editor.

        """
        for n in xrange(self.folder_editor.count()):
            v = self.folder_editor.itemData(n, role=QtCore.Qt.UserRole)
            if v == relative_path:
                self.folder_editor.setCurrentIndex(n)
                return

        self.folder_editor.model().add_item(relative_path)
        self.folder_editor.blockSignals(True)
        self.folder_editor.setCurrentIndex(self.folder_editor.count() - 1)
        self.folder_editor.blockSignals(False)

    @QtCore.Slot()
    def filename_button_clicked(self):
        """Used to reveal the parent folder in the file explorer.

        """
        if self._file is not None:
            actions.reveal(self._file)
            return

        if not self.parent_folder():
            return

        _dir = QtCore.QDir(self.parent_folder())

        if not _dir.exists():
            mbox = QtWidgets.QMessageBox(parent=self)
            mbox.setWindowTitle(u'Folder does not yet exist')
            mbox.setIcon(QtWidgets.QMessageBox.Warning)
            mbox.setText(u'Destination folder does not exist.')
            mbox.setInformativeText(
                u'The destination folder does not yet exist. Do you want to create it now?')
            button = mbox.addButton(
                u'Create folder', QtWidgets.QMessageBox.AcceptRole)
            mbox.setDefaultButton(button)
            mbox.addButton(u'Cancel', QtWidgets.QMessageBox.RejectRole)

            if mbox.exec_() == QtWidgets.QMessageBox.RejectRole:
                return
            if not _dir.mkpath(u'.'):
                common_ui.ErrorBox(
                    u'Could not create destination folder.').open()
                return

        actions.reveal(_dir.path())

    @QtCore.Slot()
    def prefix_button_clicked(self):
        editor = file_properties_widgets.PrefixEditor(parent=self)
        editor.open()

    @QtCore.Slot()
    def version_button_clicked(self):
        """Increments the version number by one.

        """
        self._increment_version(max, 1)

    @QtCore.Slot()
    def version_button2_clicked(self):
        """Decrements the version number by one.

        """
        self._increment_version(min, -1)

    def _increment_version(self, func, increment):
        """Increments the version number by one or to the smallest/largest
        available version number based on existing files found in the
        destination folder.

        """
        v = self.version_editor.text()
        if not v:
            v = u'v001'
            self.version_editor.setText(v)

        prefix = u'v' if v.startswith(u'v') else u''
        padding = len(v.replace(u'v', u''))
        try:
            n = int(v.replace(u'v', u''))
        except ValueError:
            log.error('Error.')
            return
        if not self.parent_folder():
            return
        _dir = QtCore.QDir(self.parent_folder())

        if not _dir.exists():
            n += increment
            if n < 0 or n > 999:
                return
            _v = u'{}{}'.format(prefix, u'{}'.format(n).zfill(padding))
            self.version_editor.setText(_v)
            return

        # Let's scan the destination directory for existing versions to make
        # sure we're suggesting a valid version number
        name = self.name()

        if v not in name:
            return
        idx = name.index(v)

        _arr = []
        for entry in _scandir.scandir(_dir.path()):
            if len(name) != len(entry.name):
                continue
            if name[:idx] != entry.name[:idx]:
                continue

            _v = entry.name[idx:idx + len(v)]

            _prefix = u'v' if _v.startswith(u'v') else u''
            _padding = len(_v.replace(u'v', u''))
            try:
                _n = int(_v.replace(u'v', u''))
            except ValueError:
                continue
            _arr.append(_n)

        if not _arr:
            n += increment
            if n < 0 or n > 999:
                return
            v = u'{}{}'.format(prefix, u'{}'.format(n).zfill(padding))
            self.version_editor.setText(v)
            return

        _n = func(_arr)
        _n += increment

        if func == max and _n <= n:
            _n = n + increment
        if func == min and _n >= n:
            _n = n + increment
        if _n < 0 or _n > 999:
            return

        v = u'{}{}'.format(_prefix, u'{}'.format(_n).zfill(_padding))
        self.version_editor.setText(v)
