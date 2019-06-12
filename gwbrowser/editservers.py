# -*- coding: utf-8 -*-
"""``editserver.py`` is a utility widget to edit the server configuration.
"""

from PySide2 import QtWidgets, QtCore
import gwbrowser.common as common


class ServerEditor(QtWidgets.QDialog):
    """Dialog to edit the server configuration.

    The server information is stored in the templates/servers.conf
    and is supplied by the ``common.Server`` class. This widget will  write
    directly into the configuration files.

    """

    def __init__(self, parent=None):
        super(ServerEditor, self).__init__(parent=parent)
        self.primary_mac_editor = None
        self.primary_win_editor = None
        self.primary_description = None

        self.backup_mac_editor = None
        self.backup_win_editor = None
        self.backup_description = None

        self.local_mac_editor = None
        self.local_win_description = None
        self.local_description = None

        self.ok_button = None
        self.cancel_button = None

        self.setWindowTitle(u'Edit the default servers definitions')
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

        self._createUI()
        self._connectSignals()
        self._initValues()

    def _createUI(self):
        def hrow(parent=None):
            """macro for adding a new row"""
            w = QtWidgets.QWidget(parent=parent)
            QtWidgets.QHBoxLayout(w)
            w.layout().setContentsMargins(0, 0, 0, 0)
            w.layout().setSpacing(common.INDICATOR_WIDTH)
            w.layout().setAlignment(QtCore.Qt.AlignCenter)
            w.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding,
            )
            w.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
            w.setAttribute(QtCore.Qt.WA_NoBackground)
            w.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            return w

        def add_label(text, parent=None):
            label = QtWidgets.QLabel(text, parent=parent)
            label.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
            label.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Expanding
            )
            label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
            self.layout().addWidget(label, 0)

        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(common.INDICATOR_WIDTH)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)

        # Primary server
        add_label(u'Primary server')
        # Mac
        row = hrow(parent=self)
        self.layout().addWidget(row, 1)
        label = QtWidgets.QLabel(u'MacOS')
        label.setFixedWidth(80)

        label.setDisabled(True)
        row.layout().addWidget(label, 0)

        self.primary_mac_editor = QtWidgets.QLineEdit(parent=self)
        self.primary_mac_editor.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        row.layout().addWidget(self.primary_mac_editor, 1)

        # Win
        row = hrow(parent=self)
        self.layout().addWidget(row, 1)
        label = QtWidgets.QLabel(u'Windows')
        label.setFixedWidth(80)

        label.setDisabled(True)
        row.layout().addWidget(label, 0)

        self.primary_win_editor = QtWidgets.QLineEdit(parent=self)
        self.primary_win_editor.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        row.layout().addWidget(self.primary_win_editor, 1)

        # Description
        row = hrow(parent=self)
        self.layout().addWidget(row, 1)
        label = QtWidgets.QLabel(u'Description')
        label.setFixedWidth(80)

        label.setDisabled(True)
        row.layout().addWidget(label, 0)

        self.primary_description = QtWidgets.QLineEdit(parent=self)
        self.primary_description.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        row.layout().addWidget(self.primary_description, 1)

        # Backup server
        add_label(u'Backup server')
        # Mac
        row = hrow(parent=self)
        self.layout().addWidget(row, 1)
        label = QtWidgets.QLabel(u'MacOS')
        label.setFixedWidth(80)

        label.setDisabled(True)
        row.layout().addWidget(label, 0)

        self.backup_mac_editor = QtWidgets.QLineEdit(parent=self)
        self.backup_mac_editor.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        row.layout().addWidget(self.backup_mac_editor, 1)

        # Win
        row = hrow(parent=self)
        self.layout().addWidget(row, 1)
        label = QtWidgets.QLabel(u'Windows')
        label.setFixedWidth(80)

        label.setDisabled(True)
        row.layout().addWidget(label, 0)

        self.backup_win_editor = QtWidgets.QLineEdit(parent=self)
        self.backup_win_editor.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        row.layout().addWidget(self.backup_win_editor, 1)

        # Description
        row = hrow(parent=self)
        self.layout().addWidget(row, 1)
        label = QtWidgets.QLabel(u'Description')
        label.setFixedWidth(80)

        label.setDisabled(True)
        row.layout().addWidget(label, 0)

        self.backup_description = QtWidgets.QLineEdit(parent=self)
        self.backup_description.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        row.layout().addWidget(self.backup_description, 1)

        # Backup server
        add_label(u'Local work-folder')
        # Mac
        row = hrow(parent=self)
        self.layout().addWidget(row, 1)
        label = QtWidgets.QLabel(u'MacOS')
        label.setFixedWidth(80)

        label.setDisabled(True)
        row.layout().addWidget(label, 0)

        self.local_mac_editor = QtWidgets.QLineEdit(parent=self)
        self.local_mac_editor.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        row.layout().addWidget(self.local_mac_editor, 1)

        # Win
        row = hrow(parent=self)
        self.layout().addWidget(row, 1)
        label = QtWidgets.QLabel(u'Windows')
        label.setFixedWidth(80)

        label.setDisabled(True)
        row.layout().addWidget(label, 0)

        self.local_win_editor = QtWidgets.QLineEdit(parent=self)
        self.local_win_editor.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        row.layout().addWidget(self.local_win_editor, 1)

        # Description
        row = hrow(parent=self)
        self.layout().addWidget(row, 1)
        label = QtWidgets.QLabel(u'Description')
        label.setFixedWidth(80)

        label.setDisabled(True)
        row.layout().addWidget(label, 0)

        self.local_description = QtWidgets.QLineEdit(parent=self)
        self.local_description.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)
        row.layout().addWidget(self.local_description, 1)


        self.ok_button = QtWidgets.QPushButton(u'Ok')
        self.cancel_button = QtWidgets.QPushButton(u'Cancel')
        row = hrow(parent=self)
        row.layout().addWidget(self.ok_button, 1)
        row.layout().addWidget(self.cancel_button, 1)
        self.layout().addWidget(row, 1)

    def _connectSignals(self):
        pass
        self.ok_button.clicked.connect(lambda: self.done(0))
        self.cancel_button.clicked.connect(self.reject)

    def _initValues(self):
        parser = common.Server.conf()
        def get(section, key):
            try:
                return parser.get(section, key)
            except:
                return ''

        self.primary_mac_editor.setText(get('primary', 'mac'))
        self.primary_win_editor.setText(get('primary', 'win'))
        self.primary_description.setText(get('primary', 'description'))

        self.backup_mac_editor.setText(get('backup', 'mac'))
        self.backup_win_editor.setText(get('backup', 'win'))
        self.backup_description.setText(get('backup', 'description'))

        self.local_mac_editor.setText(get('local', 'mac'))
        self.local_win_editor.setText(get('local', 'win'))
        self.local_description.setText(get('local', 'description'))

    def sizeHint(self):
        return QtCore.QSize(500, 500)

    def reject(self):
        self.done(1)

    @QtCore.Slot()
    def done(self, r=0):
        if r == 0:
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
            if not all(values.values()):
                mbox = QtWidgets.QMessageBox(parent=self)
                mbox.setWindowTitle(u'Error adding asset')
                mbox.setIcon(QtWidgets.QMessageBox.Warning)
                mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                mbox.setDefaultButton(QtWidgets.QMessageBox.Ok)
                mbox.setWindowTitle(u'Missing value')

                mbox.setText(u'All fields must be filled out!')
                mbox.setInformativeText(u'Make sure all the fields have been filled out with a path to a server, and/or a description')
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
            return super(ServerEditor, self).done(r)
            
        return super(ServerEditor, self).done(r)

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = ServerEditor()
    w.exec_()
