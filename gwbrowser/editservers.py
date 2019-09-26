# -*- coding: utf-8 -*-
"""``editserver.py`` is a utility widget to edit the server configuration.
"""

from PySide2 import QtWidgets, QtCore
import gwbrowser.common as common
from gwbrowser.common_ui import (
    PaintedButton, PaintedLabel, add_row, add_label, add_line_edit)


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

        self.save_button = None

        self.setWindowTitle(u'Edit the default servers definitions')
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

        self._createUI()
        self._connectSignals()
        self._init_values()

    def _createUI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        label = PaintedLabel(u'Servers Settings', size=common.LARGE_FONT_SIZE, color=common.TEXT)
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

        # Save
        row = add_row(u'', parent=self, padding=o)
        self.save_button = PaintedButton(u'Save', parent=row)
        row.layout().addWidget(self.save_button, 1)
        self.layout().addStretch(1)
        self.layout().addWidget(row)

    def _connectSignals(self):
        self.save_button.clicked.connect(self.save_settings)

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


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = ServersSettingsWidget()
    w.show()
    app.exec_()
