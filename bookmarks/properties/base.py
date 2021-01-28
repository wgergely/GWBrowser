# -*- coding: utf-8 -*-
"""The module contains the base class used by all property editors across
Bookmarks.

The editor widgets provide a unified approach for editing job, bookmark, asset
and file properties. If the base-class is passed the optional `db_table`
keyword, it will try to load/save/update data found in the bookmark database.


PropertiesWidget
----------------

The `PropertiesWidget` base class is relatively flexible and has a number of
abstract methods that need implementing in subclasses depending on the
desired functionality. Namely, `db_source()`, `init_data()` and `save_changes()`
are functions responsbile for providing values and methods needed to load and
save default values from the bookmark database or another source.

The editor provides a thumbnail editor widget that can be used to save a custom
thumbnail for a job, bookmark, asset or file. The default thumbnail can be set
by providing the optional `fallback_thumb` keyword to the instance constructor.

Example
-------

    ..code_block:: python

        editor = PropertiesWidget(
            SECTIONS,
            server,
            job,
            root,
            asset=asset,
            alignment=QtCore.Qt.AlignLeft,
            fallback_thumb=u'file',
            db_table=bookmark_db.AssetTable,
        )
        editor.open()


The editor UI is created by passing a `SECTIONS` dictionary to the
base class.


"""
import uuid
import functools
import datetime

from PySide2 import QtCore, QtGui, QtWidgets

from .. import log
from .. import common
from .. import common_ui
from .. import images
from .. import bookmark_db
from .. import contextmenu
from ..shotgun import shotgun


SLACK_API_URL = u'https://api.slack.com/apps'

CLIPBOARD = {
    bookmark_db.BookmarkTable: {},
    bookmark_db.AssetTable: {},
}

asset_config_help = u'Settings for asset folder names, filters and file name templates.'
instance = None

floatvalidator = QtGui.QRegExpValidator()
floatvalidator.setRegExp(QtCore.QRegExp(ur'[0-9]+[\.]?[0-9]*'))
intvalidator = QtGui.QRegExpValidator()
intvalidator.setRegExp(QtCore.QRegExp(ur'[0-9]+'))
textvalidator = QtGui.QRegExpValidator()
textvalidator.setRegExp(QtCore.QRegExp(ur'[a-zA-Z0-9]+'))
namevalidator = QtGui.QRegExpValidator()
namevalidator.setRegExp(QtCore.QRegExp(ur'[a-zA-Z0-9\-\_]+'))
domainvalidator = QtGui.QRegExpValidator()
domainvalidator.setRegExp(QtCore.QRegExp(ur'[a-zA-Z0-9/:\.]+'))
versionvalidator = QtGui.QRegExpValidator()
versionvalidator.setRegExp(QtCore.QRegExp(ur'[v]?[0-9]{1,4}'))
tokenvalidator = QtGui.QRegExpValidator()
tokenvalidator.setRegExp(QtCore.QRegExp(ur'[0-0a-zA-Z\_\-\.\{\}]*'))


span = {
    'start': '<span style="color:rgba({})">'.format(common.rgb(common.ADD)),
    'end': '</span>',
}

TEMP_THUMBNAIL_PATH = u'{temp}/{product}/temp/{uuid}.{ext}'


def copy_properties(server, job, root, asset=None, table=bookmark_db.BookmarkTable):
    """Copies the given bookmark's properties from the database to `CLIPBOARD`.

    Args:
        server (unicode):   The server's name.
        job (unicode):   The job's name.
        root (unicode):   The root's name.


    """
    data = {}
    source = u'{}/{}/{}'.format(server, job, root) if not asset else u'{}/{}/{}/{}'.format(
        server, job, root, asset)
    with bookmark_db.transactions(server, job, root) as db:
        for k in bookmark_db.TABLES[table]:
            if k == 'id':
                continue
            v = db.value(source, k, table=table)
            if v is None:
                continue
            data[k] = v

    if data:
        global CLIPBOARD
        CLIPBOARD[table] = data
        log.success(u'{} copied.'.format(table.title()))

    return data


