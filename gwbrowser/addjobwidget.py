# -*- coding: utf-8 -*-
"""This module defines the ``AddJobWidget``, the main widget used to add a
new job inside an existing server.

Assets are simple folder-structures, and the main placeholders for files generated
during digital production. Jobs are placeholders for addittional assets, eg.
shots, sequences, or build assets.

The job templates themselves are simple zip-files. Adding simply means unzipping
their contents into a specified directory.

"""

import functools
from PySide2 import QtWidgets, QtCore, QtGui

import gwbrowser.common as common
import gwbrowser.common_ui as common_ui

from gwbrowser.common_ui import PaintedButton, add_row
from gwbrowser.basecontextmenu import BaseContextMenu, contextmenu


class AddJobWidgetContextMenu(BaseContextMenu):
    """Context menu associated with the ``AddJobWidget``."""

    def __init__(self, parent=None):
        super(AddJobWidgetContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_reveal_item_menu()

    @contextmenu
    def add_reveal_item_menu(self, menu_set):
        """Menu for thumbnail operations."""
        menu_set['Reveal'] = {
            'text': u'Reveal destination',
            'action': functools.partial(common.reveal, self.parent().path)
        }
        return menu_set


class AddJobWidget(QtWidgets.QWidget):
    """Defines the widget used add a job to a selected server."""
    def __init__(self, parent=None):
        super(AddJobWidget, self).__init__(parent=parent)
        self.save_button = None
        self.cancel_button = None
        self.last_asset_added = None
        self.name_widget = None

        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_widget_pos = None

        self.installEventFilter(self)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self._createUI()
        self._connectSignals()

    def _createUI(self):
        """Creates the ``AddAssetsWidget``'s ui and layout."""
        common.set_custom_stylesheet(self)
        #
        QtWidgets.QVBoxLayout(self)
        o = 0
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)
        #
        row = common_ui.add_row(u'Job name:', padding=0, parent=self)

        self.name_widget = QtWidgets.QLineEdit(parent=self)
        self.name_widget.setFixedWidth(200)
        regex = QtCore.QRegExp(ur'[a-zA-Z0-9\_\-]+')
        validator = QtGui.QRegExpValidator(regex)
        self.name_widget.setValidator(validator)
        row.layout().addWidget(self.name_widget, 1)

        self.save_button = common_ui.PaintedButton(u'Add job', parent=self)
        self.cancel_button = common_ui.PaintedButton(u'Cancel', parent=self)
        row.layout().addWidget(self.save_button)
        row.layout().addWidget(self.cancel_button)

    def _connectSignals(self):
        self.save_button.clicked.connect(lambda: self.done(QtWidgets.QDialog.Accepted))
        self.cancel_button.clicked.connect(lambda: self.done(QtWidgets.QDialog.Rejected))

    @QtCore.Slot()
    def done(self, result):
        """Slot called by the check button to initiate the save."""
        if result == QtWidgets.QDialog.Rejected:
            return self.hide()

        mbox = QtWidgets.QMessageBox()
        mbox.setWindowTitle(u'Error adding asset')
        mbox.setIcon(QtWidgets.QMessageBox.Warning)
        mbox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        mbox.setDefaultButton(QtWidgets.QMessageBox.Ok)

        file_info = QtCore.QFileInfo(self.path)

        if not file_info.exists():
            mbox.setText(
                u'The destination folder does not exists.')
            mbox.setInformativeText(
                u'{} does not exist. Make sure a valid bookmark is activated before trying to add the asset.'.format(file_info.filePath()))
            return mbox.exec_()

        if not file_info.isWritable():
            mbox.setText(
                u'{} is not writable.'.format(file_info.filePath()))
            mbox.setInformativeText(
                u'The destination folder is not writeable. Check if you have permissions to create files and folders.')
            return mbox.exec_()

        if not self.name_widget.text():
            mbox.setText(u'The asset has no name.')
            mbox.setInformativeText(
                u'You must set a name before adding an asset.')
            return mbox.exec_()

        path = ur'{}/{}'.format(file_info.filePath(), self.name_widget.text())
        file_info = QtCore.QFileInfo(path)
        if file_info.exists():
            mbox.setText(u'"{}" already exists. Try again with a different name...'.format(
                self.name_widget.text()))
            mbox.setInformativeText(u'')
            return mbox.exec_()

        # Finally, let's actually create the asset
        try:
            common.create_asset_from_template(
                self.name_widget.text(), self.path, template=common.ProjectTemplate)
        except Exception as err:
            mbox.setText(u'An error occured when creating the asset:')
            mbox.setInformativeText('{}'.format(err))
            return mbox.exec_()

        mbox.setWindowTitle(u'Success')
        mbox.setText(u'Succesfully added "{}".'.format(
            self.name_widget.text()))
        mbox.setIcon(QtWidgets.QMessageBox.NoIcon)
        mbox.setStandardButtons(
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        mbox.setDefaultButton(QtWidgets.QMessageBox.No)
        mbox.setInformativeText(
            u'Do you want to add another asset?')
        if mbox.exec_() == QtWidgets.QMessageBox.Yes:
            self.name_widget.setText(u'')
            return
        else:
            self.last_asset_added = self.name_widget.text()
            common.reveal(u'{}/{}'.format(self.path, self.name_widget.text()))

        super(AddJobWidget, self).done(result)

    def contextMenuEvent(self, event):
        menu = AddJobWidgetContextMenu(parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()






if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = AddJobWidget()
    w.show()
    app.exec_()
