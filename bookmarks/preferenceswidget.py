"""Application preferences.

Copyright (C) 2020 Gergely Wootsch

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <https://www.gnu.org/licenses/>.

"""
import functools
from PySide2 import QtCore, QtGui, QtWidgets

import bookmarks.settings as settings
import bookmarks.common as common
import bookmarks.defaultpaths as defaultpaths
import bookmarks.common_ui as common_ui
import bookmarks.images as images


def get_sections():
    return (
        {u'name': u'General', u'description': u'General Settings',
            'cls': ApplicationSettingsWidget},
        {u'name': u'Default Paths', u'description': u'Saver Settings',
            u'cls': SaverSettingsWidget},
        {u'name': u'Maya Plugin', u'description': u'Maya Plugin Settings',
            u'cls': MayaSettingsWidget},
    )


def get_preference(name):
    return u'preferences/{}'.format(name)


class BaseSettingsWidget(QtWidgets.QWidget):
    def __init__(self, label, parent=None):
        super(BaseSettingsWidget, self).__init__(parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum,
        )
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN()
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        self._create_UI()
        self._init_values()
        self._connect_signals()

    def _create_UI(self):
        pass

    def _connect_signals(self):
        pass

    def _init_values(self):
        pass


class MayaSettingsWidget(BaseSettingsWidget):
    def __init__(self, parent=None):
        super(MayaSettingsWidget, self).__init__(
            u'Maya Settings', parent=parent)

    def _create_UI(self):
        label = common_ui.PaintedLabel(
            u'Maya Plugin Preferences',
            size=common.LARGE_FONT_SIZE(),
            parent=self,
        )
        self.layout().addWidget(label)

        grp = common_ui.get_group(parent=self)
        row = common_ui.add_row(u'Sync instances', parent=grp)
        self.sync_active_button = QtWidgets.QCheckBox(
            u'Disable instance syncing', parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.sync_active_button)
        label = u'{} instances are syncronised by default. \
For example, when an asset is activated, other instances \
with will also activate the same asset. \
You can turn this behaviour off above.'.format(
            common.PRODUCT)
        common_ui.add_description(label, label=u'Help', parent=grp)
        ######################################################
        grp = common_ui.get_group(parent=self)
        row = common_ui.add_row(u'Alembic Export Path', parent=grp)
        label = u'Edit the Alembic cache export path below. \
Make sure to include the following tokens:\n\n\
{workspace}: The path to the current workspace.\n\
{exports}: The name of the exports folder ("exports" by default).\n\
{set}: The name of the geometry group (eg. "character_rig_geo")\n\n\
There must be a version number present as well (this will be automatically \
incremented when exporting). Eg. v01, v001 or v0001, etc.'
        common_ui.add_description(label, parent=grp)

        self.alembic_export_path = common_ui.add_line_edit(
            u'eg. {workspace}/{exports}/abc/{set}/{set}_v001.abc', parent=row)
        row.layout().addWidget(self.alembic_export_path, 1)

        row = common_ui.add_row(u'Playblast Path', parent=grp)
        self.capture_path = common_ui.add_line_edit(
            u'eg. viewport_captures', parent=row)
        label = u'Edit the relative path of the playblasts (relative to the current project root)'
        common_ui.add_description(label, parent=grp)
        row.layout().addWidget(self.capture_path, 1)

        ######################################################
        grp = common_ui.get_group(parent=self)
        row = common_ui.add_row(u'Workspace warning', parent=grp)
        self.workspace_warning_button = QtWidgets.QCheckBox(
            u'Disable workspace change warnings', parent=grp)
        row.layout().addStretch(1)
        row.layout().addWidget(self.workspace_warning_button)
        label = u'Disable the pop-up warning when the current Workspace is \
changed by {}'.format(common.PRODUCT)
        common_ui.add_description(label, parent=grp)

        row = common_ui.add_row(u'Save warning', parent=grp)
        self.save_warning_button = QtWidgets.QCheckBox(
            u'Don\'t show save warning', parent=grp)
        row.layout().addStretch(1)
        row.layout().addWidget(self.save_warning_button)
        label = u'Saving files outside the current workspace will show a \
warning dialog. Tick to disable (default is "off"):'
        common_ui.add_description(label, parent=grp)
        ######################################################
        grp = common_ui.get_group(parent=self)
        row = common_ui.add_row(u'Sync workspace', parent=grp)
        self.sync_maya_project_button = QtWidgets.QCheckBox(
            u'Disable workspace syncing', parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.sync_maya_project_button)
        label = u'{} sets the current Workspace to the active asset \
        (overriding any Workspace set manually by Maya\'s Set Project). \
        Tick above if you want to disable Maya Workspace Syncing \
        (default is "off"):'.format(common.PRODUCT)
        common_ui.add_description(label, parent=grp)

        self.layout().addStretch(1)

    def _connect_signals(self):
        self.sync_active_button.toggled.connect(
            lambda x: settings.local_settings.setValue(get_preference(u'disable_active_sync'), x))
        self.sync_maya_project_button.toggled.connect(
            lambda x: settings.local_settings.setValue(get_preference(u'disable_workspace_sync'), x))
        self.save_warning_button.toggled.connect(
            lambda x: settings.local_settings.setValue(get_preference(u'disable_save_warnings'), x))
        self.workspace_warning_button.toggled.connect(
            lambda x: settings.local_settings.setValue(get_preference(u'disable_workspace_warnings'), x))

        self.alembic_export_path.textChanged.connect(
            lambda x: settings.local_settings.setValue(get_preference(u'alembic_export_path'), x))
        self.capture_path.textChanged.connect(
            lambda x: settings.local_settings.setValue(get_preference(u'capture_path'), x))

    def _init_values(self):
        val = settings.local_settings.value(
            get_preference(u'disable_active_sync'))
        if val is not None:
            self.sync_active_button.setChecked(val)

        val = settings.local_settings.value(
            get_preference(u'disable_workspace_sync'))
        if val is not None:
            self.sync_maya_project_button.setChecked(val)

        val = settings.local_settings.value(
            get_preference(u'disable_save_warnings'))
        if val is not None:
            self.save_warning_button.setChecked(val)

        val = settings.local_settings.value(
            get_preference(u'disable_workspace_warnings'))
        if val is not None:
            self.workspace_warning_button.setChecked(val)

        val = settings.local_settings.value(
            get_preference(u'alembic_export_path'))
        if val is not None:
            self.alembic_export_path.setText(val)

        val = settings.local_settings.value(
            get_preference(u'capture_path'))
        if val is not None:
            self.capture_path.setText(val)


