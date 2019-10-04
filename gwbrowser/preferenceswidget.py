"""Preferences"""

import re
from PySide2 import QtCore, QtGui, QtWidgets

from gwbrowser.settings import local_settings
import gwbrowser.common as common
from gwbrowser.common_ui import PaintedButton, PaintedLabel, add_row, add_label, add_line_edit


get_sections = lambda: (
    {'name': u'General', 'description': u'Common preferences', 'cls': ApplicationSettingsWidget},
    {'name': u'Servers', 'description': u'Server preferences', 'cls': ServersSettingsWidget},
    {'name': u'Maya', 'description': u'Maya settings', 'cls': MayaSettingsWidget},
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

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum,
        )

        label = PaintedLabel(label, size=common.LARGE_FONT_SIZE, color=common.TEXT)
        self.layout().addWidget(label)


        self._createUI()
        self._init_values()
        self._connectSignals()

    def _createUI(self):
        pass

    def _connectSignals(self):
        pass

    def _init_values(self):
        pass

    def name(self, name):
        cls = self.__class__.__name__.replace(u'Widget', u'')
        return u'preferences/{}/{}'.format(cls, name)


class MayaSettingsWidget(BaseSettingsWidget):
    def __init__(self, parent=None):
        super(MayaSettingsWidget, self).__init__(u'Maya Settings', parent=parent)

    def _createUI(self):
        add_label(u'Bookmark & Asset Syncing', parent=self)

        label = u'GWBrowser sessions are syncronised by default. Disable syncing below (default is "off"):'
        label = QtWidgets.QLabel(label)
        label.setWordWrap(True)
        self.layout().addWidget(label)

        row = add_row(u'Sync instances', parent=self)
        self.sync_active_button = QtWidgets.QCheckBox(u'Disable instance syncing', parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.sync_active_button)

        add_label(u'Maya workspace syncing', parent=self)
        label =u'The Maya workspace is always set to be the active GWBrowser asset by default. Click below to disable workspace syncing (default is "off"):'
        label = QtWidgets.QLabel(label)
        label.setWordWrap(True)
        self.layout().addWidget(label)

        row = add_row(u'Sync workspace', parent=self)
        self.sync_maya_project_button = QtWidgets.QCheckBox(u'Disable workspace syncing', parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.sync_maya_project_button)


        label =u'Saving files outside the current workspace will shows a warning dialog. Click below to disable (default is "off"):'
        label = QtWidgets.QLabel(label)
        label.setWordWrap(True)
        self.layout().addWidget(label)
        row = add_row(u'Save warning', parent=self)
        self.save_warning_button = QtWidgets.QCheckBox(u'Disable save warnings', parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.save_warning_button)

        label =u'When the asset is changed in a another session a warning message is show by default. Click below to disable (default is "off"):'
        label = QtWidgets.QLabel(label)
        label.setWordWrap(True)
        self.layout().addWidget(label)
        row = add_row(u'Workspace warning', parent=self)
        self.workspace_warning_button = QtWidgets.QCheckBox(u'Disable workspace change warnings', parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.workspace_warning_button)

        label =u'The template used to export the alembic caches:'
        label = QtWidgets.QLabel(label)
        label.setWordWrap(True)
        self.layout().addWidget(label)
        row = add_row(u'Alembic template', parent=self)
        self.alembic_export_path = add_line_edit(
            u'eg. {workspace}/{exports}/abc/{set}/{set}_v001.abc', parent=row)
        row.layout().addWidget(self.alembic_export_path, 1)

        self.layout().addStretch(1)

    def _connectSignals(self):
        self.sync_active_button.toggled.connect(lambda x: local_settings.setValue(self.name(u'disable_active_sync'), x))
        self.sync_maya_project_button.toggled.connect(lambda x: local_settings.setValue(self.name(u'disable_workspace_sync'), x))
        self.save_warning_button.toggled.connect(lambda x: local_settings.setValue(self.name(u'disable_save_warnings'), x))
        self.workspace_warning_button.toggled.connect(lambda x: local_settings.setValue(self.name(u'disable_workspace_warnings'), x))
        self.alembic_export_path.textChanged.connect(lambda x: local_settings.setValue(self.name(u'alembic_export_path'), x))

    def _init_values(self):
        val = local_settings.value(self.name(u'disable_active_sync'))
        if val is not None:
            self.sync_active_button.setChecked(val)

        val = local_settings.value(self.name(u'disable_workspace_sync'))
        if val is not None:
            self.sync_maya_project_button.setChecked(val)

        val = local_settings.value(self.name(u'disable_save_warnings'))
        if val is not None:
            self.save_warning_button.setChecked(val)

        val = local_settings.value(self.name(u'disable_workspace_warnings'))
        if val is not None:
            self.workspace_warning_button.setChecked(val)

        val = local_settings.value(self.name(u'alembic_export_path'))
        if val:
            self.alembic_export_path.setText(val)
        else:
            self.alembic_export_path.setText(common.ALEMBIC_EXPORT_PATH)


