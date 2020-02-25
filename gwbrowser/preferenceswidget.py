"""Preferences"""

from PySide2 import QtCore, QtGui, QtWidgets

from gwbrowser.imagecache import ImageCache
import gwbrowser.settings as settings_
import gwbrowser.common as common
from gwbrowser.common_ui import PaintedButton, PaintedLabel, add_row, add_label, add_line_edit
import gwbrowser.slacker as slacker

def get_sections(): return (
    {'name': u'General', 'description': u'Common Preferences',
        'cls': ApplicationSettingsWidget},
    {'name': u'Integrations', 'description': u'External Package Integrations',
        'cls': IntegrationSettingsWidget},
    {'name': u'Maya Plugin', 'description': u'Maya Plugin Settings', 'cls': MayaSettingsWidget},
    # {'name': u'Folder templates', 'description': u'Various folder options', 'cls': TemplateSettingsWidget},
)


class BaseSettingsWidget(QtWidgets.QWidget):
    def __init__(self, label, parent=None):
        super(BaseSettingsWidget, self).__init__(parent=parent)

        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)

        label = PaintedLabel(
            label, size=common.LARGE_FONT_SIZE, color=common.TEXT)
        self.layout().addWidget(label)
        self.layout().addSpacing(common.MARGIN)
        self._createUI()
        self._init_values()
        self._connectSignals()

    def _createUI(self):
        pass

    def _connectSignals(self):
        pass

    def _init_values(self):
        pass

    def get_preference(self, name):
        cls = self.__class__.__name__.replace(u'Widget', u'')
        return u'preferences/{}/{}'.format(cls, name)