class ApplicationSettingsWidget(BaseSettingsWidget):

    def __init__(self, parent=None):
        self.check_updates = None
        self.show_help = None
        self.rv_path = None
        self.frameless_window = None

        if common.STANDALONE:
            self.ui_scale = None

        super(ApplicationSettingsWidget, self).__init__(
            u'Settings', parent=parent)

    def _create_UI(self):
        import bookmarks

        label = common_ui.PaintedLabel(
            u'General Preferences',
            size=common.LARGE_FONT_SIZE(),
            parent=self
        )
        self.layout().addWidget(label)
        grp = common_ui.get_group(parent=self)

        row = common_ui.add_row(u'Frameless window', parent=grp)
        self.frameless_window = QtWidgets.QCheckBox(
            u'Use frameless window', parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.frameless_window)
        label = common_ui.PaintedLabel(
            u'(Restart required)',
            size=common.SMALL_FONT_SIZE(),
            color=common.TEXT_DISABLED
        )
        row.layout().addWidget(label, 0)

        if common.STANDALONE:
            row = common_ui.add_row(u'Scale interface', parent=grp)
            self.ui_scale = QtWidgets.QComboBox(parent=self)
            self.ui_scale.setFixedHeight(common.ROW_HEIGHT() * 0.66)

            for s in (u'100%', u'125%', u'150%', u'175%', u'200%'):
                self.ui_scale.addItem(s)
                idx = self.ui_scale.count() - 1
                data = int(s.strip(u'%')) * 0.01
                self.ui_scale.setItemData(idx, data, role=QtCore.Qt.UserRole)
                data = QtCore.QSize(1, common.ROW_HEIGHT() * 0.66)
                self.ui_scale.setItemData(
                    idx, data, role=QtCore.Qt.SizeHintRole)

            row.layout().addWidget(self.ui_scale, 1)
            label = common_ui.PaintedLabel(
                u'(Restart required)',
                size=common.SMALL_FONT_SIZE(),
                color=common.TEXT_DISABLED
            )
            row.layout().addWidget(label, 0)

        ##############################
        row = common_ui.add_row(u'Update', parent=grp)
        self.check_updates = common_ui.PaintedButton(
            u'Check for Updates', parent=row)
        self.show_help = common_ui.PaintedButton(u'Help', parent=row)
        row.layout().addWidget(self.check_updates)
        row.layout().addWidget(self.show_help)
        row.layout().addStretch(1.0)
        #######################################################
        row = common_ui.add_row(None, parent=self)

        label = common_ui.PaintedLabel(
            u'Shotgun RV',
            size=common.LARGE_FONT_SIZE(),
            parent=row
        )
        row.layout().addWidget(label)
        row.layout().addStretch(1)

        grp = common_ui.get_group(parent=self)

        row = common_ui.add_row(u'Path to RV', parent=grp)
        self.rv_path = common_ui.add_line_edit(
            u'eg. c:/rv/bin/rv.exe', parent=row)
        row.layout().addWidget(self.rv_path, 1)

        button = common_ui.PaintedButton(u'Pick')
        button.clicked.connect(self.pick_rv)
        row.layout().addWidget(button)
        button = common_ui.PaintedButton(u'Reveal')
        button.clicked.connect(lambda: common.reveal(self.rv_path.text()))
        row.layout().addWidget(button)

        text = \
            u'You can use {} to push footage to Shotgun RV \
(<span style="color:rgba({});">CTRL+P)</span>. Select the RV executable for this to work.'.format(
                common.PRODUCT, common.rgb(common.ADD))
        common_ui.add_description(text, label=u'Hint', parent=grp)

        #######################################################

        label = common_ui.PaintedLabel(
            u'Shortcuts', size=common.LARGE_FONT_SIZE(), parent=self)
        self.layout().addWidget(label)

        grp = common_ui.get_group(parent=self)

        label = QtWidgets.QLabel(parent=self)
        s = u'<table width="100%">'
        def r(): return unicode(
            '<tr>\
    <td align="center" style="background-color:rgba(0,0,0,80);padding:{pad}px;">\
        <span style="color:rgba({ADD});">{shortcut}</span>\
    </td>\
    <td align="left" style="background-color:rgba(0,0,0,30);padding:{pad}px;">\
        <span style="color:rgba({TEXT});">{description}</span>\
    </td>\
</tr>'
        )
        for shortcut, description in (
            (u'Ctrl+N', u'Open new {} instance'.format(common.PRODUCT)),
            (u'Enter', u'Activate item'),
            (u'Space', u'Preview thumbnail'),
            (u'Arrow Up/Down', u'Navigate list'),
            (u'Ctrl+R', u'Reload'),
            (u'Ctrl+F', u'Edit filter'),
            (u'Ctrl+O', u'Reveal in file manager'),
            (u'Ctrl+C', u'Copy path'),
            (u'Ctrl+Shift+C', u'Copy path (alt)'),
            (u'Ctrl+S', u'Save/remove favourite'),
            (u'Ctrl+A', u'Archive/enable'),
            (u'Ctrl+T', u'Show Notes & Todos'),
            (u'Ctrl+H', u'Hide buttons'),
            (u'Ctrl+M', u'Toggle thumbnail loading'),
            (u'Ctrl+Shift+A', u'Show/Hide archived items'),
            (u'Ctrl+Shift+F', u'Show favourites only/Show all'),
            (u'Tab', u'Edit item description'),
            (u'Shift+Tab', u'Edit item description'),
            (u'Alt+Left', u'Show previous tab'),
            (u'Alt+Right', u'Show next tab'),
            (u'Ctrl+1', u'Show bookmarks'),
            (u'Ctrl+2', u'Show assets'),
            (u'Ctrl+3', u'Show files'),
            (u'Ctrl+4', u'Show favourites'),
            (u'Ctrl+Plus', u'Increase row height'),
            (u'Ctrl+Minus', u'Decrease row height'),
            (u'Ctrl+0', u'Reset row height'),
        ):
            s += r().format(
                shortcut=shortcut,
                description=description,
                pad=int(common.INDICATOR_WIDTH() * 1.5),
                ADD=common.rgb(common.ADD),
                TEXT=common.rgb(common.SECONDARY_TEXT),
            )
        s += u'</table>'
        label.setText(s)
        label.setWordWrap(True)
        grp.layout().addWidget(label)

        label = common_ui.PaintedLabel(
            u'About {}'.format(common.PRODUCT),
            size=common.LARGE_FONT_SIZE(),
            parent=grp
        )
        self.layout().addWidget(label)
        grp = common_ui.get_group(parent=self)
        o = common.MARGIN()
        grp.layout().setContentsMargins(o, o, o, o)
        # row = common_ui.add_row(u'Version', parent=grp, height=None)
        s = u'\n'.join(bookmarks.get_info())
        common_ui.add_description(s, label=None, parent=grp)

        self.layout().addStretch(1)

    def _connect_signals(self):
        import bookmarks.versioncontrol.versioncontrol as vc
        self.check_updates.clicked.connect(vc.check)
        self.show_help.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(common.ABOUT_URL))

        self.frameless_window.toggled.connect(
            lambda x: settings.local_settings.setValue(get_preference(u'frameless_window'), x))

        if common.STANDALONE:

            @QtCore.Slot(int)
            def save_ui_scale(x):
                v = self.ui_scale.itemData(x)
                settings.local_settings.setValue(
                    get_preference(u'ui_scale'), v)

            self.ui_scale.activated.connect(save_ui_scale)

        self.rv_path.textChanged.connect(self.set_rv_path)

    def _init_values(self):
        val = settings.local_settings.value(
            get_preference(u'frameless_window'))
        val = val if not None else False
        if val is not None:
            self.frameless_window.setChecked(val)

        if common.STANDALONE:
            val = settings.local_settings.value(get_preference(u'ui_scale'))
            val = val if not None else 1.0
            if val is not None:
                idx = self.ui_scale.findData(val)
                if idx != -1:
                    self.ui_scale.setCurrentIndex(idx)

        rv_path = settings.local_settings.value(get_preference(u'rv_path'))
        val = rv_path if rv_path else None
        self.rv_path.setText(val)
        file_info = QtCore.QFileInfo(val)
        if file_info.exists():
            self.rv_path.setStyleSheet(
                u'color: rgba({})'.format(common.rgb(common.ADD)))

    @QtCore.Slot()
    def pick_rv(self):
        if common.get_platform() == u'win':
            res = QtWidgets.QFileDialog.getOpenFileName(
                caption=u'Select RV.exe',
                filter=u'rv.exe',
                dir=u'/'
            )
            path, _ = res
            if path:
                self.rv_path.setText(path)
        if common.get_platform() == u'mac':
            res = QtWidgets.QFileDialog.getOpenFileName(
                caption=u'Select RV',
                filter=u'*.*',
                dir=u'/'
            )
            path, _ = res
            if path:
                self.rv_path.setText(path)

    @QtCore.Slot(unicode)
    def set_rv_path(self, val):
        settings.local_settings.setValue(get_preference(u'rv_path'), val)
        file_info = QtCore.QFileInfo(val)
        if file_info.exists():
            self.rv_path.setStyleSheet(
                u'color: rgba({})'.format(common.rgb(common.ADD)))
        else:
            self.rv_path.setStyleSheet(
                u'color: rgba({})'.format(common.rgb(common.REMOVE)))


