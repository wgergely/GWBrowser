# -*- coding: utf-8 -*-
"""Defines ``UpdateConfigWidget``, a popup dialog used add a new path to the local configuration file.

Note:
    The widget itself makes no changes to the configurations file, but rather sets internal attributes that
    can be used later tpo modfiy the configrations file.

    The final path is a composit of [server]/[job]/[root].

Example:
    .. code-block:: python
        :linenos:

        widget = UpdateConfigWidget()
        widget.exec_()
        print widget.server # None or the selected server, eg //gordo/jobs


Attributes:
    server (str):   The path to the server. `None` if invalid.
    job (str):      The name of the job folder. `None` if invalid.
    root (str):     A relative path to the folder where the assets are located. `None` if invalid.


"""


import re

from PySide2 import QtWidgets, QtCore, QtGui

import mayabrowser.common as common
from mayabrowser.configparsers import local_settings
from mayabrowser.delegate import BaseDelegate

# pylint: disable=E1101, C0103, R0913, I1101


class ComboBoxItemDelegate(BaseDelegate):
    """Delegate used to render simple list items."""

    def __init__(self, parent=None):
        super(ComboBoxItemDelegate, self).__init__(parent=parent)

    def paint(self, painter, option, index):
        """The main paint method."""
        args = self._get_paint_args(painter, option, index)

        self.paint_background(*args)
        self.paint_separators(*args)
        self.paint_data(*args)
        self.paint_selection_indicator(*args)
        self.paint_active_indicator(*args)
        self.paint_focus(*args)

    def paint_data(self, *args):
        painter, option, index, selected, _, _, _, _ = args
        disabled = (index.flags() == QtCore.Qt.NoItemFlags)

        painter.save()

        font = QtGui.QFont('Roboto')
        font.setBold(True)
        font.setPointSize(8)
        painter.setFont(font)

        rect = QtCore.QRect(option.rect)
        rect.setLeft(common.MARGIN)
        rect.setRight(option.rect.right())

        if selected:
            painter.setPen(QtGui.QPen(common.TEXT_SELECTED))
        else:
            painter.setPen(QtGui.QPen(common.TEXT))

        if disabled:
            painter.setPen(QtGui.QPen(common.TEXT_DISABLED))

        painter.setBrush(QtCore.Qt.NoBrush)

        metrics = QtGui.QFontMetrics(painter.font())
        text = index.data(QtCore.Qt.DisplayRole)
        text = metrics.elidedText(
            re.sub(r'[\W\d\_]+', ' ', text.upper()),
            QtCore.Qt.ElideRight,
            rect.width()
        )
        if disabled:
            text = metrics.elidedText(
                '{}  |  Offline'.format(index.data(QtCore.Qt.DisplayRole)),
                QtCore.Qt.ElideRight,
                rect.width()
            )

        painter.drawText(
            rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft | QtCore.Qt.TextWordWrap,
            text
        )

        painter.restore()

    def sizeHint(self, option, index):
        return QtCore.QSize(200, common.ROW_HEIGHT * 0.66)