class MayaSettingsWidget(BaseSettingsWidget):
    def __init__(self, parent=None):
        super(MayaSettingsWidget, self).__init__(
            u'Maya Plugin Settings', parent=parent)

    def _createUI(self):
        pixmap = ImageCache.get_rsc_pixmap('maya', None, 32)
        label = QtWidgets.QLabel()
        label.setPixmap(pixmap)
        self.layout().addWidget(label)
        add_label(u'Bookmark & Asset Syncing', parent=self)
        label = u'The running instances of GWBrowser are syncronised by default. Eg. when an asset is activated in one instance, all the other instances will activate the same asset. You can disable this behaviour below (default is "off").'
        label = QtWidgets.QLabel(label)
        label.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.SECONDARY_TEXT)))
        label.setWordWrap(True)
        self.layout().addWidget(label)
        row = add_row(u'Sync instances', parent=self)
        self.sync_active_button = QtWidgets.QCheckBox(
            u'Disable instance syncing', parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.sync_active_button)
        self.layout().addSpacing(common.MARGIN)

        add_label(u'Warning Messages', parent=self)

        label = u'When the current Maya workspace is changed by another instance of GWBrowser a pop-up warning is shown by default. You can disable it below (default is "off").'
        label = QtWidgets.QLabel(label)
        label.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.SECONDARY_TEXT)))
        label.setWordWrap(True)
        self.layout().addWidget(label)
        row = add_row(u'Workspace warning', parent=self)
        self.workspace_warning_button = QtWidgets.QCheckBox(
            u'Disable workspace change warnings', parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.workspace_warning_button)

        label = u'Saving files outside the current workspace will show a warning dialog. Click below to disable (default is "off"):'
        label = QtWidgets.QLabel(label)
        label.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.SECONDARY_TEXT)))
        label.setWordWrap(True)
        self.layout().addWidget(label)
        row = add_row(u'Save warning', parent=self)
        self.save_warning_button = QtWidgets.QCheckBox(
            u'Disable save warnings', parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.save_warning_button)
        self.layout().addSpacing(common.MARGIN)

        add_label(u'Maya Workspace Syncing', parent=self)

        label = u'GWBrowser overrides workspaces set manually by `Set Project` and instead uses the active asset as the current workspace (Note: you won\'t be able to use `Set Project` whilst the Maya Workspace Syncing is on). Select below if you want to disable Maya Workspace Syncing (default is "off"):'
        label = QtWidgets.QLabel(label)
        label.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.SECONDARY_TEXT)))
        label.setWordWrap(True)
        self.layout().addWidget(label)
        row = add_row(u'Sync workspace', parent=self)
        self.sync_maya_project_button = QtWidgets.QCheckBox(
            u'Disable workspace syncing', parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.sync_maya_project_button)
        self.layout().addSpacing(common.MARGIN)

        add_label(u'Export & Import', parent=self)
        label = u'Edit the Alembic cache export path below. The following tokens have to be included:\n\n{workspace}: The path to the current workspace.\n{exports}: The name of the exports folder ("exports" by default).\n{set}: The name of the geometry group (eg. "character_rig_geo")\n\nThere must be a version number present as well (this will be automatically incremented when exporting). Eg. v01, v001 or v0001, etc.'
        label = QtWidgets.QLabel(label)
        label.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.SECONDARY_TEXT)))
        label.setWordWrap(True)
        self.layout().addWidget(label)
        row = add_row(u'Alembic template', parent=self)
        self.alembic_export_path = add_line_edit(
            u'eg. {workspace}/{exports}/abc/{set}/{set}_v001.abc', parent=row)
        row.layout().addWidget(self.alembic_export_path, 1)

        label = u'Edit the viewport capture path below. The path is relative to the current workspace.'
        label = QtWidgets.QLabel(label)
        label.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.SECONDARY_TEXT)))
        label.setWordWrap(True)
        self.layout().addWidget(label)
        row = add_row(u'Capture folder', parent=self)
        self.capture_path = add_line_edit(
            u'eg. viewport_captures/animation', parent=row)
        row.layout().addWidget(self.capture_path, 1)


        label = u'Reveal output folder in the file explorer after the capture finishes.'
        label = QtWidgets.QLabel(label)
        label.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.SECONDARY_TEXT)))
        label.setWordWrap(True)
        self.layout().addWidget(label)
        row = add_row(u'Reveal capture', parent=self)
        self.reveal_capture_button = QtWidgets.QCheckBox(
            u'Reveal capture in the file explorer', parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.reveal_capture_button)
        self.layout().addSpacing(common.MARGIN)

        label = u'Set if the viewport capture should be automatically pushed to RV when a capture finishes.'
        label = QtWidgets.QLabel(label)
        label.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.SECONDARY_TEXT)))
        label.setWordWrap(True)
        self.layout().addWidget(label)
        row = add_row(u'Reveal capture', parent=self)
        self.push_to_rv_button = QtWidgets.QCheckBox(
            u'Push capture to RV', parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.push_to_rv_button)
        self.layout().addSpacing(common.MARGIN)

        self.layout().addStretch(1)

    def _connectSignals(self):
        self.sync_active_button.toggled.connect(
            lambda x: settings_.local_settings.setValue(self.get_preference(u'disable_active_sync'), x))
        self.sync_maya_project_button.toggled.connect(
            lambda x: settings_.local_settings.setValue(self.get_preference(u'disable_workspace_sync'), x))
        self.save_warning_button.toggled.connect(
            lambda x: settings_.local_settings.setValue(self.get_preference(u'disable_save_warnings'), x))
        self.workspace_warning_button.toggled.connect(
            lambda x: settings_.local_settings.setValue(self.get_preference(u'disable_workspace_warnings'), x))
        self.reveal_capture_button.toggled.connect(
            lambda x: settings_.local_settings.setValue(self.get_preference(u'reveal_capture'), x))
        self.push_to_rv_button.toggled.connect(
            lambda x: settings_.local_settings.setValue(self.get_preference(u'push_to_rv'), x))
        self.alembic_export_path.textChanged.connect(
            lambda x: settings_.local_settings.setValue(self.get_preference(u'alembic_export_path'), x))
        self.capture_path.textChanged.connect(
            lambda x: settings_.local_settings.setValue(self.get_preference(u'capture_path'), x))

    def _init_values(self):
        val = settings_.local_settings.value(self.get_preference(u'disable_active_sync'))
        if val is not None:
            self.sync_active_button.setChecked(val)

        val = settings_.local_settings.value(self.get_preference(u'disable_workspace_sync'))
        if val is not None:
            self.sync_maya_project_button.setChecked(val)

        val = settings_.local_settings.value(self.get_preference(u'disable_save_warnings'))
        if val is not None:
            self.save_warning_button.setChecked(val)

        val = settings_.local_settings.value(self.get_preference(u'disable_workspace_warnings'))
        if val is not None:
            self.workspace_warning_button.setChecked(val)

        val = settings_.local_settings.value(self.get_preference(u'reveal_capture'))
        val = val if val is not None else False
        self.reveal_capture_button.setChecked(val)

        val = settings_.local_settings.value(self.get_preference(u'push_to_rv'))
        val = val if val is not None else True
        self.push_to_rv_button.setChecked(val)

        val = settings_.local_settings.value(self.get_preference(u'alembic_export_path'))
        if val:
            self.alembic_export_path.setText(val)
        else:
            self.alembic_export_path.setText(common.ALEMBIC_EXPORT_PATH)

        val = settings_.local_settings.value(self.get_preference(u'capture_path'))
        if val:
            self.capture_path.setText(val)
        else:
            self.capture_path.setText(common.CAPTURE_PATH)


