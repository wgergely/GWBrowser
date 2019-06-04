# -*- coding: utf-8 -*-
"""This module defines the ``AddAssetWidget``, the main widget used to add a
new asset to an existing bookmark.

Assets are simple folder-structures, and the main placeholders for files generated
during digital production.

The asset templates themselves are simple zip-files. Adding simply means unzipping
their contents into a specified directory.

"""

import re
import functools
from PySide2 import QtWidgets, QtCore

import gwbrowser.common as common
from gwbrowser.addbookmarkswidget import PaintedLabel
from gwbrowser.addfilewidget import ThumbnailButton
from gwbrowser.addfilewidget import DescriptionEditor, NameEditor
from gwbrowser.addfilewidget import Check
from gwbrowser.addfilewidget import SaverHeaderWidget
from gwbrowser.basecontextmenu import BaseContextMenu, contextmenu
from gwbrowser.standalonewidgets import CloseButton
import gwbrowser.gwscandir as gwscandir
import gwbrowser.settings as Settings


class AddAssetWidgetContextMenu(BaseContextMenu):
    """Context menu associated with the ``AddAssetWidget``."""

    def __init__(self, parent=None):
        super(AddAssetWidgetContextMenu, self).__init__(
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


class AddAssetWidget(QtWidgets.QDialog):
    """Defines the widget used add an asset to the currently active bookmark."""
    shutdown = QtCore.Signal()

    def __init__(self, path, parent=None):
        super(AddAssetWidget, self).__init__(parent=parent)
        self._path = path
        self.last_asset_added = None
        self.thumbnail_image = None

        self.checkmark_widget = None
        self.name_widget = None
        self.thumbnail_widget = None
        self.description_widget = None

        self.move_in_progress = False
        self.move_start_event_pos = None
        self.move_start_widget_pos = None

        self.setWindowTitle(u'Add asset')
        self.setMouseTracking(True)
        self.installEventFilter(self)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Window)

        self._createUI()
        self._connectSignals()

    @property
    def path(self):
        """The active bookmark"""
        return self._path

    def completer_keywords(self):
        """We can give some hints when naming assets using auto-completion.
        The will contain the already existing folder names and some predefined
        shot, sequence names.

        """
        kw = []
        for entry in gwscandir.scandir(self.path):
            kw.append(entry.name)
        kw.append(u'sh010')
        kw.append(u'lay_sh010')
        kw.append(u'ani_sh010')
        kw.append(u'fx_sh010')
        kw.append(u'seq010_sh010')
        kw.append(u'seq010_ani_sh010')
        kw.append(u'seq010_fx_sh010')
        kw.append(u'seq010_lay_sh010')
        return kw

    def _createUI(self):
        """Creates the ``AddAssetsWidget``'s ui and layout."""
        common.set_custom_stylesheet(self)
        #
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(
            common.INDICATOR_WIDTH, common.INDICATOR_WIDTH,
            common.INDICATOR_WIDTH, common.INDICATOR_WIDTH)
        self.layout().setSpacing(common.INDICATOR_WIDTH)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        #
        self.setFixedWidth(common.WIDTH)

        #
        mainrow = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(mainrow)
        self.layout().addWidget(mainrow)
        mainrow.layout().setContentsMargins(0, 0, 0, 0)
        mainrow.layout().setSpacing(common.INDICATOR_WIDTH)
        mainrow.layout().setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        # top label
        label = PaintedLabel(u'Add new asset', size=common.LARGE_FONT_SIZE)
        mainrow.layout().addSpacing(common.MARGIN / 2)
        mainrow.layout().addWidget(label, 0)

        #
        mainrow = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(mainrow)
        mainrow.layout().setContentsMargins(0, 0, 0, 0)
        mainrow.layout().setSpacing(common.INDICATOR_WIDTH)
        mainrow.layout().setAlignment(QtCore.Qt.AlignCenter)
        #
        self.thumbnail_widget = ThumbnailButton(parent=self)
        self.thumbnail_widget.setFixedSize(
            common.ASSET_ROW_HEIGHT, common.ASSET_ROW_HEIGHT)
        mainrow.layout().addWidget(self.thumbnail_widget)
        self.layout().addWidget(mainrow)
        #
        column = QtWidgets.QWidget()
        QtWidgets.QVBoxLayout(column)
        column.layout().setContentsMargins(0, 0, 0, 0)
        column.layout().setSpacing(0)
        column.layout().setAlignment(QtCore.Qt.AlignCenter)
        mainrow.layout().addWidget(column)

        # Row 1
        row = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row)
        row.layout().setContentsMargins(0, 0, 0, 0)
        row.layout().setSpacing(common.INDICATOR_WIDTH)
        row.layout().setAlignment(QtCore.Qt.AlignCenter)
        column.layout().addWidget(row, 1)

        self.name_widget = NameEditor(parent=self)
        # Settings the completer associated with the Editor widget
        completer = QtWidgets.QCompleter(
            sorted(self.completer_keywords()), self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        completer.setCompletionMode(
            QtWidgets.QCompleter.InlineCompletion)
        self.name_widget.setCompleter(completer)

        self.description_widget = DescriptionEditor(parent=self)
        self.checkmark_widget = Check(parent=self)

        row.layout().addWidget(self.name_widget, 1)
        row.layout().addWidget(self.description_widget, 2)

        mainrow.layout().addWidget(self.checkmark_widget)
        self.layout().insertWidget(0, SaverHeaderWidget(parent=self))
        self.layout().addSpacing(common.MARGIN)

    def _connectSignals(self):
        self.checkmark_widget.clicked.connect(lambda: self.done(
            QtWidgets.QDialog.Accepted), type=QtCore.Qt.QueuedConnection)
        self.name_widget.textEdited.connect(self.validate_text)
        self.thumbnail_widget.clicked.connect(
            self.thumbnail_widget.pick_thumbnail)
        self.shutdown.connect(self.close)
        closebutton = self.findChild(CloseButton)
        closebutton.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected), type=QtCore.Qt.QueuedConnection)

    @QtCore.Slot(unicode)
    def validate_text(self, text):
        """Strips all invalid characters from the input string."""
        cp = self.name_widget.cursorPosition()
        _text = re.sub(ur'[^a-z0-9\_\-]', u'_', text, flags=re.IGNORECASE)
        _text = re.sub(ur'[_]{2,}', u'_', _text)
        _text = re.sub(ur'[-]{2,}', u'-', _text)
        if len(_text) > 35:
            _text = _text[0:35]
        self.name_widget.setText(_text)
        self.name_widget.setCursorPosition(cp)

    def done(self, result):
        """Slot called by the check button to create a new asset."""
        if result == QtWidgets.QDialog.Rejected:
            return super(AddAssetWidget, self).done(result)

        mbox = QtWidgets.QMessageBox(parent=self)
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
                u'You must set a name before adding an asset. The description and the thumbnails are optional, albeit highly recommended to add these as well. ')
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
                self.name_widget.text(), self.path, template=common.MayaAssetTemplate)
            self.save_thumbnail_and_description()
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
            self.description_widget.setText(u'')
            self.thumbnail_widget.reset_thumbnail()
            return
        else:
            self.last_asset_added = self.name_widget.text()
            common.reveal(u'{}/{}'.format(self.path, self.name_widget.text()))
        super(AddAssetWidget, self).done(result)

    def save_thumbnail_and_description(self):
        """Saves the selected thumbnail and description in the config file."""
        bindex = self.parent().widget(0).model().sourceModel().active_index()
        if not bindex.isValid():
            return

        server, job, root = bindex.data(common.ParentRole)
        asset = self.name_widget.text()
        settings = Settings.AssetSettings(
            QtCore.QModelIndex(), args=(server, job, root, asset))

        description = self.description_widget.text()
        if description:
            settings.setValue(u'config/description', description)
        if self.thumbnail_widget.image:
            if not self.thumbnail_widget.image.isNull():
                self.thumbnail_widget.image.save(settings.thumbnail_path())

    def contextMenuEvent(self, event):
        menu = AddAssetWidgetContextMenu(parent=self)
        pos = event.pos()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    w = AddAssetWidget(ur'C:\temp\projects\job1\build')
    w.exec_()
