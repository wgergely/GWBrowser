"""Preferences"""

from PySide2 import QtCore, QtGui, QtWidgets

import gwbrowser.images as images
import gwbrowser.settings as settings_
import gwbrowser.common as common
import gwbrowser.common_ui as common_ui


def get_sections(): return (
    {'name': u'Application', 'description': u'Common Preferences',
        'cls': ApplicationSettingsWidget},
    {'name': u'Maya', 'description': u'Maya Settings', 'cls': MayaSettingsWidget},
)


def get_preference(name):
    return u'preferences/{}'.format(name)


class BaseSettingsWidget(QtWidgets.QWidget):
    def __init__(self, label, parent=None):
        super(BaseSettingsWidget, self).__init__(parent=parent)

        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        self._createUI()
        self._init_values()
        self._connectSignals()

    def _createUI(self):
        pass

    def _connectSignals(self):
        pass

    def _init_values(self):
        pass


class MayaSettingsWidget(BaseSettingsWidget):
    def __init__(self, parent=None):
        super(MayaSettingsWidget, self).__init__(
            u'Maya Settings', parent=parent)

    def _createUI(self):
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
            u'eg. viewport_captures/animation', parent=row)
        label = u'Edit the playblast path below. The path is relative to the current workspace.'
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
        ######################################################
        self.layout().addStretch(10)

    def _connectSignals(self):
        self.sync_active_button.toggled.connect(
            lambda x: settings_.local_settings.setValue(get_preference(u'disable_active_sync'), x))
        self.sync_maya_project_button.toggled.connect(
            lambda x: settings_.local_settings.setValue(get_preference(u'disable_workspace_sync'), x))
        self.save_warning_button.toggled.connect(
            lambda x: settings_.local_settings.setValue(get_preference(u'disable_save_warnings'), x))
        self.workspace_warning_button.toggled.connect(
            lambda x: settings_.local_settings.setValue(get_preference(u'disable_workspace_warnings'), x))

        self.alembic_export_path.textChanged.connect(
            lambda x: settings_.local_settings.setValue(get_preference(u'alembic_export_path'), x))
        self.capture_path.textChanged.connect(
            lambda x: settings_.local_settings.setValue(get_preference(u'capture_path'), x))

    def _init_values(self):
        val = settings_.local_settings.value(
            get_preference(u'disable_active_sync'))
        if val is not None:
            self.sync_active_button.setChecked(val)

        val = settings_.local_settings.value(
            get_preference(u'disable_workspace_sync'))
        if val is not None:
            self.sync_maya_project_button.setChecked(val)

        val = settings_.local_settings.value(
            get_preference(u'disable_save_warnings'))
        if val is not None:
            self.save_warning_button.setChecked(val)

        val = settings_.local_settings.value(
            get_preference(u'disable_workspace_warnings'))
        if val is not None:
            self.workspace_warning_button.setChecked(val)

        val = settings_.local_settings.value(
            get_preference(u'alembic_export_path'))
        if val is not None:
            self.alembic_export_path.setText(val)

        val = settings_.local_settings.value(
            get_preference(u'capture_path'))
        if val is not None:
            self.capture_path.setText(val)


