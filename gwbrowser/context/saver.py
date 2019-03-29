# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903, C0330

"""Browser's custom saver widget. The widget will take into consideration the
currently set active paths and will try to return an appropiate save-path.

It is possible to add an option ``currentfile`` when initiating the saver.
Saver will then try to factor in the given files current location and version number.
(this will be incremented by +1).

Note:
    The widget itself will only return a filepath and is not performing any save
    operations.

    When the selection is made by the user the ``SaverWidget.fileSaveRequested``
    signal is emitted with the output path.

    The set description and image will be emited by the ``fileThumbnailAdded`` and
    ``fileDescriptionAdded`` signals.

"""


import re
import uuid
import collections

from PySide2 import QtCore, QtWidgets, QtGui

import gwbrowser.common as common

from gwbrowser.editors import ClickableLabel

from gwbrowser.basecontextmenu import BaseContextMenu, contextmenu
from gwbrowser.bookmarkswidget import BookmarksModel
from gwbrowser.assetwidget import AssetModel
from gwbrowser.standalone import HeaderWidget, CloseButton, MinimizeButton

from gwbrowser.capture import ScreenGrabber
import gwbrowser.settings as Settings

from gwbrowser.settings import AssetSettings
from gwbrowser.imagecache import ImageCache

from gwbrowser.context.saverwidgets import SelectBookmarkButton
from gwbrowser.context.saverwidgets import SelectBookmarkView

from gwbrowser.context.saverwidgets import SelectAssetButton
from gwbrowser.context.saverwidgets import SelectAssetView

from gwbrowser.context.saverwidgets import SelectFolderButton
from gwbrowser.context.saverwidgets import SelectFolderView
from gwbrowser.context.saverwidgets import SelectFolderModel


class ThumbnailContextMenu(BaseContextMenu):
    """Context menu associated with the thumbnail."""

    def __init__(self, parent=None):
        super(ThumbnailContextMenu, self).__init__(
            QtCore.QModelIndex(), parent=parent)
        self.add_thumbnail_menu()

    @contextmenu
    def add_thumbnail_menu(self, menu_set):
        """Menu for thumbnail operations."""
        capture_thumbnail_pixmap = ImageCache.get_rsc_pixmap(
            u'capture_thumbnail', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        pick_thumbnail_pixmap = ImageCache.get_rsc_pixmap(
            u'pick_thumbnail', common.SECONDARY_TEXT, common.INLINE_ICON_SIZE)
        remove_thumbnail_pixmap = ImageCache.get_rsc_pixmap(
            u'todo_remove', common.FAVOURITE, common.INLINE_ICON_SIZE)

        menu_set[u'Capture thumbnail'] = {
            u'icon': capture_thumbnail_pixmap,
            u'action': self.parent().window().capture_thumbnail
        }
        menu_set[u'Pick thumbnail'] = {
            u'icon': pick_thumbnail_pixmap,
            u'action': self.parent().window().pick_thumbnail
        }
        menu_set[u'separator'] = {}
        menu_set[u'Reset thumbnail'] = {
            u'icon': remove_thumbnail_pixmap,
            u'action': self.parent().reset
        }
        return menu_set


class ThumbnailButton(ClickableLabel):
    """Button used to select the thumbnail for this item."""

    def __init__(self, parent=None):
        super(ThumbnailButton, self).__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self.reset()

    def reset(self):
        pixmap = ImageCache.get_rsc_pixmap(
            u'pick_thumbnail', common.FAVOURITE, common.ROW_HEIGHT)
        self.setPixmap(pixmap)
        self.setStyleSheet(
            u'background-color: rgba({});'.format(u'{}/{}/{}/{}'.format(*common.BACKGROUND.getRgb())))

        self.window().thumbnail_image = QtGui.QImage()

    def contextMenuEvent(self, event):
        menu = ThumbnailContextMenu(parent=self)
        pos = self.rect().center()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()


class SaverHeaderWidget(HeaderWidget):
    def __init__(self, parent=None):
        super(SaverHeaderWidget, self).__init__(parent=parent)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtCore.Qt.NoPen)
        rect = event.rect()
        rect.setTop(rect.bottom())
        painter.setBrush(QtGui.QBrush(common.BACKGROUND))
        painter.drawRect(event.rect())
        painter.end()