class UpdateConfigWidget(QtWidgets.QDialog):
    """Interface to update the path querried."""

    def __init__(self, parent=None):
        """Initialises the widget with optional default values."""
        super(UpdateConfigWidget, self).__init__(parent=parent)

        common.set_custom_stylesheet(self)

        self.installEventFilter(self)
        self.setWindowTitle('Add location')
        self._createUI()
        self._connectSignals()
        self._set_initial_values()

        self._root = None


    def get_choice(self):
        """Returns the currently selected items."""
        return (
            self.pick_server_widget.currentData(QtCore.Qt.UserRole),
            self.pick_job_widget.currentData(QtCore.Qt.UserRole),
            self._root
        )

    def _createUI(self):
        """Creates the UI layout.

        +------------------+------------------+
        |                  |                  |
        |                  |                  |
        |   pathsettings   |                  |
        |                  |                  |
        |                  |                  |
        +------------------+------------------+

        """
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(
            common.MARGIN,
            common.MARGIN,
            common.MARGIN,
            common.MARGIN
        )

        self.pathsettings = QtWidgets.QWidget()
        QtWidgets.QVBoxLayout(self.pathsettings)
        self.pathsettings.layout().setContentsMargins(0, 0, 0, 0)
        self.pathsettings.layout().setSpacing(common.MARGIN * 0.33)


        # Server
        self.pick_server_widget = QtWidgets.QComboBox()
        view = QtWidgets.QListWidget()  # Setting a custom view here
        self.pick_server_widget.setModel(view.model())
        self.pick_server_widget.setView(view)
        self.pick_server_widget.setFrame(False)
        self.pick_server_widget.setDuplicatesEnabled(False)
        self.pick_server_widget.setItemDelegate(
            ComboBoxItemDelegate(self.pick_server_widget))

        self.pick_job_widget = QtWidgets.QComboBox()
        view = QtWidgets.QListWidget()  # Setting a custom view here
        self.pick_job_widget.setModel(view.model())
        self.pick_job_widget.setView(view)
        self.pick_job_widget.setFrame(False)
        self.pick_job_widget.setDuplicatesEnabled(False)
        self.pick_job_widget.setItemDelegate(
            ComboBoxItemDelegate(self.pick_job_widget))

        self.pick_root_widget = QtWidgets.QPushButton('Select folder')

        row = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row)

        self.ok_button = QtWidgets.QPushButton('Add bookmark')
        self.ok_button.setDisabled(True)
        self.cancel_button = QtWidgets.QPushButton('Cancel')

        row.layout().addWidget(self.ok_button, 1)
        row.layout().addWidget(self.cancel_button, 1)


        # Adding it all together

        path = '{}/rsc/bookmark.png'.format(QtCore.QFileInfo(__file__).dir().path())
        pixmap = QtGui.QPixmap()
        pixmap.load(path)
        pixmap = pixmap.scaledToWidth(128, QtCore.Qt.SmoothTransformation)
        label = QtWidgets.QLabel()
        label.setPixmap(pixmap)
        self.layout().addWidget(label)
        self.layout().addSpacing(common.MARGIN)
        self.layout().addWidget(self.pathsettings)

        self.pathsettings.layout().addWidget(QtWidgets.QLabel('Server'), 1)
        label = QtWidgets.QLabel(
            'Select the network path the job is located at:')
        label.setWordWrap(True)
        label.setDisabled(True)
        self.pathsettings.layout().addWidget(label, 0)
        self.pathsettings.layout().addWidget(self.pick_server_widget, 1)
        self.pathsettings.layout().addStretch(1)
        self.pathsettings.layout().addWidget(QtWidgets.QLabel('Job'), 1)
        label = QtWidgets.QLabel(
            'Select the job:')
        label.setWordWrap(True)
        label.setDisabled(True)
        self.pathsettings.layout().addWidget(label, 0)
        self.pathsettings.layout().addWidget(self.pick_job_widget, 1)
        self.pathsettings.layout().addStretch(1)
        self.pathsettings.layout().addWidget(QtWidgets.QLabel('Assets'), 1)
        label = QtWidgets.QLabel(
            'Select the folder inside the Job containing a list of shots and/or assets:')
        label.setWordWrap(True)
        label.setDisabled(True)
        self.pathsettings.layout().addWidget(label, 0)
        self.pathsettings.layout().addWidget(self.pick_root_widget, 1)
        self.pathsettings.layout().addStretch(10)
        self.pathsettings.layout().addWidget(row, 1)
        self.pathsettings.setMinimumWidth(300)

    def _connectSignals(self):
        self.pick_server_widget.currentIndexChanged.connect(self.serverChanged)
        self.pick_job_widget.currentIndexChanged.connect(self.jobChanged)
        self.pick_root_widget.pressed.connect(self._pick_root)

    def _add_servers(self):
        self.pick_server_widget.clear()

        for server in common.SERVERS:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, server['nickname'])
            item.setData(QtCore.Qt.EditRole, server['nickname'])
            item.setData(QtCore.Qt.StatusTipRole,
                         '{}\n{}'.format(server['nickname'], server['path']))
            item.setData(QtCore.Qt.ToolTipRole,
                         '{}\n{}'.format(server['nickname'], server['path']))
            item.setData(QtCore.Qt.UserRole, server['path'])
            item.setData(QtCore.Qt.PathRole, QtCore.QFileInfo(server['path']))
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                200, common.ROW_BUTTONS_HEIGHT))

            self.pick_server_widget.view().addItem(item)

            if not item.data(QtCore.Qt.PathRole).exists():
                item.setFlags(QtCore.Qt.NoItemFlags)

    def _add_jobs(self, dir):
        dir.setFilter(
            QtCore.QDir.NoDotAndDotDot |
            QtCore.QDir.Dirs |
            QtCore.QDir.NoSymLinks |
            QtCore.QDir.Readable
        )

        self.pick_job_widget.clear()

        for file_info in dir.entryInfoList():
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.DisplayRole, file_info.fileName())
            item.setData(QtCore.Qt.EditRole, file_info.fileName())
            item.setData(QtCore.Qt.StatusTipRole, file_info.filePath())
            item.setData(QtCore.Qt.ToolTipRole, file_info.filePath())
            item.setData(QtCore.Qt.UserRole, file_info.fileName())
            item.setData(QtCore.Qt.PathRole, file_info)
            item.setData(QtCore.Qt.SizeHintRole, QtCore.QSize(
                200, common.ROW_BUTTONS_HEIGHT))

            self.pick_job_widget.view().addItem(item)

    def _pick_root(self):
        """Method to select a the root folder of the assets. Called by the Assets push button."""
        self._root = None

        dialog = QtWidgets.QFileDialog()
        dialog.setViewMode(QtWidgets.QFileDialog.Detail)
        file_info = self.pick_job_widget.currentData(QtCore.Qt.PathRole)

        path = dialog.getExistingDirectory(
            self,
            'Pick the location of the assets folder',
            file_info.filePath(),
            QtWidgets.QFileDialog.ShowDirsOnly |
            QtWidgets.QFileDialog.DontResolveSymlinks |
            QtWidgets.QFileDialog.DontUseCustomDirectoryIcons |
            QtWidgets.QFileDialog.HideNameFilterDetails |
            QtWidgets.QFileDialog.ReadOnly
        )
        if not path:
            self.ok_button.setDisabled(True)
            self.pick_root_widget.setText('Select folder')
            self._root = None
            return

        self.ok_button.setDisabled(False)

        dir = QtCore.QDir(path)
        dir.setFilter(
            QtCore.QDir.NoDotAndDotDot |
            QtCore.QDir.Dirs |
            QtCore.QDir.NoSymLinks |
            QtCore.QDir.Readable
        )


        # Counting the number assets found
        count = 0
        for file_info in dir.entryInfoList():
            dir = QtCore.QDir(file_info.filePath())
            dir.setFilter(QtCore.QDir.Files)
            dir.setNameFilters(('*.mel',))
            if dir.entryInfoList():
                count += 1

        # Removing the server and job name from the selection
        path = path.replace(self.pick_job_widget.currentData(QtCore.Qt.PathRole).filePath(), '')
        path = path.lstrip('/').rstrip('/')

        # Setting the internal root variable
        self._root = path

        if count:
            self.pick_root_widget.setStyleSheet('color: rgba({},{},{},{});'.format(*common.TEXT.getRgb()))
        else:
            self.pick_root_widget.setStyleSheet('color: rgba(250, 100, 50, 255);')

        path = '{}:  {} assets'.format(path, count)
        self.pick_root_widget.setText(path)


    def jobChanged(self, idx):
        """Triggered when the pick_job_widget selection changes."""
        self._root = None
        self.pick_root_widget.setStyleSheet('color: rgba(250, 100, 50, 255);')
        self.pick_root_widget.setText('Select folder')

    def serverChanged(self, idx):
        """Triggered when the pick_server_widget selection changes."""
        if idx < 0:
            self.pick_job_widget.clear()
            return

        item = self.pick_server_widget.view().item(idx)
        dir = QtCore.QDir(item.data(QtCore.Qt.PathRole).filePath())
        self._add_jobs(dir)

    def _set_initial_values(self):
        """Sets the initial values in the widget."""
        self._add_servers()

        # Select the currently active server
        if local_settings.value('activepath/server'):
            idx = self.pick_server_widget.findData(
                local_settings.value('activepath/server'),
                role=QtCore.Qt.UserRole,
                flags=QtCore.Qt.MatchFixedString
            )
            self.pick_server_widget.setCurrentIndex(idx)

        # Select the currently active server
        if local_settings.value('activepath/job'):
            idx = self.pick_job_widget.findData(
                local_settings.value('activepath/job'),
                role=QtCore.Qt.UserRole,
                flags=QtCore.Qt.MatchFixedString
            )
            self.pick_job_widget.setCurrentIndex(idx)



if __name__ == '__main__':
    a = QtWidgets.QApplication([])
    a.w = UpdateConfigWidget()
    a.w.exec_()
    # a.exec_()