class ApplicationSettingsWidget(BaseSettingsWidget):

    def __init__(self, parent=None):
        super(ApplicationSettingsWidget, self).__init__(u'General Settings', parent=parent)
        self.slack_url = None
        self.reveal_asset_template = None
        self.show_help = None
        self.check_updates = None

    def _createUI(self):
        import gwbrowser
        add_label(u'You\'re running GWBrowser v{}'.format(gwbrowser.__version__), parent=self)

        row = add_row(u'Update', parent=self)
        self.check_updates = PaintedButton(u'Check for updates', width=200, parent=row)
        row.layout().addStretch(1)
        row.layout().addWidget(self.check_updates)

        row = add_row(u'Documentation', parent=self)
        self.show_help = PaintedButton(u'Show online documentation', width=200, parent=row)
        row.layout().addStretch(1)
        row.layout().addWidget(self.show_help)


        add_label(u'Asset & Job Folder Templates', parent=self)
        row = add_row(u'Reveal files', parent=self)
        self.reveal_asset_template = PaintedButton(u'Show in explorer', width=200, parent=row)
        row.layout().addStretch(1)
        row.layout().addWidget(self.reveal_asset_template, 1)

        add_label(u'Slack shortcut', parent=self)
        row = add_row(u'Current URL', parent=self)
        self.slack_url = add_line_edit(
            u'eg. https://mystudio.slack.com...', parent=row)
        row.layout().addWidget(self.slack_url, 1)

        add_label(u'Company name', parent=self)
        row = add_row(u'', parent=self)
        label = 'Add the name of your company below.'
        label = QtWidgets.QLabel(label, parent=self)
        label.setWordWrap(True)
        row.layout().addWidget(label, 1)
        row = add_row(u'Company', parent=self)
        self.company_name = add_line_edit(
            u'eg. My Studio', parent=row)

        self.layout().addStretch(1)

    def _init_values(self):
        slack_url = local_settings.value(self.name(u'slack_url'))
        val = slack_url if slack_url else common.SLACK_URL
        self.slack_url.setText(val)

        company_name = local_settings.value(self.name(u'company'))
        val = company_name if company_name else common.COMPANY
        self.company_name .setText(val)

    def _connectSignals(self):
        import gwbrowser.versioncontrol.versioncontrol as vc
        self.check_updates.clicked.connect(vc.check)
        self.show_help.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(common.ABOUT_URL))
        self.reveal_asset_template.clicked.connect(self.show_asset_template)

        self.slack_url.textChanged.connect(
            lambda x: local_settings.setValue(self.name(u'slack_url'), x))

        self.company_name.textChanged.connect(
            lambda x: local_settings.setValue(self.name(u'company'), x))

    @QtCore.Slot()
    def show_asset_template(self):
        home = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)
        path = u'{}/GWBrowser/Asset.zip'.format(home)
        common.reveal(path)


class TemplateSettingsWidget(BaseSettingsWidget):

    def __init__(self, parent=None):
        super(TemplateSettingsWidget, self).__init__(u'Template Settings', parent=parent)
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