def paste_properties(server, job, root, asset=None, table=bookmark_db.BookmarkTable):
    """Pastes the saved bookmark properties from `CLIPBOARD` to the given
    bookmark's properties.

    """
    if not CLIPBOARD[table]:
        return

    source = u'/'.join((server, job, root)) if not asset else u'/'.join((server, job, root, asset))
    with bookmark_db.transactions(server, job, root) as db:
        for k in CLIPBOARD[table]:
            db.setValue(source, k, CLIPBOARD[table][k], table=table)
    log.success(u'{} data pasted.'.format(table.title()))


def add_section(icon, label, parent, color=None):
    """Used to a new section with an icon and a title to a widget.

    Args:
        icon (unicode):     The name of an rsc image.
        parent (QWidget):   A widget to add the section to.
        color (QColor):     The color of the icon. Defaults to `None`.

    Returns:
        QWidget:            A widget to add editors to.

    """
    parent = common_ui.add_row(u'', height=None, vertical=True, parent=parent)

    h = common.ROW_HEIGHT()

    _label = QtWidgets.QLabel(parent=parent)
    pixmap = images.ImageCache.get_rsc_pixmap(icon, color, h * 0.8)
    _label.setPixmap(pixmap)
    label = common_ui.PaintedLabel(
        label,
        size=common.LARGE_FONT_SIZE(),
        color=common.TEXT,
        parent=parent
    )

    row = common_ui.add_row(u'', height=h, parent=parent)
    row.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
    row.layout().addWidget(_label, 0)
    row.layout().addWidget(label, 0)
    row.layout().addStretch(1)

    return parent


@QtCore.Slot(unicode)
def process_image(source):
    """Converts resizes and loads an image file as a QImage.

    Args:
        source (unicode): Path to an image file.

    Returns:
        QImage: The resized QImage, or `None` if the image was not processed successfully.

    """
    destination = TEMP_THUMBNAIL_PATH.format(
        temp=QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.GenericDataLocation),
        product=common.PRODUCT,
        uuid=uuid.uuid1(),
        ext=images.THUMBNAIL_FORMAT
    )
    f = QtCore.QFileInfo(destination)
    if not f.dir().exists():
        if not f.dir().mkpath(u'.'):
            s = u'Could not create temp folder.'
            log.error(s)
            common_ui.ErrorBox(u'Capture failed', s).open()
            return None

    res = images.ImageCache.oiio_make_thumbnail(
        source,
        destination,
        images.THUMBNAIL_IMAGE_SIZE
    )

    s = u'Error converting the thumbnail.'
    if not res:
        log.error(s)
        common_ui.ErrorBox(s, u'').open()
        return None

    images.ImageCache.flush(destination)
    image = images.ImageCache.get_image(
        destination,
        int(images.THUMBNAIL_IMAGE_SIZE),
        force=True
    )
    if not image or image.isNull():
        log.error(s)
        common_ui.ErrorBox(s, u'').open()
        return None

    if not QtCore.QFile(destination).remove():
        log.error('Failed to remove temp file')

    return image




class ShotgunTypeWidget(QtWidgets.QComboBox):
    ProjectTypes = (shotgun.ProjectEntity,)
    AssetTypes = (shotgun.AssetEntity, shotgun.SequenceEntity, shotgun.ShotEntity)
    FileTypes = ()

    def __init__(self, entity_types, parent=None):
        super(ShotgunTypeWidget, self).__init__(parent=parent)

        shotgun_pixmap = images.ImageCache.get_rsc_pixmap(
            u'shotgun', common.SECONDARY_TEXT, common.MARGIN())

        for entity_type in entity_types:
            self.addItem(entity_type)
            self.setItemData(
                self.count() - 1,
                QtCore.QSize(1, common.ROW_HEIGHT()),
                role=QtCore.Qt.SizeHintRole,
            )
            self.setItemData(
                self.count() - 1,
                QtGui.QIcon(shotgun_pixmap),
                role=QtCore.Qt.DecorationRole,
            )

        self.blockSignals(True)
        self.setCurrentIndex(-1)
        self.blockSignals(False)