class SaverFileInfo(QtCore.QObject):
    """A QFileInfo-like QObject responsible for getting the currently set file-path
    components.

    Methods:
        fileInfo():     QFileInfo instance with the current path choice.
        path():         The path of the current choice without the filename.
        fileName():     The filename without the path.

    """

    def __init__(self, parent):
        super(SaverFileInfo, self).__init__(parent=parent)

    def _new(self):
        """Creates a new filename based on the currently set properties."""
        job = None
        asset = None
        location = self.parent().window().location

        buttons = self.parent().window().findChildren(SelectFolderButton)
        assetbutton = [f for f in buttons if f.objectName() == u'SelectAssetButton'][-1]
        a = assetbutton.view()

        index = a.model().sourceModel().active_index()
        if index.isValid():
            job = index.data(common.ParentRole)[1]
            asset = index.data(common.ParentRole)[-1]

        custom = self.parent().window().findChild(Custom).text()
        regex = re.compile(r'[^0-9a-z]+', flags=re.IGNORECASE)
        job = regex.sub(u'', job)[
            :3] if job else u'gw'

        asset = regex.sub(u'', asset)[
            :12] if asset else u'sandbox'

        folder = regex.sub(u'', location)[
            :12]

        custom = custom if custom else u'untitled'
        custom = regex.sub(u'-', custom)[:25]

        version = u'001'

        user = next(f for f in QtCore.QStandardPaths.standardLocations(
            QtCore.QStandardPaths.HomeLocation))
        user = QtCore.QFileInfo(user).fileName()
        user = regex.sub(u'', user)
        # Numbers are not allowed in the username
        user = re.sub(r'[0-9]+', u'', user)

        isexport = location == common.ExportsFolder
        folder = self.parent().window().extension if isexport else folder
        return '{job}_{asset}_{folder}_{custom}_{version}_{user}.{ext}'.format(
            job=job,
            asset=asset,
            folder=folder,
            custom=custom,
            version=version,
            user=user,
            ext=self.parent().window().extension,
        )

    def _increment_sequence(self, currentfile):
        """Increments the version of the current file by 1."""
        file_info = QtCore.QFileInfo(currentfile)
        match = common.get_sequence(file_info.fileName())

        if not match:
            return currentfile

        version = '{}'.format(int(match.group(2))
                              + 1).zfill(len(match.group(2)))
        return match.expand(r'\1{}\3.\4').format(version)

    def fileInfo(self):
        """Returns the path as a QFileInfo instance"""
        return QtCore.QFileInfo('{}/{}'.format(self.path(), self.fileName()))

    def path(self):
        """Returns the path() element of the set path."""
        buttons = self.parent().window().findChildren(SelectFolderButton)
        foldersbutton = [f for f in buttons if f.objectName() == u'SelectFolderButton'][-1]
        return foldersbutton.view().model().destination()

    def fileName(self, style=common.LowerCase):
        """The main method to get the new file's filename."""
        currentfile = self.parent().window().currentfile

        if currentfile:
            match = common.get_valid_filename(currentfile)
            if match:
                custom = self.parent().window().findChild(Custom).text()

                # Not including the username if the destination is the exports folder
                filename = match.expand(r'\1_\2_\3_{}_{}_\6.\7'.format(
                    custom if custom else u'untitled',
                    u'{}'.format(int(match.group(5))
                                 + 1).zfill(len(match.group(5)))
                ))
            else:
                filename = self._increment_sequence(currentfile)
        else:
            filename = self._new()

        if style == common.LowerCase:
            filename = filename.lower()
        elif style == common.UpperCase:
            filename = filename.upper()
        return filename