class ServersSettingsWidget(BaseSettingsWidget):
    """Dialog to edit the server configuration.

    The server information is stored in the templates/servers.conf
    and is supplied by the ``common.Server`` class. This widget will  write
    directly into the configuration files.

    """

    def __init__(self, parent=None):
        """
        Properties:
            primary_mac_editor:
            primary_win_editor:
            primary_description:

            backup_mac_editor:
            backup_win_editor:
            backup_description:

            local_mac_editor:
            local_win_description:
            local_description:

        """
        super(ServersSettingsWidget, self).__init__(u'Server Settings', parent=parent)


    def _createUI(self):
        o = common.MARGIN
        # Primary server
        add_label(u'Primary server', parent=self)
        row = add_row(u'MacOS', parent=self)
        self.primary_mac_editor = add_line_edit(
            u'eg. /Volumes/jobs...', parent=row)
        row = add_row(u'Windows', parent=self, padding=o)
        self.primary_win_editor = add_line_edit(
            u'eg. //myserver/jobs...', parent=row)
        row = add_row(u'Description', parent=self, padding=o)
        self.primary_description = add_line_edit(
            u'Enter a description...', parent=row)

        # Backup server
        add_label(u'Secondary server', parent=self)
        row = add_row(u'MacOS', parent=self, padding=o)
        self.backup_mac_editor = add_line_edit(
            u'eg. /Volumes/jobs...', parent=row)
        row = add_row(u'Windows', parent=self, padding=o)
        self.backup_win_editor = add_line_edit(
            u'eg. //myserver/jobs...', parent=row)
        row = add_row(u'Description', parent=self, padding=o)
        self.backup_description = add_line_edit(
            u'Enter a description...', parent=row)

        # Backup server
        add_label(u'Local job folder', parent=self)
        row = add_row(u'MacOS', parent=self, padding=o)
        self.local_mac_editor = add_line_edit(u'eg. /jobs...', parent=row)
        row = add_row(u'Windows', parent=self, padding=o)
        self.local_win_editor = add_line_edit(u'eg. C:/jobs...', parent=row)
        row = add_row(u'Description', parent=self, padding=o)
        self.local_description = add_line_edit(
            u'Enter a description...', parent=row)

        self.layout().addStretch(1)
        regex = QtCore.QRegExp(u'[a-zA-Z0-9/_-]*')
        validator = QtGui.QRegExpValidator(regex)
        self.primary_mac_editor.setValidator(validator)
        self.primary_win_editor.setValidator(validator)
        self.primary_description.setValidator(validator)
        self.backup_mac_editor.setValidator(validator)
        self.backup_win_editor.setValidator(validator)
        self.backup_description.setValidator(validator)
        self.local_mac_editor.setValidator(validator)
        self.local_win_editor.setValidator(validator)
        self.local_description.setValidator(validator)

    def _connectSignals(self):
        pass
        # self.primary_mac_editor.textChanged.connect(self.save_settings)
        # self.primary_win_editor.textChanged.connect(self.save_settings)
        # self.primary_description.textChanged.connect(self.save_settings)
        # self.backup_mac_editor.textChanged.connect(self.save_settings)
        # self.backup_win_editor.textChanged.connect(self.save_settings)
        # self.backup_description.textChanged.connect(self.save_settings)
        # self.local_mac_editor.textChanged.connect(self.save_settings)
        # self.local_win_editor.textChanged.connect(self.save_settings)
        # self.local_description.textChanged.connect(self.save_settings)

    def _init_values(self):
        """Populates the edit fields with the saved values."""
        parser = common.Server.conf()

        def _get(section, key):
            try:
                return parser.get(section, key)
            except:
                return u''

        self.primary_mac_editor.setText(_get(u'primary', u'mac'))
        self.primary_win_editor.setText(_get(u'primary', u'win'))
        self.primary_description.setText(_get(u'primary', u'description'))

        self.backup_mac_editor.setText(_get(u'backup', u'mac'))
        self.backup_win_editor.setText(_get(u'backup', u'win'))
        self.backup_description.setText(_get(u'backup', u'description'))

        self.local_mac_editor.setText(_get(u'local', u'mac'))
        self.local_win_editor.setText(_get(u'local', u'win'))
        self.local_description.setText(_get(u'local', u'description'))

    def sizeHint(self):
        return QtCore.QSize(500, 500)

    def hideEvent(self, event):
        self.save_settings()

    @QtCore.Slot()
    def save_settings(self):
        """"""
        values = {
            u'primary:mac': self.primary_mac_editor.text().rstrip(u'/'),
            u'primary:win': self.primary_win_editor.text().rstrip(u'/'),
            u'primary:description': self.primary_description.text(),
            u'backup:mac': self.backup_mac_editor.text().rstrip(u'/'),
            u'backup:win': self.backup_win_editor.text().rstrip(u'/'),
            u'backup:description': self.backup_description.text(),
            u'local:mac': self.local_mac_editor.text().rstrip(u'/'),
            u'local:win': self.local_win_editor.text().rstrip(u'/'),
            u'local:description': self.local_description.text(),
        }

        if not all((values[u'primary:win'], values[u'primary:mac'])):
            mbox = QtWidgets.QMessageBox(parent=self)
            mbox.setWindowTitle(u'Primary not set')
            mbox.setIcon(QtWidgets.QMessageBox.Warning)
            mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            mbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
            mbox.setText(u'Primary server has to be set.')
            mbox.setInformativeText(
                u'It usually is a network path of the server where the jobs are stored, eg. //myserver/jobs')
            return mbox.exec_()

        parser = common.Server.conf()
        for k in values:
            section, key = k.split(u':')
            if not parser.has_section(section):
                parser.add_section(section)
            parser.set(section, key, values[k])

        # Making the path if the folder doesn't exist
        file_info = QtCore.QFileInfo(common.Server.conf_path())
        if not file_info.exists():
            file_info.dir().mkpath(file_info.dir().path())

        # Creating the config file if it doesn't exist
        with open(common.Server.conf_path(), u'w+') as configfile:
            parser.write(configfile)

        return


