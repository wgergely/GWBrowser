"""Preferences"""

from PySide2 import QtCore, QtGui, QtWidgets

from gwbrowser.settings import local_settings
import gwbrowser.common as common
from gwbrowser.common_ui import PaintedButton, PaintedLabel, add_row, add_label, add_line_edit


SECTIONS = (
    {'name': u'Servers', 'description': u'Server preferences'},
    {'name': u'Application', 'description': u'Common preferences'},
    {'name': u'Folder templates', 'description': u'Various folder options'},
)


class ApplicationSettingsWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(ApplicationSettingsWidget, self).__init__(parent=parent)
        self.setDisabled(False)
        self._createUI()
        self._connectSignals()

    def _createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        label = PaintedLabel(u'GWBrowser Settings',
                             size=common.LARGE_FONT_SIZE, color=common.TEXT)
        self.layout().addWidget(label)

        import gwbrowser
        add_label(u'You\'re running GWBrowser v{}'.format(gwbrowser.__version__), parent=self)

        row = add_row(u'Update:', parent=self)
        self.check_updates = PaintedButton(u'Check for updates', width=200, parent=row)
        row.layout().addStretch(1)
        row.layout().addWidget(self.check_updates)

        row = add_row(u'Docs:', parent=self)
        self.show_help = PaintedButton(u'Show online documentation', width=200, parent=row)
        row.layout().addStretch(1)
        row.layout().addWidget(self.show_help)


        add_label(u'Asset & Job Folder Templates', parent=self)
        row = add_row(u'Show files:', parent=self)
        self.reveal_asset_template = PaintedButton(u'Show in explorer', width=200, parent=row)
        row.layout().addStretch(1)
        row.layout().addWidget(self.reveal_asset_template, 1)

        add_label(u'Slack shortcut', parent=self)
        row = add_row(u'Current URL:', parent=self)
        self.slack_url = add_line_edit(
            u'eg. https://mystudio.slack.com...', parent=row)
        row.layout().addWidget(self.slack_url, 1)
        self.slack_url.setText(common.SLACK_URL)
        self.slack_url.setReadOnly(True)

        self.layout().addStretch(1)

    def _connectSignals(self):
        import gwbrowser.versioncontrol.versioncontrol as vc
        self.check_updates.clicked.connect(vc.check)
        self.show_help.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(common.ABOUT_URL))
        self.reveal_asset_template.clicked.connect(self.show_asset_template)

    @QtCore.Slot()
    def show_asset_template(self):
        home = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DocumentsLocation)
        path = u'{}/GWBrowser/Asset.zip'.format(home)
        common.reveal(path)

class TemplateSettingsWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(TemplateSettingsWidget, self).__init__(parent=parent)
        self.slack_editor = None
        self.asset_identifier = None
        self.setDisabled(True)
        self._createUI()

    def _createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        label = PaintedLabel(u'Template Settings',
                             size=common.LARGE_FONT_SIZE, color=common.TEXT)
        self.layout().addWidget(label)

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


class ServersSettingsWidget(QtWidgets.QWidget):
    """Dialog to edit the server configuration.

    The server information is stored in the templates/servers.conf
    and is supplied by the ``common.Server`` class. This widget will  write
    directly into the configuration files.

    """

    def __init__(self, parent=None):
        super(ServersSettingsWidget, self).__init__(parent=parent)
        self.primary_mac_editor = None
        self.primary_win_editor = None
        self.primary_description = None

        self.backup_mac_editor = None
        self.backup_win_editor = None
        self.backup_description = None

        self.local_mac_editor = None
        self.local_win_description = None
        self.local_description = None

        self.setWindowTitle(u'Edit the default servers definitions')

        self._createUI()
        self._init_values()
        self._connectSignals()

    def _createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        label = PaintedLabel(u'Server Settings',
                             size=common.LARGE_FONT_SIZE, color=common.TEXT)
        self.layout().addWidget(label)

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
        regex = QtCore.QRegExp(u'[a-zA-Z0-9/_-]+')
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
        self.primary_mac_editor.textChanged.connect(self.save_settings)
        self.primary_win_editor.textChanged.connect(self.save_settings)
        self.primary_description.textChanged.connect(self.save_settings)
        self.backup_mac_editor.textChanged.connect(self.save_settings)
        self.backup_win_editor.textChanged.connect(self.save_settings)
        self.backup_description.textChanged.connect(self.save_settings)
        self.local_mac_editor.textChanged.connect(self.save_settings)
        self.local_win_editor.textChanged.connect(self.save_settings)
        self.local_description.textChanged.connect(self.save_settings)

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
            u'primary:mac': self.primary_mac_editor.text(),
            u'primary:win': self.primary_win_editor.text(),
            u'primary:description': self.primary_description.text(),
            u'backup:mac': self.backup_mac_editor.text(),
            u'backup:win': self.backup_win_editor.text(),
            u'backup:description': self.backup_description.text(),
            u'local:mac': self.local_mac_editor.text(),
            u'local:win': self.local_win_editor.text(),
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
                u'It usually is a network path of the server where jobs are stored, eg. //myserver/jobs')
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

        self._add_sections()
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

    def _add_sections(self):
        """Adds the sections defined in the ``SECTIONS`` variable."""
        for s in SECTIONS:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, s[u'name'].title())
            item.setData(common.DescriptionRole, s[u'description'])
            item.setData(QtCore.Qt.StatusTipRole, s[u'description'])
            item.setData(QtCore.Qt.ToolTipRole, s[u'description'])
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                150, common.INLINE_ICON_SIZE))
            self.addItem(item)


class SectionsStackWidget(QtWidgets.QStackedWidget):

    def __init__(self, parent=None):
        super(SectionsStackWidget, self).__init__(parent=parent)
        self.server_settings = ServersSettingsWidget(parent=self)
        self.application_settings = ApplicationSettingsWidget(parent=self)
        self.template_settings = TemplateSettingsWidget(parent=self)

        self.addWidget(self.server_settings)
        self.addWidget(self.application_settings)
        self.addWidget(self.template_settings)


class PreferencesWidget(QtWidgets.QWidget):
    """The main preferences widget."""

    def __init__(self, parent=None):
        super(PreferencesWidget, self).__init__(parent=parent)
        self.sections_list_widget = None
        self.sections_stack_widget = None
        self.setWindowTitle(u'GWBrowser Preferences')
        self.setWindowFlags(QtCore.Qt.Window)

        self._createUI()
        self._connectSignals()

    def _createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QHBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentsMargins(o, o, o, o)

        self.sections_list_widget = SectionSwitcherWidget(parent=self)
        self.layout().addWidget(self.sections_list_widget)
        self.sections_stack_widget = SectionsStackWidget(parent=self)
        self.layout().addWidget(self.sections_stack_widget)

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