class DescriptionEditor(QtWidgets.QLineEdit):
    """Editor widget to input the description of the file."""

    def __init__(self, parent=None):
        super(DescriptionEditor, self).__init__(parent=parent)
        self.setPlaceholderText(u'Description...')
        self.setStyleSheet("""QLineEdit {{
            background-color: rgba(0,0,0,0);
            border-bottom: 2px solid rgba(0,0,0,50);
            padding: 0px;
            margin: 0px;
            color: rgba({});
            font-family: "{}";
            font-size: 11pt;
        }}""".format(
            '{},{},{},{}'.format(*common.TEXT_SELECTED.getRgb()),
            common.PrimaryFont.family()
        ))
        self.setFixedHeight(36)


class BaseNameLabel(QtWidgets.QLabel):
    """Baselabel to display the current filename."""

    def __init__(self, parent=None):
        super(BaseNameLabel, self).__init__(parent=parent)
        self.setTextFormat(QtCore.Qt.RichText)
        self.setOpenExternalLinks(False)
        self.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)

        self.setStyleSheet(
            """QLabel{{
                background-color: rgba(0,0,0,0);
                font-family: "{}";
                font-size: 11pt;
            }}""".format(common.PrimaryFont.family())
        )


class Prefix(BaseNameLabel):
    """Displays the first parth of the filename."""

    def __init__(self, parent=None):
        super(Prefix, self).__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight)


class Custom(QtWidgets.QLineEdit):
    """Widget for editing the custom filename component."""

    def __init__(self, parent=None):
        super(Custom, self).__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignCenter)

        self.setMaxLength(25)
        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSize(11)
        metrics = QtGui.QFontMetrics(font)

        self.setPlaceholderText('untitled')
        self.setStyleSheet("""QLineEdit{{
            background-color: rgba(0,0,0,0);
            border-bottom: 2px solid rgba(255,255,255,255);
            padding: 0px;
            margin: 0px;
            color: rgba({});
            font-family: "{}";
            font-size: 11pt;
        }}""".format(
            '{},{},{},{}'.format(*common.TEXT_SELECTED.getRgb()),
            common.PrimaryFont.family()))

        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSize(12)
        metrics = QtGui.QFontMetrics(font)
        self.setFixedWidth(metrics.width('untitled'))

        self.textChanged.connect(self.resizeLineEditToContents)
        self.textChanged.connect(self.verify)

    def verify(self, text):
        cpos = self.cursorPosition()
        text = re.sub(r'[^a-z0-9\-]+', '-', text, flags=re.IGNORECASE)
        text = re.sub(r'-{2,}', '-', text, flags=re.IGNORECASE)
        self.setText(text)
        self.setCursorPosition(cpos)

    def resizeLineEditToContents(self, text):
        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSize(12)
        metrics = QtGui.QFontMetrics(font)
        width = metrics.width(text)
        minwidth = metrics.width('untitled')
        width = minwidth if width < minwidth else width
        self.setFixedSize(width, self.height())


class Suffix(BaseNameLabel):
    """Label containing the end of the filename string."""

    def __init__(self, parent=None):
        super(Suffix, self).__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)


class Check(ClickableLabel):
    """The checkbox button."""

    def __init__(self, parent=None):
        super(Check, self).__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setFixedSize(common.ASSET_ROW_HEIGHT, common.ASSET_ROW_HEIGHT)
        pixmap = ImageCache.get_rsc_pixmap(
            'check', common.FAVOURITE, common.ROW_HEIGHT / 1.5)
        self.setPixmap(pixmap)
        self.setStyleSheet("""
            QLabel {{background-color: rgba({});}}
        """.format(u'{}/{}/{}/{}'.format(*common.BACKGROUND.getRgb())))