class IntegrationSettingsWidget(BaseSettingsWidget):

    def __init__(self, parent=None):
        super(IntegrationSettingsWidget, self).__init__(
            u'Integration Settings', parent=parent)

    def _createUI(self):


        add_label(u'Slack', parent=self)


        row = add_row(u'Workspace Url', parent=self)

        label = QtWidgets.QLabel(parent=self)
        pixmap = ImageCache.get_rsc_pixmap('slack', common.TEXT, 32)
        label.setPixmap(pixmap)
        row.layout().addWidget(label)

        self.slack_url = add_line_edit(
            u'eg. https://mystudio.slack.com...', parent=row)
        row.layout().addWidget(self.slack_url, 1)
        button = PaintedButton(u'Visit')
        button.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(self.slack_url.text()))
        row.layout().addWidget(button)

        row = add_row(u'Slack API Token', parent=self)
        label = u'You will have to add a Slack App or Bot to your workspace to use this feature. Make sure they have adequate permissions to read user data and to send messages. Once all set up, paste the authentication token (usually starting with "xoxb" or "xoxp") here.'
        label = QtWidgets.QLabel(label)
        label.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.SECONDARY_TEXT)))
        label.setWordWrap(True)
        self.layout().addWidget(label)
        self.slack_token = add_line_edit(
            u'eg. xoxb-01234567890-01234567...', parent=row)
        row.layout().addWidget(self.slack_token, 1)
        button = PaintedButton(u'Test Token')
        button.clicked.connect(self.test_slack_token)
        row.layout().addWidget(button)

        row = add_row(u'Your Member ID', parent=self)
        self.slack_member_id = add_line_edit(
            u'eg. U01ABC23D', parent=row)
        row.layout().addWidget(self.slack_member_id)
        button = PaintedButton(u'Test ID')
        button.clicked.connect(self.test_slack_member_id)
        row.layout().addWidget(button)
        label = u'You can get your Member ID from Slack (usually found on your profile page).\nThis is used to let other users know who is sending the message.'
        label = QtWidgets.QLabel(label)
        label.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.SECONDARY_TEXT)))
        label.setWordWrap(True)
        self.layout().addWidget(label)

        self.layout().addSpacing(common.MARGIN)

        add_label(u'Shotgun RV', parent=self)
        row = add_row(u'RV Executable', parent=self)
        self.rv_path = add_line_edit(
            u'eg. C:/rv/bin/rv.exe', parent=row)
        row.layout().addWidget(self.rv_path, 1)
        button = PaintedButton(u'Pick')
        button.clicked.connect(self.pick_rv)
        row.layout().addWidget(button)
        button = PaintedButton(u'Reveal')
        button.clicked.connect(lambda: common.reveal(self.rv_path.text()))
        row.layout().addWidget(button)

        self.layout().addSpacing(common.MARGIN)

        add_label(u'FFMPEG', parent=self)
        row = add_row(u'FFmpeg Executable', parent=self)
        self.ffmpeg_path = add_line_edit(
            u'eg. //myserver/path/to/ffmpeg.exe', parent=row)
        row.layout().addWidget(self.ffmpeg_path, 1)
        button = PaintedButton(u'Pick')
        button.clicked.connect(self.pick_ffmpeg)
        row.layout().addWidget(button)
        button = PaintedButton(u'Reveal')
        button.clicked.connect(lambda: common.reveal(self.ffmpeg_path.text()))
        row.layout().addWidget(button)

        row = add_row(u'FFmpeg Command', parent=self)
        self.ffmpeg_command = add_line_edit(
            u'eg. -loglevel info -hide_banner -y -framerate {framerate} -start_number {start} -i "{source}" -c:v libx264 -crf 25 -vf format=yuv420p "{dest}"', parent=row)
        row.layout().addWidget(self.ffmpeg_command, 1)
        label = u'Edit the FFMPEG convert command above. This is the argument passed to ffmpeg to create, by default, a h264 video. The following tokens have to be included:\n\n{framerate}: The scene\' framerate\n{start}: The first frame of the sequence, eg. 1001\n{source} Path to the capture\n{dest}: Output path'
        label = QtWidgets.QLabel(label)
        label.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.SECONDARY_TEXT)))
        label.setWordWrap(True)
        self.layout().addWidget(label)

        self.layout().addStretch()

    def _init_values(self):
        slack_url = settings_.local_settings.value(self.get_preference(u'slack_url'))
        val = slack_url if slack_url else None
        self.slack_url.setText(val)

        slack_token = settings_.local_settings.value(self.get_preference(u'slack_token'))
        val = slack_token if slack_token else u''
        self.slack_token.setText(val)

        slack_member_id = settings_.local_settings.value(self.get_preference(u'slack_member_id'))
        val = slack_member_id if slack_member_id else u''
        self.slack_member_id.setText(val)

        rv_path = settings_.local_settings.value(self.get_preference(u'rv_path'))
        val = rv_path if rv_path else None
        self.rv_path.setText(val)
        file_info = QtCore.QFileInfo(val)
        if file_info.exists():
            self.rv_path.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.ADD)))
        else:
            self.rv_path.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.REMOVE)))

        val = settings_.local_settings.value(self.get_preference(u'ffmpeg_path'))
        val = val if val else u''
        self.ffmpeg_path.setText(val)
        file_info = QtCore.QFileInfo(val)
        if file_info.exists():
            self.ffmpeg_path.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.ADD)))
        else:
            self.ffmpeg_path.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.REMOVE)))

        val = settings_.local_settings.value(self.get_preference(u'ffmpeg_command'))
        if val:
            self.ffmpeg_command.setText(val)
        else:
            self.ffmpeg_command.setText(common.FFMPEG_COMMAND)

    def _connectSignals(self):
        self.slack_url.textChanged.connect(
            lambda x: settings_.local_settings.setValue(self.get_preference(u'slack_url'), x))
        self.slack_token.textChanged.connect(
            lambda x: settings_.local_settings.setValue(self.get_preference(u'slack_token'), x))
        self.slack_member_id.textChanged.connect(
            lambda x: settings_.local_settings.setValue(self.get_preference(u'slack_member_id'), x))

        @QtCore.Slot(unicode)
        def set_rv_path(val):
            settings_.local_settings.setValue(self.get_preference(u'rv_path'), val)
            file_info = QtCore.QFileInfo(val)
            if file_info.exists():
                self.rv_path.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.ADD)))
            else:
                self.rv_path.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.REMOVE)))

        @QtCore.Slot(unicode)
        def set_ffmpeg_path(val):
            settings_.local_settings.setValue(self.get_preference(u'ffmpeg_path'), val)
            file_info = QtCore.QFileInfo(val)
            if file_info.exists():
                self.ffmpeg_path.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.ADD)))
            else:
                self.ffmpeg_path.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.REMOVE)))

        self.rv_path.textChanged.connect(set_rv_path)

        self.ffmpeg_path.textChanged.connect(set_ffmpeg_path)
        self.ffmpeg_command.textChanged.connect(
            lambda x: settings_.local_settings.setValue(self.get_preference(u'ffmpeg_command'), x))

    def test_slack_token(self):
        try:
            client = slacker.Slacker(self.slack_token.text(), self.slack_member_id.text())
            client.profiles()

            self.slack_token.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.ADD)))
            mbox = QtWidgets.QMessageBox(parent=self)
            mbox.setIcon(QtWidgets.QMessageBox.Information)
            mbox.setWindowTitle(u'Slack: Thumbs up!')
            mbox.setText(u'All seems to be working correctly. Thumbs up!')
            mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            mbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
            res = mbox.exec_()
        except Exception as err:
            mbox = QtWidgets.QMessageBox(parent=self)
            mbox.setIcon(QtWidgets.QMessageBox.Information)
            mbox.setWindowTitle(u'Slack: An error occured')
            mbox.setText(u'An error occured validating the Slack API token:')
            mbox.setInformativeText(u'{}'.format(err))
            mbox.setIcon(QtWidgets.QMessageBox.Warning)
            mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            mbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
            self.slack_token.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.REMOVE)))
            res = mbox.exec_()

    def test_slack_member_id(self):
        try:
            client = slacker.Slacker(self.slack_token.text(), self.slack_member_id.text())
            profiles = client.profiles()
            if not self.slack_member_id.text().lower() in [f[ucommon.IdRole].lower() for f in profiles if f[ucommon.IdRole]]:
                raise RuntimeError(u'Member ID not found in the profiles.')

            self.slack_member_id.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.ADD)))
            mbox = QtWidgets.QMessageBox(parent=self)
            mbox.setIcon(QtWidgets.QMessageBox.Information)
            mbox.setWindowTitle(u'Slack: Thumbs up!')
            mbox.setText(u'All seems to be working correctly. Thumbs up!')
            mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            mbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
            res = mbox.exec_()
        except Exception as err:
            mbox = QtWidgets.QMessageBox(parent=self)
            mbox.setIcon(QtWidgets.QMessageBox.Information)
            mbox.setWindowTitle(u'Slack: An error occured')
            mbox.setText(u'An error occured validating the Slack API token:')
            mbox.setInformativeText(u'{}'.format(err))
            mbox.setIcon(QtWidgets.QMessageBox.Warning)
            mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            mbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
            self.slack_member_id.setStyleSheet(u'color: rgba({})'.format(common.rgb(common.REMOVE)))
            res = mbox.exec_()

    def pick_rv(self):
        if common.get_platform() == u'win':
            res = QtWidgets.QFileDialog.getOpenFileName(
                caption=u'Select RV.exe',
                filter=u'rv.exe',
                dir=u'/'
            )
            path, ext = res
            if path:
                self.rv_path.setText(path)
        if common.get_platform() == u'mac':
            res = QtWidgets.QFileDialog.getOpenFileName(
                caption=u'Select RV',
                filter=u'*.*',
                dir=u'/'
            )
            path, ext = res
            if path:
                self.rv_path.setText(path)

    def pick_ffmpeg(self):
        if common.get_platform() == u'win':
            res = QtWidgets.QFileDialog.getOpenFileName(
                caption=u'Select ffmpeg.exe',
                filter=u'ffmpeg.exe',
                dir=u'/'
            )
            path, ext = res
            if path:
                self.ffmpeg_path.setText(path)

        if common.get_platform() == u'mac':
            res = QtWidgets.QFileDialog.getOpenFileName(
                caption=u'Select FFmpeg',
                filter=u'*.*',
                dir=u'/'
            )
            path, ext = res
            if path:
                self.ffmpeg_path.setText(path)