class SectionSwitcherWidget(QtWidgets.QListWidget):
    """Widget responsible for selecting the preferences sections."""

    def __init__(self, parent=None):
        super(SectionSwitcherWidget, self).__init__(parent=parent)
        self.setFixedWidth(150)
        self._connectSignals()

    def _connectSignals(self):
        self.selectionModel().currentChanged.connect(self.save_settings)

    def showEvent(self, event):
        self.init_settings()

    def init_settings(self):
        val = local_settings.value(u'preferences/current_section')
        if not val:
            self.setCurrentRow(0)
            return
        self.setCurrentRow(val)

    def save_settings(self, index):
        """Saves the current row selection to the local settings."""
        if not index.isValid():
            return
        local_settings.setValue(u'preferences/current_section', index.row())


class SectionsStackWidget(QtWidgets.QStackedWidget):

    def __init__(self, parent=None):
        super(SectionsStackWidget, self).__init__(parent=parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )


class PreferencesWidget(QtWidgets.QWidget):
    """The main preferences widget."""

    def __init__(self, parent=None):
        super(PreferencesWidget, self).__init__(parent=parent)
        self.sections_list_widget = None
        self.sections_stack_widget = None
        self.setWindowTitle(u'GWBrowser Preferences')
        self.setWindowFlags(QtCore.Qt.Window)

        self._createUI()
        self._add_sections()
        self._connectSignals()

    def _createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QHBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentsMargins(o, o, o, o)

        self.sections_list_widget = SectionSwitcherWidget(parent=self)
        self.layout().addWidget(self.sections_list_widget)

        scroll_area = QtWidgets.QScrollArea(parent=self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        scroll_area.setMinimumHeight(640)
        self.layout().addWidget(scroll_area)

        self.sections_stack_widget = SectionsStackWidget(parent=self)
        scroll_area.setWidget(self.sections_stack_widget)

    def _add_sections(self):
        """Adds the sections defined in the ``SECTIONS`` variable."""
        for s in get_sections():
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, s[u'name'].title())
            item.setData(common.DescriptionRole, s[u'description'])
            item.setData(QtCore.Qt.StatusTipRole, s[u'description'])
            item.setData(QtCore.Qt.ToolTipRole, s[u'description'])
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                150, common.INLINE_ICON_SIZE))
            self.sections_list_widget.addItem(item)
            self.sections_stack_widget.addWidget(s[u'cls'](parent=self))

                    # self.server_settings = ServersSettingsWidget(parent=self)
                    # self.application_settings = ApplicationSettingsWidget(parent=self)
                    # self.template_settings = TemplateSettingsWidget(parent=self)


    def _connectSignals(self):
        self.sections_list_widget.selectionModel().currentChanged.connect(self.current_changed)

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