class ApplicationSettingsWidget(BaseSettingsWidget):

    def __init__(self, parent=None):
        super(ApplicationSettingsWidget, self).__init__(
            u'Settings', parent=parent)
        self.show_help = None
        self.check_updates = None
        self.frameless_window = None

    def _createUI(self):
        import gwbrowser
        grp = common_ui.get_group(parent=self)
        row = common_ui.add_row(None, parent=grp, height=None)
        label = QtWidgets.QLabel()
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'custom_bw', None, common.INLINE_ICON_SIZE)
        label.setPixmap(pixmap)

        self.check_updates = common_ui.PaintedButton(
            u'Update', parent=row)
        self.show_help = common_ui.PaintedButton(
            u'Documentation', parent=row)
        row.layout().addWidget(label)
        common_ui.add_label(
            u'{} v{}'.format(common.PRODUCT, gwbrowser.__version__),
            parent=row
        )
        row.layout().addWidget(self.check_updates)
        row.layout().addWidget(self.show_help)
        #######################################################
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

        row = common_ui.add_row(u'Frameless window', parent=grp)
        self.frameless_window = QtWidgets.QCheckBox(
            u'Use frameless window', parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.frameless_window)
        #######################################################
        grp = common_ui.get_group(parent=self)
        o = common.MARGIN
        grp.layout().setContentsMargins(o, o, o, o)

        label = common_ui.PaintedLabel(
            u'Shortcuts', size=common.LARGE_FONT_SIZE, parent=self)
        grp.layout().addWidget(label)
        grp.layout().addSpacing(o)
        label = QtWidgets.QLabel(parent=self)
        label.setText(
            """
<span style="color:rgba({f});">Ctrl + C</span> Copy local path<br>
<span style="color:rgba({f});">Ctrl + Shift + C</span> Copy Unix path<br>
<span style="color:rgba({f});">Ctrl + R</span> Reload<br>
<span style="color:rgba({f});">Ctrl + F</span> Search/Filter<br>
<span style="color:rgba({f});">Ctrl + O</span> Show in File Explorer<br>
<span style="color:rgba({f});">Ctrl + S</span> Set/unset favourite<br>
<span style="color:rgba({f});">Ctrl + A</span> Archive/unarchive select<br>
<span style="color:rgba({f});">Ctrl + T</span> Show Notes & Comments<br>
<span style="color:rgba({f});">Ctrl + H</span> Show simple(r) file-list<br>
<span style="color:rgba({f});">Ctrl + M</span> Stop/Start generating thumbnails<br>

<span style="color:rgba({f});">Ctrl + Shift + A</span> Show/Hide archived items<br>
<span style="color:rgba({f});">Ctrl + Shift + F</span> Show/Hide non-favourites<br>

<span style="color:rgba({f});">Shift + Tab</span> Edit next description<br>
<span style="color:rgba({f});">Shift + Backtab</span> Edit previous description<br>
<span style="color:rgba({f});">Enter</span> Activate item<br>

<span style="color:rgba({f});">Alt + Left</span> Show previous panel<br>
<span style="color:rgba({f});">Alt + Right</span> Show next common_ui.PaintedLabel<br>

<span style="color:rgba({f});">Space</span> Preview thumbnail<br>

<span style="color:rgba({f});">Ctrl + 1</span> Show Bookmarks tab0<br>
<span style="color:rgba({f});">Ctrl + 2</span> Show Assets tab<br>
<span style="color:rgba({f});">Ctrl + 3</span> Show Files tab<br>
<span style="color:rgba({f});">Ctrl + 4</span> Show Favourites tab<br>
""".format(f=common.rgb(common.ADD))
        )
        label.setWordWrap(True)
        grp.layout().addWidget(label)

        self.layout().addStretch(10)

    def _connectSignals(self):
        import gwbrowser.versioncontrol.versioncontrol as vc
        self.check_updates.clicked.connect(vc.check)
        self.show_help.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(common.ABOUT_URL))

        self.frameless_window.toggled.connect(
            lambda x: settings_.local_settings.setValue(get_preference(u'frameless_window'), x))

        self.rv_path.textChanged.connect(self.set_rv_path)

    def _init_values(self):
        val = settings_.local_settings.value(
            get_preference(u'frameless_window'))
        val = val if not None else False
        if val is not None:
            self.frameless_window.setChecked(val)

        rv_path = settings_.local_settings.value(get_preference(u'rv_path'))
        val = rv_path if rv_path else None
        self.rv_path.setText(val)
        file_info = QtCore.QFileInfo(val)
        if file_info.exists():
            self.rv_path.setStyleSheet(
                u'color: rgba({})'.format(common.rgb(common.ADD)))
        else:
            self.rv_path.setStyleSheet(
                u'color: rgba({})'.format(common.rgb(common.REMOVE)))

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
        settings_.local_settings.setValue(get_preference(u'rv_path'), val)
        file_info = QtCore.QFileInfo(val)
        if file_info.exists():
            self.rv_path.setStyleSheet(
                u'color: rgba({})'.format(common.rgb(common.ADD)))
        else:
            self.rv_path.setStyleSheet(
                u'color: rgba({})'.format(common.rgb(common.REMOVE)))


class SectionSwitcherWidget(QtWidgets.QListWidget):
    """Widget responsible for selecting the preferences sections."""

    def __init__(self, parent=None):
        super(SectionSwitcherWidget, self).__init__(parent=parent)
        self._connectSignals()
        self.setMaximumWidth(130)

    def _connectSignals(self):
        self.selectionModel().currentChanged.connect(self.save_settings)

    def showEvent(self, event):
        self.init_settings()

    def init_settings(self):
        val = settings_.local_settings.value(u'preferences/current_section')
        if not val:
            self.setCurrentRow(0)
            return
        self.setCurrentRow(val)

    def save_settings(self, index):
        """Saves the current row selection to the local settings."""
        if not index.isValid():
            return
        settings_.local_settings.setValue(
            u'preferences/current_section', index.row())


class SectionsStackWidget(QtWidgets.QStackedWidget):

    def __init__(self, parent=None):
        super(SectionsStackWidget, self).__init__(parent=parent)


class PreferencesWidget(QtWidgets.QDialog):
    """The main preferences widget."""

    def __init__(self, parent=None):
        super(PreferencesWidget, self).__init__(parent=parent)
        self.sections_list_widget = None
        self.sections_stack_widget = None
        self.setWindowTitle(u'Preferences')
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoBackground)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(QtCore.Qt.Widget)

        self._createUI()
        self._add_sections()
        self._connectSignals()

    def _createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentsMargins(o, o * 0.5, o, o)
        self.layout().setSpacing(0)

        row = common_ui.add_row(None, padding=None, parent=self)
        self.hide_button = common_ui.ClickableIconButton(
            u'close',
            (common.REMOVE, common.REMOVE),
            common.ROW_BUTTONS_HEIGHT * 0.6
        )
        label = common_ui.PaintedLabel(
            'Preferences', size=common.LARGE_FONT_SIZE)
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
        scroll_area.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
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
                0, common.CONTROL_HEIGHT * 0.66))
            self.sections_list_widget.addItem(item)
            self.sections_stack_widget.addWidget(s[u'cls'](parent=self))

    def _connectSignals(self):
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
        pen.setWidthF(1.0)
        painter.setBrush(common.BACKGROUND)
        painter.setPen(pen)
        o = common.MARGIN * 0.4
        rect = self.rect().marginsRemoved(QtCore.QMargins(o, o, o, o))
        painter.setOpacity(0.9)
        painter.drawRoundedRect(rect, 4, 4)
        painter.end()

    def showEvent(self, event):
        if self.parent():
            self.resize(self.parent().rect().size())


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = PreferencesWidget()
    w.show()
    app.exec_()