class SaverWidget(QtWidgets.QDialog):
    """The save dialog to save a file.
    Contains the header and the saver widgets needed to select the desired path.

    When done() is called, the widget will emit the ``fileSaveRequested``,
    ``fileDescriptionAdded`` and ``fileThumbnailAdded`` signals.

    The latter two will emit a tuple of paths (bookmark, file path) the data to
    be provide the information needed to initialize an AssetSettings instance.

    """

    # Signals
    fileSaveRequested = QtCore.Signal(basestring)
    fileDescriptionAdded = QtCore.Signal(tuple)
    fileThumbnailAdded = QtCore.Signal(tuple)

    def __init__(self, extension, location, currentfile=None, parent=None):
        super(SaverWidget, self).__init__(parent=parent)
        self.extension = extension
        self.currentfile = currentfile
        self.location = location
        self.thumbnail_image = None

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowFlags(
            QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

        self._createUI()
        self._connectSignals()
        self.initialize()

    def _createUI(self):
        common.set_custom_stylesheet(self)
        #
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(common.MARGIN / 2, common.MARGIN / 2, common.MARGIN / 2, common.MARGIN / 2)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        #
        self.setFixedWidth(common.WIDTH * 1.5)
        #
        mainrow = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(mainrow)
        mainrow.layout().setContentsMargins(0, 0, 0, 0)
        mainrow.layout().setSpacing(common.INDICATOR_WIDTH)
        mainrow.layout().setAlignment(QtCore.Qt.AlignCenter)
        #
        thumbnailbutton = ThumbnailButton(parent=self)
        thumbnailbutton.setFixedSize(
            common.ASSET_ROW_HEIGHT, common.ASSET_ROW_HEIGHT)
        mainrow.layout().addWidget(thumbnailbutton)
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
        # #
        #
        editor = DescriptionEditor(parent=self)
        row.layout().addWidget(editor, 1)


        bookmarkbutton = SelectBookmarkButton(parent=self)
        bookmarkview = SelectBookmarkView()
        bookmarkbutton.set_view(bookmarkview)

        assetbutton = SelectAssetButton(parent=self)
        assetview = SelectAssetView()
        assetbutton.set_view(assetview)

        foldersbutton = SelectFolderButton(parent=self)
        foldersview = SelectFolderView()
        foldersview.set_model(SelectFolderModel())
        foldersbutton.set_view(foldersview)

        row.layout().addWidget(bookmarkbutton)
        row.layout().addWidget(assetbutton)
        row.layout().addWidget(foldersbutton)
        #
        row = QtWidgets.QWidget()
        QtWidgets.QHBoxLayout(row)
        row.layout().setContentsMargins(0, 0, 0, 0)
        row.layout().setSpacing(0)
        row.layout().setAlignment(QtCore.Qt.AlignCenter)
        row.layout().addWidget(Prefix(parent=self))
        row.layout().addWidget(Custom(parent=self))
        row.layout().addWidget(Suffix(parent=self), 1)
        column.layout().addWidget(row, 1)

        mainrow.layout().addWidget(Check(parent=self))
        self.layout().insertWidget(0, SaverHeaderWidget(parent=self))

        minimizebutton = self.findChild(MinimizeButton)
        minimizebutton.setHidden(True)

        # Statusbar
        statusbar = QtWidgets.QStatusBar(parent=self)
        statusbar.setFixedHeight(common.ROW_BUTTONS_HEIGHT)
        statusbar.setSizeGripEnabled(False)
        statusbar.layout().setAlignment(QtCore.Qt.AlignRight)
        statusbar.setStyleSheet("""QStatusBar {{
            background-color: rgba(0,0,0,0);
            color: rgba({color});
            font-family: "{family}";
            font-size: 8pt;
        }}""".format(
            color='{},{},{},{}'.format(*common.SECONDARY_TEXT.getRgb()),
            family=common.PrimaryFont.family()
        ))

        statusbar.layout().setContentsMargins(20, 20, 20, 20)

        statusbar.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )

        self.layout().addSpacing(common.MARGIN)
        self.layout().addWidget(statusbar, 1)


    def _connectSignals(self):
        buttons = self.findChildren(SelectFolderButton)
        bookmarkbutton = [f for f in buttons if f.objectName() == u'SelectBookmarkButton'][-1]
        assetbutton = [f for f in buttons if f.objectName() == u'SelectAssetButton'][-1]
        foldersbutton = [f for f in buttons if f.objectName() == u'SelectFolderButton'][-1]
        header = self.findChild(SaverHeaderWidget)

        b = bookmarkbutton.view()
        a = assetbutton.view()
        f = foldersbutton.view()

        b.widgetShown.connect(a.hide)
        b.widgetShown.connect(f.hide)

        a.widgetShown.connect(b.hide)
        a.widgetShown.connect(f.hide)

        f.widgetShown.connect(a.hide)
        f.widgetShown.connect(b.hide)

        header.widgetMoved.connect(b.move)
        header.widgetMoved.connect(a.move)
        header.widgetMoved.connect(f.move)

        # Signal/slot connections for the primary bookmark/asset and filemodels
        b.model().sourceModel().modelReset.connect(
            lambda: a.model().sourceModel().set_active(b.model().sourceModel().active_index()))
        b.model().sourceModel().modelReset.connect(
            a.model().sourceModel().modelDataResetRequested.emit)
        b.model().sourceModel().activeChanged.connect(
            a.model().sourceModel().set_active)
        b.model().sourceModel().activeChanged.connect(
            lambda x: a.model().sourceModel().modelDataResetRequested.emit())


        a.model().sourceModel().activeChanged.connect(f.set_asset)
        a.model().sourceModel().activeChanged.connect(lambda i: f.model().fileTypeChanged.emit(self.extension))

        b.model().sourceModel().activeChanged.connect(lambda i: self.update_filename_display())
        b.model().sourceModel().activeChanged.connect(lambda i: self.update_filepath_display())
        a.model().sourceModel().activeChanged.connect(lambda i: self.update_filename_display())
        a.model().sourceModel().activeChanged.connect(lambda i: self.update_filepath_display())

        b.model().sourceModel().modelReset.connect(self.update_filename_display)
        b.model().sourceModel().modelReset.connect(self.update_filepath_display)
        a.model().sourceModel().modelReset.connect(self.update_filename_display)
        a.model().sourceModel().modelReset.connect(self.update_filepath_display)
        f.model().modelReset.connect(self.update_filename_display)
        f.model().modelReset.connect(self.update_filepath_display)

        closebutton = self.findChild(CloseButton)
        thumbnailbutton = self.findChild(ThumbnailButton)
        custom = self.findChild(Custom)
        check = self.findChild(Check)

        check.clicked.connect(lambda: self.done(QtWidgets.QDialog.Accepted))
        closebutton.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected))
        # Picks a thumbnail
        thumbnailbutton.clicked.connect(self.pick_thumbnail)

        # Filename
        b.activated.connect(self.update_filename_display)
        a.activated.connect(self.update_filename_display)
        f.activated.connect(self.update_filename_display)
        f.model().destinationChanged.connect(lambda x: self.update_filename_display)
        f.model().fileTypeChanged.connect(lambda x: self.update_filename_display)
        custom.textChanged.connect(self.update_filename_display)
        # Filepath
        b.activated.connect(self.update_filepath_display)
        a.activated.connect(self.update_filepath_display)
        f.activated.connect(self.update_filepath_display)
        f.model().destinationChanged.connect(lambda x: self.update_filepath_display)
        f.model().fileTypeChanged.connect(lambda x: self.update_filepath_display)
        custom.textChanged.connect(self.update_filepath_display)

    def initialize(self):
        """Checks the models' active items and sets the ui elements accordingly."""
        buttons = self.findChildren(SelectFolderButton)
        bookmarkbutton = [f for f in buttons if f.objectName() == u'SelectBookmarkButton'][-1]
        assetbutton = [f for f in buttons if f.objectName() == u'SelectAssetButton'][-1]
        foldersbutton = [f for f in buttons if f.objectName() == u'SelectFolderButton'][-1]

        b = bookmarkbutton.view()
        a = assetbutton.view()
        f = foldersbutton.view()

        b.model().filterTextChanged.emit(b.model().filterText())
        a.model().filterTextChanged.emit(a.model().filterText())
        #
        b.model().filterFlagChanged.emit(Settings.MarkedAsActive, b.model().filterFlag(Settings.MarkedAsActive))
        b.model().filterFlagChanged.emit(Settings.MarkedAsArchived, b.model().filterFlag(Settings.MarkedAsArchived))
        b.model().filterFlagChanged.emit(Settings.MarkedAsFavourite, b.model().filterFlag(Settings.MarkedAsFavourite))
        #
        a.model().filterFlagChanged.emit(Settings.MarkedAsActive, a.model().filterFlag(Settings.MarkedAsActive))
        a.model().filterFlagChanged.emit(Settings.MarkedAsArchived, a.model().filterFlag(Settings.MarkedAsArchived))
        a.model().filterFlagChanged.emit(Settings.MarkedAsFavourite, a.model().filterFlag(Settings.MarkedAsFavourite))

        if self.currentfile:
            # Checking if the reference file has a valid pattern
            match = common.get_valid_filename(self.currentfile)
            if match:
                self.findChild(Custom).setHidden(False)
                self.findChild(Custom).setText(match.group(4))
            else:
                self.findChild(Custom).setHidden(True)
            self.findChild(Custom).setHidden(False)
            # Thumbnail
            self.update_thumbnail_preview()
        else:
            self.findChild(Custom).setHidden(False)



        bookmarkbutton.view().model().sourceModel().modelDataResetRequested.emit()
        bookmarkbutton.view().model().sourceModel().activeChanged.emit(bookmarkbutton.view().model().sourceModel().active_index())
        assetbutton.view().model().sourceModel().activeChanged.emit(assetbutton.view().model().sourceModel().active_index())

        if self.location:
            if not f.model().asset().isValid():
                return  # can't set the destination without the asset
            path = list(f.model().asset().data(common.ParentRole)) + [self.location, ]
            path = u'/'.join(path)
            index = f.model().index(path)
            f.model().destinationChanged.emit(index)

    def pick_thumbnail(self):
        """Prompt to select an image file."""
        dialog = QtWidgets.QFileDialog(parent=self)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilter(
            u'Image files (*.png *.jpg *.jpeg *.tiff *.tff *.tga *.psd *.exr *.tx *.dpx)')

        # Setting the dialog's root path
        dialog.setDirectory(SaverFileInfo(self).path())
        dialog.setOption(
            QtWidgets.QFileDialog.DontUseCustomDirectoryIcons, True)

        if not dialog.exec_():
            return
        if not dialog.selectedFiles():
            return

        temp_path = '{}/browser_temp_thumbnail_{}.png'.format(
            QtCore.QDir.tempPath(), uuid.uuid1())
        generate_thumbnail(next(f for f in dialog.selectedFiles()), temp_path)

        self.thumbnail_image = QtGui.QImage()
        self.thumbnail_image.load(temp_path)
        self.update_thumbnail_preview()

    def capture_thumbnail(self):
        """Captures a thumbnail."""
        pixmap = ScreenGrabber.capture()

        if not pixmap:
            return
        if pixmap.isNull():
            return

        image = common.resize_image(
            pixmap.toImage(), common.THUMBNAIL_IMAGE_SIZE)
        self.thumbnail_image = image
        self.update_thumbnail_preview()

    def update_thumbnail_preview(self):
        """Displays the selected thumbnail image."""
        if not self.thumbnail_image:
            return
        if self.thumbnail_image.isNull():
            return
        # Resizing for display
        thumbnail = self.findChild(ThumbnailButton)
        image = common.resize_image(self.thumbnail_image, thumbnail.height())

        pixmap = QtGui.QPixmap()
        pixmap.convertFromImage(image)
        background = common.get_color_average(image)

        thumbnail.setPixmap(pixmap)
        thumbnail.setStyleSheet("""QLabel {{background-color: rgba({});}}""".format(
            '{},{},{},{}'.format(*background.getRgb())
        ))

    def update_filepath_display(self, *args, **kwargs):
        """Slot responsible for updating the file-path display."""
        font = QtGui.QFont(common.PrimaryFont)
        font.setPointSize(8)
        metrics = QtGui.QFontMetrics(font)
        text = metrics.elidedText(
            SaverFileInfo(self).fileInfo().filePath(),
            QtCore.Qt.ElideLeft,
            self.window().rect().width() - common.MARGIN
        )
        self.findChild(QtWidgets.QStatusBar).showMessage(text)

    def update_filename_display(self, *args, **kwargs):
        """Slot responsible for updating the Prefix, Custom, and Suffix widgets."""
        f = SaverFileInfo(self)
        file_info = QtCore.QFileInfo(f.fileName(style=common.LowerCase))

        match = common.get_valid_filename(
            self.currentfile) if self.currentfile else None
        if self.currentfile and not match:
            self.findChild(Prefix).setText(file_info.completeBaseName())
            self.findChild(Suffix).setText(
                '.{}'.format(file_info.completeSuffix()))
        elif self.currentfile and match:
            prefix, suffix = self.prefix_suffix(match, increment=True)
            self.findChild(Prefix).setText(prefix)
            self.findChild(Suffix).setText(suffix)
        else:  # New name
            match = common.get_valid_filename(
                '/{}'.format(f.fileName(style=common.LowerCase)))
            prefix, suffix = self.prefix_suffix(match, increment=False)
            self.findChild(Prefix).setText(prefix)
            self.findChild(Suffix).setText(suffix)

    def prefix_suffix(self, match, increment=True):
        prefix = match.expand(r'\1_\2_\3_')
        suffix = match.expand(r'_<span style="color:rgba({});">{}</span>_\6.\7'.format(
            u'{},{},{},{}'.format(*common.FAVOURITE.getRgb()),
            u'{}'.format(int(match.group(5)) + int(increment)
                         ).zfill(len(match.group(5)))
        ))
        return prefix, suffix

    def done(self, result):
        """Slot called by the check button to initiate the save."""
        if result == QtWidgets.QDialog.Rejected:
            return super(SaverWidget, self).done(result)

        buttons = self.findChildren(SelectFolderButton)
        bookmarkbutton = [f for f in buttons if f.objectName() == u'SelectBookmarkButton'][-1]
        assetbutton = [f for f in buttons if f.objectName() == u'SelectAssetButton'][-1]
        foldersbutton = [f for f in buttons if f.objectName() == u'SelectFolderButton'][-1]

        if not bookmarkbutton.view().active_index().isValid():
            return QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.NoIcon,
                u'', u'Unable to save as the destination bookmark has not yet been selected.', parent=self).exec_()
        elif not assetbutton.view().active_index().isValid():
            return QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.NoIcon,
                u'', u'Unable to save as the destination asset has not yet been selected.', parent=self).exec_()
        elif not foldersbutton.view().model().destination():
            return QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.NoIcon,
                u'', u'Unable to save as the destination folder inside not yet been selected.', parent=self).exec_()

        file_info = SaverFileInfo(self).fileInfo()

        # Let's check if we're not overwriding a file by accident
        if file_info.exists():
            mbox = QtWidgets.QMessageBox(parent=self)
            mbox.setWindowTitle(u'File exists already')
            mbox.setIcon(QtWidgets.QMessageBox.Warning)
            mbox.setText(
                u'{} already exists.'.format(file_info.fileName())
            )
            mbox.setInformativeText(
                u'If you decide to proceed the existing file will be overriden. Are you sure you want to continue?')
            mbox.setStandardButtons(
                QtWidgets.QMessageBox.Save
                | QtWidgets.QMessageBox.Cancel
            )
            mbox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
            if mbox.exec_() == QtWidgets.QMessageBox.Cancel:
                return

        bookmark = bookmarkbutton.view().active_index().data(common.ParentRole)
        # Let's broadcast these settings
        self.fileSaveRequested.emit(file_info.filePath())
        self.fileThumbnailAdded.emit((
            bookmark[0],
            bookmark[1],
            bookmark[2],
            file_info.filePath(),
            self.thumbnail_image))
        self.fileDescriptionAdded.emit((
            bookmark[0],
            bookmark[1],
            bookmark[2],
            file_info.filePath(),
            self.findChild(DescriptionEditor).text()))

        super(SaverWidget, self).done(result)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    currentfile = '//gordo/jobs/bemusic_8283/assets/trumpet/exports/bem_trumpet_scenes_untitled_001_freelance.obj'

    widget = SaverWidget(u'psd', common.ScenesFolder, currentfile=None)

    def func(path):
        print path
    widget.fileSaveRequested.connect(func)
    widget.fileThumbnailAdded.connect(func)
    widget.fileDescriptionAdded.connect(func)
    widget.show()
    app.exec_()