class ApplicationSettingsWidget(BaseSettingsWidget):

    def __init__(self, parent=None):
        super(ApplicationSettingsWidget, self).__init__(
            u'General Settings', parent=parent)
        self.reveal_asset_template = None
        self.show_help = None
        self.check_updates = None

    def _createUI(self):
        label = QtWidgets.QLabel()
        pixmap = ImageCache.get_rsc_pixmap('custom', None, 64)
        label.setPixmap(pixmap)
        self.layout().addWidget(label)


        import gwbrowser
        add_label(u'You\'re running GWBrowser v{}'.format(
            gwbrowser.__version__), parent=self)

        row = add_row(u'Update', parent=self)
        self.check_updates = PaintedButton(
            u'Check for updates', width=200, parent=row)
        row.layout().addStretch(1)
        row.layout().addWidget(self.check_updates)

        row = add_row(u'Documentation', parent=self)
        self.show_help = PaintedButton(
            u'Show online documentation', width=200, parent=row)
        row.layout().addStretch(1)
        row.layout().addWidget(self.show_help)

        add_label(u'Asset & Job Folder Templates', parent=self)
        row = add_row(u'Reveal files', parent=self)
        self.reveal_asset_template = PaintedButton(
            u'Show in explorer', width=200, parent=row)
        row.layout().addStretch(1)
        row.layout().addWidget(self.reveal_asset_template, 1)

        add_label(u'Company Name', parent=self)
        row = add_row(u'Company', parent=self)
        self.company_name = add_line_edit(
            u'eg. My Studio', parent=row)

        add_label(u'Shortcuts', parent=self)
        label = QtWidgets.QLabel(parent=self)
        label.setText(
"""
'Ctrl+C': Copy local path
'Ctrl+Shift+C': Copy Unix path
'Ctrl+R': Reload
'Ctrl+F': Search/Filter
'Ctrl+O': Show in File Explorer
'Ctrl+S': Set/unset favourite
'Ctrl+A': Archive/unarchive select
'Ctrl+T': Show Notes & Comments
'Ctrl+H': Show simple(r) file-list
'Ctrl+M': Stop/Start generating thumbnails

'Ctrl+Shift+A': Show/Hide archived items
'Ctrl+Shift+F': Show/Hide non-favourites

'Shift+Tab': Edit next description
'Shift+Backtab': Edit previous description
'Enter': Activate item

'Alt+Left': Show previous panel
'Alt+Right': Show next PaintedLabel

'Space': Preview thumbnail

'Ctrl+1': Show Bookmarks tab0
'Ctrl+2': Show Assets tab
'Ctrl+3': Show Files tab
'Ctrl+4': Show Favourites tab
"""
        )
        label.setWordWrap(True)
        label.setStyleSheet(u'color: rgba({});'.format(
            common.rgb(common.TEXT),
        ))
        self.layout().addWidget(label)
        self.layout().addStretch(1)


    def _init_values(self):
        company_name = settings_.local_settings.value(self.get_preference(u'company'))
        val = company_name if company_name else common.COMPANY
        self.company_name .setText(val)

    def _connectSignals(self):
        import gwbrowser.versioncontrol.versioncontrol as vc
        self.check_updates.clicked.connect(vc.check)
        self.show_help.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(common.ABOUT_URL))
        self.reveal_asset_template.clicked.connect(self.show_asset_template)
        self.company_name.textChanged.connect(
            lambda x: settings_.local_settings.setValue(self.get_preference(u'company'), x))


    @QtCore.Slot()
    def show_asset_template(self):
        home = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.DocumentsLocation)
        path = u'{}/GWBrowser/Asset.zip'.format(home)
        common.reveal(path)