class ThumbnailContextMenu(contextmenu.BaseContextMenu):
    """Context menu associated with the ThumbnailWidget.

    """
    def setup(self):
        add_pixmap = images.ImageCache.get_rsc_pixmap(
            u'add', common.ADD, common.MARGIN())
        remove_pixmap = images.ImageCache.get_rsc_pixmap(
            u'remove', common.REMOVE, common.MARGIN())

        self.menu[u'Capture...'] = {
            u'icon': add_pixmap,
            u'action': self.parent().capture
        }
        self.menu[u'Pick...'] = {
            u'icon': add_pixmap,
            u'action': self.parent().pick_image
        }

        self.separator()

        self.menu[u'Reset'] = {
            u'icon': remove_pixmap,
            u'action': self.parent().reset_image
        }



class ThumbnailWidget(common_ui.ClickableIconButton):
    """Widget used to select and save thumbnails.

    The widget will display any currently set thumbnails if the current

    """

    def __init__(self, server, job, root, source=None, fallback_thumb=u'placeholder', parent=None):
        super(ThumbnailWidget, self).__init__(
            u'pick_image',
            (common.FAVOURITE, common.SECONDARY_BACKGROUND),
            size=common.MARGIN() * 10,
            description=u'Right-click to add a thumbnail...',
            parent=parent
        )

        self.server = server
        self.job = job
        self.root = root
        self.source = source
        self.fallback_thumb = fallback_thumb

        self._image = QtGui.QImage()
        self._image.setDevicePixelRatio(images.pixel_ratio)

        self.setAcceptDrops(True)
        self._drag_in_progress = False

        self.clicked.connect(self.capture)

    def image(self):
        return self._image

    @QtCore.Slot()
    def set_image(self, image):
        if not isinstance(image, QtGui.QImage) or image.isNull():
            self._image = QtGui.QImage()
            self._image.setDevicePixelRatio(images.pixel_ratio)
        else:
            self._image = image
        self.update()

    def save_image(self, destination=None):
        """Save the selected thumbnail image to the disc."""
        if not isinstance(self._image, QtGui.QImage) or self._image.isNull():
            return

        args = (
            self.server,
            self.job,
            self.root,
            self.source
        )

        if not all(args) and destination is None:
            return

        if destination is None:
            destination = images.get_thumbnail_path(*args)

        if not self._image.save(destination):
            log.error(u'Failed to save thumbnail.')
            return
        # Remove any previous cahed images from `ImageCache`
        images.ImageCache.flush(destination)

    @QtCore.Slot()
    def reset_image(self):
        self.set_image(None)

    @QtCore.Slot()
    def pick_image(self):
        """Prompt to select an image file."""
        dialog = QtWidgets.QFileDialog(parent=self)
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.List)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setNameFilter(images.get_oiio_namefilters())
        dialog.setFilter(
            QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dialog.setLabelText(
            QtWidgets.QFileDialog.Accept, u'Pick a thumbnail...')

        dialog.fileSelected.connect(lambda s: self.set_image(process_image(s)))
        dialog.open()

    @QtCore.Slot()
    def capture(self):
        """Captures a thumbnail and save it as a QImage.

        The capture is kept as `self._image` and saved to disk then the user
        saves the new file.

        """
        try:
            self.window().hide()
            widget = images.ScreenCapture()
            widget.captureFinished.connect(
                lambda s: self.set_image(process_image(s)))
            widget.exec_()
        except:
            s = u'Error saving capture'
            log.error(s)
            common_ui.ErrorBox(s, u'').open()
        finally:
            self.window().show()

    def _paint_proposed_thumbnail(self, painter):
        o = common.ROW_SEPARATOR()
        rect = self.rect().adjusted(o, o, -o, -o)

        color = common.SEPARATOR
        pen = QtGui.QPen(color)
        pen.setWidthF(common.ROW_SEPARATOR())
        painter.setPen(pen)

        image = images.ImageCache.resize_image(
            self._image, self.rect().height())

        s = float(self.rect().height())
        longest_edge = float(max((self._image.width(), self._image.height())))
        ratio = s / longest_edge
        w = self._image.width() * ratio
        h = self._image.height() * ratio

        rect = QtCore.QRect(
            0, 0,
            int(w) - (o * 2), int(h) - (o * 2)
        )
        rect.moveCenter(self.rect().center())

        painter.drawImage(rect, image, image.rect())

    def _paint_background(self, painter):
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.SEPARATOR)
        painter.drawRect(self.rect())

    def _paint_current_thumbnail(self, painter):
        if not all((self.server, self.job, self.root)):
            pixmap, color = images.get_thumbnail(
                u'',
                u'',
                u'',
                u'',
                self.rect().height(),
                fallback_thumb=self.fallback_thumb
            )
        else:
            pixmap, color = images.get_thumbnail(
                self.server,
                self.job,
                self.root,
                self.source,
                self.rect().height(),
                fallback_thumb=self.fallback_thumb
            )

        if not isinstance(pixmap, QtGui.QPixmap) or pixmap.isNull():
            return

        o = common.ROW_SEPARATOR()

        color = color if color else common.SEPARATOR
        pen = QtGui.QPen(color)
        pen.setWidthF(common.ROW_SEPARATOR())
        painter.setPen(pen)

        s = float(self.rect().height())
        longest_edge = float(max((pixmap.width(), pixmap.height())))
        ratio = s / longest_edge
        w = pixmap.width() * ratio
        h = pixmap.height() * ratio

        rect = QtCore.QRect(0, 0,
                            int(w) - (o * 2),
                            int(h) - (o * 2)
                            )
        rect.moveCenter(self.rect().center())
        painter.drawPixmap(rect, pixmap, pixmap.rect())

    def contextMenuEvent(self, event):
        menu = ThumbnailContextMenu(QtCore.QModelIndex(), parent=self)
        pos = self.rect().center()
        pos = self.mapToGlobal(pos)
        menu.move(pos)
        menu.exec_()

    def paintEvent(self, event):
        option = QtWidgets.QStyleOption()
        option.initFrom(self)
        hover = option.state & QtWidgets.QStyle.State_MouseOver

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        _ = painter.setOpacity(1.0) if hover else painter.setOpacity(0.8)

        try:
            self._paint_background(painter)
            if not self._image or self._image.isNull():
                self._paint_current_thumbnail(painter)
            else:
                self._paint_proposed_thumbnail(painter)
        except:
            log.error(u'Error painting.')
        finally:
            painter.end()

    def enterEvent(self, event):
        app = QtWidgets.QApplication.instance()
        if self.isEnabled():
            if app.overrideCursor():
                app.changeOverrideCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
            else:
                app.restoreOverrideCursor()
                app.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))

        super(ThumbnailWidget, self).enterEvent(event)

    def leaveEvent(self, event):
        super(ThumbnailWidget, self).leaveEvent(event)
        app = QtWidgets.QApplication.instance()
        if self.isEnabled():
            if app.overrideCursor():
                app.restoreOverrideCursor()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self._drag_in_progress = True
            self.repaint()
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            self._drag_in_progress = True
            event.accept()
            return

        self._drag_in_progress = False
        event.ignore()

    def dragLeaveEvent(self, event):
        self._drag_in_progress = False
        self.repaint()
        return True

    def dropEvent(self, event):
        self._drag_in_progress = False
        self.repaint()

        for url in event.mimeData().urls():
            s = url.toLocalFile()
            self.set_image(process_image(s))
            break

        self.repaint()

    def supportedDropActions(self):
        return QtCore.Qt.CopyAction | QtCore.Qt.MoveAction