class SaverSettingsWidget(BaseSettingsWidget):

    def __init__(self, parent=None):
        self.check_updates = None
        self.show_help = None
        self.rv_path = None
        self.frameless_window = None

        if common.STANDALONE:
            self.ui_scale = None

        super(SaverSettingsWidget, self).__init__(
            u'Settings', parent=parent)

    def _create_UI(self):
        @QtCore.Slot()
        def text_changed(*args):
            defaultpaths.save_value(*args)

        def add_section(label, description, data):
            """Utility method for creating the layout needed to edit default paths."""
            height = common.ROW_HEIGHT() * 0.8
            o = common.MARGIN()

            grp = common_ui.get_group(parent=self)
            grp.layout().setContentsMargins(o, o, o, o)
            grp.layout().setSpacing(0)

            label = common_ui.PaintedLabel(
                label,
                size=common.LARGE_FONT_SIZE(),
                parent=self
            )
            grp.layout().addWidget(label)
            grp.layout().addSpacing(o)

            if description:
                common_ui.add_description(description, label=None, parent=grp)
                grp.layout().addSpacing(o)

            scroll_area = QtWidgets.QScrollArea(parent=self)
            scroll_area.setWidgetResizable(True)
            scroll_area.setMaximumHeight(common.HEIGHT() * 0.66)
            scroll_area.setAttribute(QtCore.Qt.WA_NoBackground)
            scroll_area.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            grp.layout().addWidget(scroll_area)

            _row = common_ui.add_row(
                None, vertical=True, padding=None, height=None, parent=grp)
            _row.layout().setContentsMargins(0, 0, 0, 0)
            _row.layout().setSpacing(0)
            scroll_area.setWidget(_row)

            for k, v in sorted(data.items()):
                label = u'<span style="color:rgba({ADD});">{k}</span> - {v}:'.format(
                    ADD=common.rgb(common.ADD),
                    k=k.upper(),
                    v=v[u'description']
                )
                row = common_ui.add_row(
                    None, padding=None, height=height, parent=_row)
                common_ui.add_description(label, label=u'', parent=row)
                row = common_ui.add_row(
                    None, padding=None, height=height, parent=_row)
                line_edit = common_ui.add_line_edit(v[u'default'], parent=row)
                line_edit.setAlignment(QtCore.Qt.AlignLeft)
                line_edit.setText(v[u'value'])
                line_edit.textChanged.connect(
                    functools.partial(text_changed, data, k))

        def add_name_template():
            height = common.ROW_HEIGHT() * 0.8
            o = common.MARGIN()

            grp = common_ui.get_group(parent=self)
            grp.layout().setContentsMargins(o, o, o, o)
            grp.layout().setSpacing(0)

            label = common_ui.PaintedLabel(
                u'Name template',
                size=common.LARGE_FONT_SIZE(),
                parent=grp
            )
            grp.layout().addWidget(label)
            grp.layout().addSpacing(o)

            label = u'<span style="color:rgba({ADD});">File name pattern</span> - {v}:'.format(
                ADD=common.rgb(common.ADD),
                v=u'The template used to generate new file names'
            )
            row = common_ui.add_row(
                None, padding=None, height=height, parent=grp)
            common_ui.add_description(label, label=u'', parent=row)
            row = common_ui.add_row(
                None, padding=None, height=height, parent=grp)
            line_edit = common_ui.add_line_edit(
                defaultpaths.FILE_NAME_PATTERN, parent=row)
            line_edit.textChanged.connect(
                functools.partial(text_changed, defaultpaths.FILE_NAME_PATTERN, u'defaultpaths/filenamepattern'))
            line_edit.setAlignment(QtCore.Qt.AlignLeft)
            line_edit.setText(defaultpaths.FILE_NAME_PATTERN)

            s = \
                u'Available tokens<br><br>\
<span style="color:rgba({ADD});">{{folder}}</span>  -  The destination folder<br>\
<span style="color:rgba({ADD});">{{prefix}}</span>  -  Prefix defined by the bookmark<br>\
<span style="color:rgba({ADD});">{{asset}}</span>   -  Asset name<br>\
<span style="color:rgba({ADD});">{{mode}}</span>    -  Selected mode (see below)<br>\
<span style="color:rgba({ADD});">{{user}}</span>    -  Name of the current user<br>\
<span style="color:rgba({ADD});">{{version}}</span> -  Version number<br>\
<span style="color:rgba({ADD});">{{ext}}</span>     -  File extension'.format(
                    ADD=common.rgb(common.ADD),
                    v=u'The template used to generate new file names'
                )
            grp.layout().addSpacing(o)
            common_ui.add_description(s, label='', parent=grp)

        def add_extensions():
            height = common.ROW_HEIGHT() * 0.8
            o = common.MARGIN()

            grp = common_ui.get_group(parent=self)
            grp.layout().setContentsMargins(o, o, o, o)
            grp.layout().setSpacing(0)

            description = \
                u'Edit the list of valid extensions. Use \
    <span style="color:rgba({ADD});">*</span> to allow all files.'.format(
                    p=common.PRODUCT,
                    ADD=common.rgb(common.ADD))

            label = common_ui.PaintedLabel(
                u'Default extension filters',
                size=common.LARGE_FONT_SIZE(),
                parent=self
            )
            grp.layout().addWidget(label)
            grp.layout().addSpacing(o)

            if description:
                common_ui.add_description(description, label=None, parent=grp)
                grp.layout().addSpacing(o)

            scroll_area = QtWidgets.QScrollArea(parent=self)
            scroll_area.setWidgetResizable(True)
            scroll_area.setMaximumHeight(common.HEIGHT() * 0.66)
            scroll_area.setAttribute(QtCore.Qt.WA_NoBackground)
            scroll_area.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            grp.layout().addWidget(scroll_area)

            _row = common_ui.add_row(
                None, vertical=True, padding=None, height=None, parent=grp)
            _row.layout().setContentsMargins(0, 0, 0, 0)
            _row.layout().setSpacing(0)
            scroll_area.setWidget(_row)

            for k, v in sorted(defaultpaths.FORMAT_FILTERS.items(), key=lambda x: x[0]):
                label = u'<span style="color:rgba({ADD});">{k}</span> - {v}:'.format(
                    ADD=common.rgb(common.ADD),
                    k=v[u'name'],
                    v=v[u'description']
                )
                row = common_ui.add_row(
                    None, padding=None, height=height, parent=_row)
                common_ui.add_description(label, label=u'', parent=row)
                row = common_ui.add_row(
                    None, padding=None, height=height, parent=_row)
                line_edit = common_ui.add_line_edit(v[u'default'], parent=row)
                line_edit.textChanged.connect(
                    functools.partial(text_changed, defaultpaths.FORMAT_FILTERS, k))
                line_edit.setAlignment(QtCore.Qt.AlignLeft)
                line_edit.setText(v[u'value'])

        description = \
            u'A <span style="color:rgba({ADD});">task folder</span> is any folder \
located in the root of the asset. The folders usually correspond to different \
stages of the asset\'s production cycle and used to categorise CG content.'.format(
                p=common.PRODUCT,
                ADD=common.rgb(common.ADD))
        add_section(u'Default task folder names',
                    description, defaultpaths.TASK_FOLDERS)

        description = \
            u'Edit the default mode names. When saving files {p} can suggest paths \
depending on the selected <span style="color:rgba({ADD});">mode</span>.\
<br><br>See below for the available modes - by default each located in the \
<span style="color:rgba({ADD});">scene</span> task folder \
(paths are relative to the asset\'s root folder).'.format(
                p=common.PRODUCT,
                ADD=common.rgb(common.ADD))
        add_section(u'Default scene paths', description,
                    defaultpaths.SCENE_FOLDERS)

        description = \
            u'Customize the export folder used by DCCs when exporting caches.'.format(
                p=common.PRODUCT,
                ADD=common.rgb(common.ADD))
        add_section(u'Default export paths', description,
                    defaultpaths.EXPORT_FOLDERS)

        add_name_template()
        add_extensions()

    def _connect_signals(self):
        pass

    def _init_values(self):
        pass