class TemplateSettingsWidget(BaseSettingsWidget):

    def __init__(self, parent=None):
        super(TemplateSettingsWidget, self).__init__(
            u'Template Settings', parent=parent)
        self.slack_editor = None
        self.asset_identifier = None

        self.setDisabled(True)

    def _createUI(self):
        # Folder descriptions
        add_label(u'Folder descriptions', parent=self)

        # Exports
        row = add_row(u'Exports Folder:', parent=self)
        self.folder_export_name = add_line_edit(
            u'Folder name, eg. "exports"', parent=row)
        row = add_row(u'Description:', parent=self)
        self.folder_export_description = add_line_edit(
            u'Description...', parent=row)
        # Data
        row = add_row(u'Data Folder:', parent=self)
        self.folder_data_name = add_line_edit(
            u'Folder name, eg. "data"', parent=row)
        row = add_row(u'Description:', parent=self)
        self.folder_data_description = add_line_edit(
            u'Description...', parent=row)
        # Data
        row = add_row(u'Reference Folder:', parent=self)
        self.folder_reference_name = add_line_edit(
            u'Folder name, eg. "reference"', parent=row)
        row = add_row(u'Description', parent=self)
        self.folder_reference_description = add_line_edit(
            u'Description...', parent=row)

        self.layout().addStretch(1)


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
        settings_.local_settings.setValue(u'preferences/current_section', index.row())


class SectionsStackWidget(QtWidgets.QStackedWidget):

    def __init__(self, parent=None):
        super(SectionsStackWidget, self).__init__(parent=parent)


class PreferencesWidget(QtWidgets.QSplitter):
    """The main preferences widget."""

    def __init__(self, parent=None):
        super(PreferencesWidget, self).__init__(parent=parent)
        self.sections_list_widget = None
        self.sections_stack_widget = None
        self.setWindowTitle(u'GWBrowser Preferences')

        self._createUI()
        self._add_sections()
        self._connectSignals()

    def _createUI(self):
        common.set_custom_stylesheet(self)
        self.sections_list_widget = SectionSwitcherWidget(parent=self)
        self.addWidget(self.sections_list_widget)

        scroll_area = QtWidgets.QScrollArea(parent=self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.addWidget(scroll_area)

        self.sections_stack_widget = SectionsStackWidget(parent=self)
        scroll_area.setWidget(self.sections_stack_widget)

    def _add_sections(self):
        """Adds the sections defined in the ``SECTIONS`` variable."""
        for s in get_sections():
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, u'  {}'.format(s[u'name'].title()))
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


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = PreferencesWidget()
    w.show()
    app.exec_()