class PropertiesWidget(QtWidgets.QDialog):
    """Base class for editing bookmark and asset properties.

    Args:
        sections (dict):        The data needed to construct the ui layout.
        server (unciode):       A server.
        job (unicode):          A job.
        root (unicode):         A root folder.
        asset (unicode):        An optional asset. Defaults to `None`.
        db_table (unicode):     An optional name of a bookmark database table.
                                When `None`, the editor won't load or save data
                                to the databse. Defaults to `None`.
        buttons (tuple):        Button labels. Defaults to `('Save', 'Cancel')`.
        alignment (int):        Text alignment. Defaults to `QtCore.Qt.AlignRight`.
        fallback_thumb (unicode): An rsc image name. Defaults to `'placeholder'`.

    """
    itemCreated = QtCore.Signal(unicode)
    itemUpdated = QtCore.Signal(unicode)
    valueUpdated = QtCore.Signal(unicode, int, object)
    thumbnailUpdated = QtCore.Signal(unicode)

    def __init__(
        self,
        sections,
        server,
        job,
        root,
        asset=None,
        db_table=None,
        buttons=(u'Save', 'Cancel'),
        alignment=QtCore.Qt.AlignRight,
        fallback_thumb=u'placeholder',
        parent=None
    ):
        if not isinstance(sections, dict):
            raise TypeError('Invalid section data.')

        super(PropertiesWidget, self).__init__(
            parent=parent,
            f=QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowMinMaxButtonsHint | QtCore.Qt.WindowCloseButtonHint
        )

        self._fallback_thumb = fallback_thumb
        self._alignment = alignment
        self._sections = sections
        self._section_widgets = []
        self._buttons = buttons
        self._db_table = db_table
        self.server = server
        self.job = job
        self.root = root
        self.asset = asset

        self.thumbnail_editor = None

        if not self.parent():
            common.set_custom_stylesheet(self)

        self.current_data = {}
        self.changed_data = {}

        self.scrollarea = None
        self.save_button = None
        self.cancel_button = None

        self.init_timer = QtCore.QTimer(parent=self)
        self.init_timer.setSingleShot(True)
        self.init_timer.setInterval(10)

        self.setMinimumWidth(common.WIDTH() * 0.5)
        self.setMinimumHeight(common.HEIGHT() * 0.5)

        if all((server, job, root)):
            if not asset:
                self.setWindowTitle(u'{}/{}/{}'.format(
                    server, job, root))
            else:
                self.setWindowTitle(u'{}/{}/{}/{}'.format(
                    server, job, root, asset))

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        o = common.MARGIN()

        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        if not self.server or not self.job or not self.root:
            source = u''
        elif not self.asset:
            source = u'/'.join((self.server, self.job, self.root))
        else:
            source = u'/'.join((self.server, self.job, self.root, self.asset))

        self.thumbnail_editor = ThumbnailWidget(
            self.server,
            self.job,
            self.root,
            source,
            fallback_thumb=self._fallback_thumb,
            parent=self
        )

        # Separator pixmap
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'gradient3', None, common.MARGIN(), opacity=0.5)
        separator = QtWidgets.QLabel(parent=self)
        separator.setScaledContents(True)
        separator.setPixmap(pixmap)

        self.left_row = QtWidgets.QWidget(parent=self)
        self.left_row.setStyleSheet(
            u'background-color: rgba({});'.format(common.rgb(common.SEPARATOR)))
        QtWidgets.QHBoxLayout(self.left_row)
        self.left_row.layout().setSpacing(0)
        self.left_row.layout().setContentsMargins(0, 0, 0, 0)
        self.left_row.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Minimum
        )
        self.layout().addWidget(self.left_row)

        parent = QtWidgets.QWidget(parent=self.left_row)
        QtWidgets.QVBoxLayout(parent)
        parent.layout().setContentsMargins(o, o, 0, o)

        parent.layout().addWidget(self.thumbnail_editor, 0)
        parent.layout().addStretch(1)
        self.left_row.layout().addWidget(parent)
        self.left_row.layout().addWidget(separator)

        self.right_row = common_ui.add_row(
            None, parent=self, padding=None, height=None, vertical=True)
        self.right_row.layout().setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        self.right_row.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.Minimum
        )

        self.scrollarea = QtWidgets.QScrollArea(parent=self)
        self.scrollarea.setWidgetResizable(True)
        self.right_row.layout().addWidget(self.scrollarea)

        parent = QtWidgets.QWidget(parent=self)

        QtWidgets.QVBoxLayout(parent)
        parent.layout().setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        parent.layout().setContentsMargins(o, o, o, o)
        parent.layout().setSpacing(o * 2)
        self.scrollarea.setWidget(parent)

        self._add_sections()
        self._add_buttons()

    def _add_sections(self):
        """Utility function used to expand the section data into an UI layout.

        """
        parent = self.scrollarea.widget()

        for section in self._sections.itervalues():
            grp = add_section(
                section['icon'],
                section['name'],
                parent,
                color=section['color'],
            )
            self._section_widgets.append(grp)

            for item in section['groups'].itervalues():
                _grp = common_ui.get_group(parent=grp)

                for v in item.itervalues():
                    row = common_ui.add_row(
                        v['name'], parent=_grp, height=None)

                    if 'description' in v and v['description']:
                        row.setStatusTip(v['description'])
                        row.setToolTip(v['description'])
                        row.setWhatsThis(v['description'])

                    if 'widget' in v and v['widget']:
                        editor = v['widget'](parent=row)
                        row.layout().addWidget(editor, 1)

                        # Set the editor as an attribute on the widget for later access
                        if v['key'] is not None:
                            setattr(
                                self,
                                v['key'] + '_editor',
                                editor
                            )
                        else:
                            setattr(
                                self,
                                v['name'].lower() + '_editor',
                                editor
                            )

                        if isinstance(editor, common_ui.LineEdit):
                            editor.setAlignment(self._alignment)

                        if v['key'] is not None and self._db_table in bookmark_db.TABLES and v['key'] in bookmark_db.TABLES[self._db_table]:
                            _type = bookmark_db.TABLES[self._db_table][v['key']]['type']
                            self._connect_editor(v['key'], _type, editor)

                        if 'validator' in v and v['validator']:
                            if hasattr(editor, 'setValidator'):
                                editor.setValidator(v['validator'])

                        if 'placeholder' in v and v['placeholder']:
                            if hasattr(editor, 'setPlaceholderText'):
                                editor.setPlaceholderText(v['placeholder'])

                        if 'protect' in v and v['protect']:
                            if hasattr(editor, 'setEchoMode'):
                                editor.setEchoMode(QtWidgets.QLineEdit.Password)

                        if 'description' in v and v['description']:
                            editor.setStatusTip(v['description'])
                            editor.setToolTip(v['description'])
                            editor.setWhatsThis(v['description'])

                            row.setStatusTip(v['description'])
                            row.setToolTip(v['description'])
                            row.setWhatsThis(v['description'])

                    if 'help' in v and v['help']:
                        common_ui.add_description(
                            v['help'], label=None, parent=_grp)

                    if 'button' in v and v['button']:
                        button = common_ui.PaintedButton(
                            v['button'], parent=row)

                        if v['key'] is not None:
                            if hasattr(self, v['key'] + '_button_clicked'):
                                button.clicked.connect(
                                    getattr(self, v['key'] + '_button_clicked')
                                )
                        else:
                            if hasattr(self, v['name'].lower() + '_button_clicked'):
                                button.clicked.connect(
                                    getattr(
                                        self, v['name'].lower() + '_button_clicked')
                                )
                        row.layout().addWidget(button, 0)

                    if 'button2' in v and v['button2']:
                        button2 = common_ui.PaintedButton(
                            v['button2'], parent=row)
                        if v['key'] is not None:
                            if hasattr(self, v['key'] + '_button2_clicked'):
                                button2.clicked.connect(
                                    getattr(self, v['key'] +
                                            '_button2_clicked')
                                )
                        else:
                            if hasattr(self, v['name'].lower() + '_button2_clicked'):
                                button2.clicked.connect(
                                    getattr(
                                        self, v['name'].lower() + '_button2_clicked')
                                )
                        row.layout().addWidget(button2, 0)

                        setattr(
                            self,
                            v['key'] + '_button',
                            button
                        )

    def _connect_editor(self, key, _type, editor):
        if hasattr(editor, 'textChanged'):
            editor.textChanged.connect(
                functools.partial(
                    self.text_changed,
                    key,
                    _type,
                    editor
                )
            )
        elif hasattr(editor, 'currentTextChanged'):
            editor.currentTextChanged.connect(
                functools.partial(
                    self.text_changed,
                    key,
                    _type,
                    editor
                )
            )
        elif hasattr(editor, 'stateChanged'):
            editor.stateChanged.connect(
                functools.partial(
                    self.text_changed,
                    key,
                    _type,
                    editor
                )
            )


    def _add_buttons(self):
        if not self._buttons:
            return
        h = common.ROW_HEIGHT()

        self.save_button = common_ui.PaintedButton(
            self._buttons[0], parent=self)
        self.save_button.setFixedHeight(h)
        # self.save_button.setFixedWidth(h * 4)
        self.cancel_button = common_ui.PaintedButton(
            self._buttons[1], parent=self)
        self.cancel_button.setFixedHeight(h)

        row = common_ui.add_row(
            None, padding=None, height=h * 2, parent=self.right_row)
        row.layout().setAlignment(QtCore.Qt.AlignCenter)
        row.layout().addSpacing(common.MARGIN())
        row.layout().addWidget(self.save_button, 1)
        row.layout().addWidget(self.cancel_button, 0)
        row.layout().addSpacing(common.MARGIN())

    def _connect_signals(self):
        self.init_timer.timeout.connect(self.init_data)
        self.cancel_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected))
        self.save_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))

    @QtCore.Slot()
    def center_window(self):
        self.adjustSize()

        app = QtWidgets.QApplication.instance()
        screen_geo = app.primaryScreen().availableGeometry()
        x = int(screen_geo.width() - self.width()) / 2
        y = int(screen_geo.height() - self.height()) / 2
        self.move(x, y)

    def _init_db_data(self):
        """Loads the current values form the bookmark database.

        """
        if self._db_table is None or self._db_table not in bookmark_db.TABLES:
            raise RuntimeError(u'Invalid database table.')

        with bookmark_db.transactions(self.server, self.job, self.root) as db:
            for k in bookmark_db.TABLES[self._db_table]:
                if not hasattr(self, k + '_editor'):
                    continue

                # If the source is not specified we won't be able to load data
                # from the database
                if self.db_source() is None:
                    self.current_data[k] = None
                    continue

                editor = getattr(self, k + '_editor')

                v = db.value(self.db_source(), k, table=self._db_table)
                if v is not None:

                    # Type verification
                    for section in self._sections.itervalues():
                        for group in section['groups'].itervalues():
                            for item in group.itervalues():
                                if item['key'] != k:
                                    continue
                                _type = bookmark_db.TABLES[self._db_table][item['key']]['type']
                                try:
                                    v = _type(v)
                                except Exception as e:
                                    log.error(e)
                                break

                if k not in self.current_data:
                    self.current_data[k] = v

                if v is not None and not isinstance(v, unicode):
                    v = u'{}'.format(v)
                if v is not None:
                    if hasattr(editor, 'setText'):
                        editor.setText(v)
                    elif hasattr(editor, 'setCurrentText'):
                        editor.setCurrentText(v)
                else:
                    if hasattr(editor, 'setCurrentText'):
                        editor.setCurrentIndex(-1)

            for k in bookmark_db.TABLES[bookmark_db.InfoTable]:
                if k == u'id':
                    continue

                source = u'{}/{}/{}'.format(self.server, self.job, self.root)
                v = db.value(source, k, table=bookmark_db.InfoTable)

                if k == 'created':
                    try:
                        v = datetime.datetime.fromtimestamp(
                            float(v)).strftime('%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        v = u'error'

                if hasattr(self, k + '_editor'):
                    editor = getattr(self, k + '_editor')
                    editor.setDisabled(True)
                    editor.setText(v)

    def _save_db_data(self):
        if self._db_table is None or self._db_table not in bookmark_db.TABLES:
            raise RuntimeError(u'Invalid database table.')

        if self.db_source() is None:
            return

        with bookmark_db.transactions(self.server, self.job, self.root) as db:
            for k, v in self.changed_data.iteritems():
                db.setValue(
                    self.db_source(),
                    k,
                    v,
                    table=self._db_table
                )

    def _get_shotgun_attrs(self):
        source = u'{}/{}/{}'.format(self.server, self.job, self.root)
        with bookmark_db.transactions(self.server, self.job, self.root) as db:
            domain = db.value(source, u'shotgun_domain',
                              table=bookmark_db.BookmarkTable)
            key = db.value(source, u'shotgun_api_key',
                           table=bookmark_db.BookmarkTable)
            script = db.value(source, u'shotgun_scriptname',
                              table=bookmark_db.BookmarkTable)

        if not all((domain, key, script)):
            common_ui.ErrorBox(
                u'Missing value.',
                u'Must enter a valid domain, script name and API key.'
            ).open()
            raise RuntimeError(u'Missing value.')

        return domain, key, script

    def _get_project_id(self):
        return None

    QtCore.Slot(unicode)
    QtCore.Slot(type)
    QtCore.Slot(QtWidgets.QWidget)
    QtCore.Slot(unicode)

    def text_changed(self, key, _type, editor, v):
        """Signal called when the user changes a value in the editor.

        Args:
            key (unicode):          The database key.
            _type (type):           The data type.
            editor (QWidget):       The editor widget.

        """
        if _type is not None:
            try:
                if v != u'':
                    v = _type(v)
            except:
                log.error('Type conversion failed.')

        if key not in self.current_data:
            self.current_data[key] = v

        if v != self.current_data[key]:
            self.changed_data[key] = v
            editor.setStyleSheet(
                u'color: rgba({});'.format(common.rgb(common.ADD)))
            return

        if key in self.changed_data:
            del self.changed_data[key]
        editor.setStyleSheet(
            u'color: rgba({});'.format(common.rgb(common.TEXT)))

    def db_source(self):
        """The path of the file database values are associated with.

        Eg. in the case of assets this is `server/job/root/asset`

        """
        raise NotImplementedError(u'Must be overridden in subclass.')

    @QtCore.Slot()
    def init_data(self):
        """Initialises the current/default values.

        """
        raise NotImplementedError(
            'Init data must be overriden in the subclass.')

    @QtCore.Slot()
    def save_changes(self):
        """Abstract method responsible for saving changed data.

        """
        raise NotImplementedError('Must be overriden in the subclass.')

    @QtCore.Slot()
    def done(self, result):
        if result == QtWidgets.QDialog.Rejected:
            if self.changed_data:
                mbox = QtWidgets.QMessageBox(parent=self)
                mbox.setIcon(QtWidgets.QMessageBox.Information)
                mbox.setWindowTitle(u'Save changes?')
                mbox.setText(
                    u'You have unsaved changes. Are you sure you want to close the editor?')
                mbox.setStandardButtons(
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)
                mbox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
                if mbox.exec_() == QtWidgets.QMessageBox.Cancel:
                    return
            return super(PropertiesWidget, self).done(result)

        if not self.save_changes():
            return

        return super(PropertiesWidget, self).done(result)

    def showEvent(self, event):
        self.init_timer.start()
        self.center_window()

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH() * 1.33, common.HEIGHT() * 1.5)

    @QtCore.Slot(int)
    @QtCore.Slot(unicode)
    def update_sg_entity(self, sg_entity_id, sg_entity_name):
        """Slot used updat the shotgun entity id and name.

        """
        self.current_data['shotgun_id'] = sg_entity_id
        sg_entity_id = u'{}'.format(sg_entity_id)
        self.shotgun_id_editor.setText(sg_entity_id)
        self.shotgun_id_editor.textEdited.emit(sg_entity_id)

        self.current_data['shotgun_name'] = sg_entity_name
        self.shotgun_name_editor.setText(sg_entity_name)
        self.shotgun_name_editor.textEdited.emit(sg_entity_name)