class SectionSwitcherWidget(QtWidgets.QListWidget):
    """Widget responsible for selecting the preferences sections."""

    def __init__(self, parent=None):
        super(SectionSwitcherWidget, self).__init__(parent=parent)
        self._connect_signals()
        self.setMaximumWidth(common.MARGIN() * 7.5)

    def _connect_signals(self):
        self.selectionModel().currentChanged.connect(self.save_settings)

    def showEvent(self, event):
        self.init_settings()

    def init_settings(self):
        val = settings.local_settings.value(u'preferences/current_section')
        if not val:
            self.setCurrentRow(0)
            return
        self.setCurrentRow(val)

    def save_settings(self, index):
        """Saves the current row selection to the local settings."""
        if not index.isValid():
            return
        settings.local_settings.setValue(
            u'preferences/current_section', index.row())


class SectionsStackWidget(QtWidgets.QStackedWidget):

    def __init__(self, parent=None):
        super(SectionsStackWidget, self).__init__(parent=parent)


class PreferencesWidget(QtWidgets.QDialog):
    """The main preferences widget."""

    def __init__(self, parent=None):
        super(PreferencesWidget, self).__init__(parent=parent)
        if not parent:
            common.set_custom_stylesheet(self)
        self.sections_list_widget = None
        self.sections_stack_widget = None
        self.setWindowTitle(u'Preferences')
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoBackground)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(QtCore.Qt.Widget)

        self._create_UI()
        self._add_sections()
        self._connect_signals()

    def _create_UI(self):
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN()
        self.layout().setContentsMargins(o, o * 0.5, o, o)
        self.layout().setSpacing(0)

        row = common_ui.add_row(None, padding=None, parent=self)
        self.hide_button = common_ui.ClickableIconButton(
            u'close',
            (common.REMOVE, common.REMOVE),
            common.ROW_HEIGHT() * 0.6
        )
        label = common_ui.PaintedLabel(
            u'Preferences', size=common.LARGE_FONT_SIZE())
        row.layout().addWidget(label, 0)
        row.layout().addStretch(1)
        row.layout().addWidget(self.hide_button, 0)
        self.hide_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected))

        splitter = QtWidgets.QSplitter(parent=self)
        self.layout().addWidget(splitter)

        self.sections_list_widget = SectionSwitcherWidget(parent=self)
        splitter.addWidget(self.sections_list_widget)

        scroll_area = QtWidgets.QScrollArea(parent=self)
        scroll_area.setWidgetResizable(True)
        splitter.addWidget(scroll_area)

        self.sections_stack_widget = SectionsStackWidget(parent=self)
        scroll_area.setWidget(self.sections_stack_widget)

    def _add_sections(self):
        """Adds the sections defined in the ``SECTIONS`` variable."""
        for s in get_sections():
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole,
                         u'  {}'.format(s[u'name'].title()))
            item.setData(common.DescriptionRole, s[u'description'])
            item.setData(QtCore.Qt.StatusTipRole, s[u'description'])
            item.setData(QtCore.Qt.ToolTipRole, s[u'description'])
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                0, common.ROW_HEIGHT() * 0.66))
            self.sections_list_widget.addItem(item)
            self.sections_stack_widget.addWidget(s[u'cls'](parent=self))

    def _connect_signals(self):
        self.sections_list_widget.selectionModel(
        ).currentChanged.connect(self.current_changed)

    @QtCore.Slot(QtCore.QModelIndex)
    def current_changed(self, index):
        if not index.isValid():
            return
        self.sections_stack_widget.setCurrentIndex(index.row())

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        pen = QtGui.QPen(common.SEPARATOR)
        pen.setWidthF(common.ROW_SEPARATOR())
        painter.setBrush(common.BACKGROUND)
        painter.setPen(pen)
        o = common.MARGIN() * 0.4
        rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
        painter.drawRoundedRect(
            rect, common.INDICATOR_WIDTH(), common.INDICATOR_WIDTH())
        painter.end()

    def showEvent(self, event):
        if self.parent():
            self.resize(self.parent().viewport().rect().size())


if __name__ == '__main__':
    import bookmarks.standalone as standalone
    app = standalone.StandaloneApp([])
    w = PreferencesWidget()
    w.show()
    app.exec_()
