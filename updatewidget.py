# -*- coding: utf-8 -*-
"""This is a widget to set the queried path of the collector.

Attributes:
    server (str):   The path to the server. None if invalid.
    job (str):      The name of the job folder. None if invalid.
    root (str):     The name of the projects root folder. None if invalid.

The final path is a composit of [path]/[job]/[root].

"""
from PySide2 import QtWidgets, QtCore
# pylint: disable=E1101, C0103, R0913, I1101


class UpdateConfigWidget(QtWidgets.QDialog):
    """Interface to update the path querried."""

    def __init__(self, server=None, job=None, root=None, parent=None):
        """Initialises the widget with optional default values."""
        super(UpdateConfigWidget, self).__init__(parent=parent)
        self.server = None
        self.job = None
        self.root = None

        self.installEventFilter(self)
        self.setWindowTitle('Configure Maya Browser')
        self._createUI()
        self._connectSignals()
        self._setInitValues(server, job, root)

    def eventFilter(self, widget, event):
        if event.type() != QtCore.QEvent.KeyPress:
            return False
        if event.key() == QtCore.Qt.Key_Enter:
            return True
        elif event.key() == QtCore.Qt.Key_Return:
            return True
        return False

    def _createUI(self):
        """Creates the ui layout."""
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(18, 18, 18, 18)
        self.setFixedWidth(360)

        # row1
        self.pick_server_line = QtWidgets.QLineEdit('//gordo/jobs')
        self.pick_server_line.setPlaceholderText('Enter path to the server...')
        self.pick_server_feedback = QtWidgets.QLabel('Server not selected.')
        self.pick_server_feedback.setAlignment(QtCore.Qt.AlignRight)
        self.pick_job_menu = QtWidgets.QComboBox()
        self.pick_root_line = QtWidgets.QLineEdit('/projects')
        self.pick_root_line.setPlaceholderText(
            'Enter path to the projects folder...')
        self.pick_root_feedback = QtWidgets.QLabel('')
        self.pick_root_feedback.setAlignment(QtCore.Qt.AlignRight)

        row = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row)
        self.ok_button = QtWidgets.QPushButton('Set')
        self.cancel_button = QtWidgets.QPushButton('Cancel')
        row.layout().addWidget(self.ok_button, 1)
        row.layout().addWidget(self.cancel_button, 1)

        self.layout().addWidget(QtWidgets.QLabel('Server'), 1)

        label = QtWidgets.QLabel(
            'Local network path pointing to where the studio\'s jobs are located (press enter to set).')
        label.setWordWrap(True)
        label.setDisabled(True)
        self.layout().addWidget(label, 0)

        self.layout().addWidget(self.pick_server_line, 1)
        self.layout().addWidget(self.pick_server_feedback, 1)
        self.layout().addWidget(QtWidgets.QLabel('Job'), 1)

        label = QtWidgets.QLabel(
            'The name of the current job.')
        label.setWordWrap(True)
        label.setDisabled(True)
        self.layout().addWidget(label, 0)

        self.layout().addWidget(self.pick_job_menu, 1)
        self.layout().addWidget(QtWidgets.QLabel('\n'), 1)
        self.layout().addWidget(QtWidgets.QLabel('Projects'), 1)

        label = QtWidgets.QLabel(
            'A relative path of where the maya projects located inside the current job (press enter to set).')
        label.setWordWrap(True)
        label.setDisabled(True)
        self.layout().addWidget(label, 0)

        self.layout().addWidget(self.pick_root_line, 1)
        self.layout().addWidget(self.pick_root_feedback, 1)
        self.layout().addStretch(6)
        self.layout().addWidget(row, 1)

    def _connectSignals(self):
        self.pick_server_line.returnPressed.connect(self.serverEdited)
        self.pick_server_line.returnPressed.connect(self.jobChanged)

        self.pick_job_menu.currentIndexChanged.connect(self.jobChanged)
        self.pick_job_menu.currentIndexChanged.connect(self.rootEdited)

        self.pick_root_line.returnPressed.connect(self.rootEdited)

        self.ok_button.clicked.connect(self.okClicked)
        self.cancel_button.clicked.connect(self.cancelClicked)

    def _setInitValues(self, server, job, root):
        """Sets the initial values in the widget."""
        if not server:
            self.serverEdited()
            return
        self.pick_server_line.setText(server)
        self.serverEdited()
        if not job:
            return
        self.pick_job_menu.setCurrentText(job)
        if job:
            self.pick_root_line.setText(root)
            self.rootEdited()

    def okClicked(self):
        self.done(1)

    def cancelClicked(self):
        self.done(0)

    def serverEdited(self):
        """Triggered when editing the server field."""
        text = self.pick_server_line.text()
        file_info = QtCore.QFileInfo()
        file_info.setFile(text)

        if file_info.exists():
            self.server = file_info.filePath()
            self.pick_server_feedback.setText(
                '{} is valid.'.format(file_info.filePath())
            )
            self.pick_server_feedback.setStyleSheet('color: green;')

            # Adding job folders.
            d = QtCore.QDir(file_info.filePath())
            dirlist = d.entryInfoList(
                sort=QtCore.QDir.Name,
                filters=QtCore.QDir.AllDirs | QtCore.QDir.NoDotAndDotDot
            )
            current = self.pick_job_menu.currentText()
            self.pick_job_menu.clear()
            if not dirlist:
                self.pick_job_menu.setDisabled(True)
                self.ok_button.setDisabled(True)
                return
            for info in dirlist:
                self.pick_job_menu.addItem(
                    info.fileName(),
                    userData=info.filePath()
                )
            self.pick_job_menu.setCurrentText(current)
            self.pick_job_menu.setDisabled(False)
            self.ok_button.setDisabled(False)
            return
        else:
            self.server = None
            self.pick_job_menu.clear()
            self.pick_job_menu.setDisabled(True)
            self.ok_button.setDisabled(True)
            self.pick_server_feedback.setText(
                'Path does not exist.'
            )
            self.pick_server_feedback.setStyleSheet('color: red;')
            return

    def jobChanged(self):
        data = self.pick_job_menu.currentData(QtCore.Qt.UserRole)
        if data:
            self.pick_root_line.setDisabled(False)
            self.pick_root_feedback.setDisabled(False)
            self.ok_button.setDisabled(False)
            file_info = QtCore.QFileInfo(data)
            if file_info.exists():
                self.job = file_info.baseName()
        else:
            self.pick_root_line.setDisabled(True)
            self.pick_root_feedback.setDisabled(True)
            self.ok_button.setDisabled(True)
            self.job = None

    def rootEdited(self):
        """Triggered when editing the server field."""
        text = self.pick_root_line.text()
        file_info = QtCore.QFileInfo()
        file_info.setFile(
            '{}/{}'.format(
                self.pick_job_menu.currentData(QtCore.Qt.UserRole),
                text
            )
        )
        if file_info.exists():
            self.ok_button.setDisabled(False)
            job_info = QtCore.QFileInfo(self.pick_job_menu.currentData(QtCore.Qt.UserRole))
            self.root = file_info.filePath().replace(job_info.filePath(), '').strip('/')
            self.pick_root_feedback.setText(
                '{}\nAll good!'.format(file_info.filePath())
            )
            self.pick_root_feedback.setStyleSheet('color: green;')
        else:
            self.ok_button.setDisabled(True)
            self.root = None
            self.pick_root_feedback.setText(
                '{}\nPath does not exist.'.format(file_info.filePath())
            )
            self.pick_root_feedback.setStyleSheet('color: red;')
