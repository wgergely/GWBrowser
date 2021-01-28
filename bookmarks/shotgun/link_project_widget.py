# -*- coding: utf-8 -*-
"""Links a Shotgun Project Entity with a Bookmark.

"""
from PySide2 import QtWidgets, QtCore, QtGui

from .. import common
from .. import images
from .. import common_ui
from .. import bookmark_db
from .. import settings
from . import shotgun


instance = None
ENTITY_TYPE = shotgun.ProjectEntity

EntityIDRole = QtCore.Qt.UserRole + 1
EntityNameRole = EntityIDRole + 1


def close():
    global instance
    if instance is None:
        return
    instance.close()
    instance.deleteLater()
    instance = None


def show(sg_properties):
    global instance
    close()
    instance = LinkProject(sg_properties)
    instance.open()
    return instance


class LinkProject(QtWidgets.QDialog):
    """Widget used to link bookmark to a Shotgun Project entity.

    Args:
        server (type): Description of parameter `server`.
        job (type): Description of parameter `job`.
        root (type): Description of parameter `root`.

    """
    entitySelected = QtCore.Signal(int, unicode)

    def __init__(self, sg_properties, parent=None):
        super(LinkProject, self).__init__(parent=parent)

        self.sg_properties = sg_properties
        self.picker = None
        self.link_button = None

        self.init_timer = QtCore.QTimer(parent=self)
        self.init_timer.setInterval(250)
        self.init_timer.setSingleShot(True)

        if not self.parent():
            common.set_custom_stylesheet(self)
        self.setWindowTitle(
            u'Select a {} Entity to Link'.format(ENTITY_TYPE.title()))

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN()
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        row = common_ui.add_row(
            ENTITY_TYPE.title(),
            height=common.ROW_HEIGHT(),
            parent=self
        )

        self.picker = QtWidgets.QComboBox(parent=self)
        self.picker.setMinimumWidth(common.WIDTH() * 0.5)
        self.picker.setFixedHeight(common.ROW_HEIGHT())
        row.layout().addWidget(self.picker, 1)

        row = common_ui.add_row(None, height=common.ROW_HEIGHT(), parent=self)
        self.link_button = common_ui.PaintedButton(
            u'Link {} Entity'.format(ENTITY_TYPE.title()))
        self.link_button.setFixedHeight(common.ROW_HEIGHT())
        row.layout().addWidget(self.link_button, 1)

    def _connect_signals(self):
        self.link_button.clicked.connect(self.emit_entity_selected)
        self.entitySelected.connect(self.save_data)

        self.link_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))
        self.init_timer.timeout.connect(self.init_items)
        self.init_timer.timeout.connect(self.select_candidate)

    @common.error
    @common.debug
    def init_items(self):
        """Loads a list of Shotgun entities.

        """
        self.picker.clear()

        self.picker.addItem(u'Connecting to Shotgun....')
        QtWidgets.QApplication.instance().processEvents()

        try:
            with shotgun.connection(self.sg_properties) as sg:
                entities = sg.find_projects()
        except:
            self.picker.clear()
            self.picker.addItem(u'An error occured.')
            idx = self.picker.count() - 1
            self.picker.setItemData(idx, None, role=EntityIDRole)
            self.picker.setItemData(idx, None, role=EntityNameRole)
            self.decorate_item(self.picker.count() - 1, error=True)
            raise

        self.picker.clear()
        for entity in sorted(entities, key=shotgun.name_key):
            name = shotgun.name_key(entity)
            if shotgun.IdColumn not in entity:
                continue
            self.picker.addItem(name)
            idx = self.picker.count() - 1
            self.picker.setItemData(
                idx, entity[shotgun.IdColumn], role=EntityIDRole)
            self.picker.setItemData(idx, name, role=EntityNameRole)
            self.decorate_item(self.picker.count() - 1)

        if not self.picker.model().rowCount():
            self.picker.addItem(u'No {} found.'.format(ENTITY_TYPE.title()))
            idx = self.picker.count() - 1
            self.picker.setItemData(idx, None, role=EntityIDRole)
            self.picker.setItemData(idx, None, role=EntityNameRole)
            self.decorate_item(self.picker.count() - 1, error=True)

    def decorate_item(self, idx, error=False):
        sg_pixmap = images.ImageCache.get_rsc_pixmap(
            u'shotgun', None, common.MARGIN() * 2)
        error_pixmap = images.ImageCache.get_rsc_pixmap(
            u'close', common.REMOVE, common.MARGIN() * 2)

        self.picker.setItemData(
            idx,
            QtCore.QSize(1, common.ROW_HEIGHT() * 0.8),
            role=QtCore.Qt.SizeHintRole
        )

        if error:
            pixmap = error_pixmap
        else:
            pixmap = sg_pixmap

        self.picker.setItemData(
            idx,
            QtGui.QIcon(pixmap),
            role=QtCore.Qt.DecorationRole
        )

    @QtCore.Slot()
    def select_candidate(self):
        """Try and select an item from the list matching the local asset's name."""
        name = self.sg_properties[settings.JobKey]
        for n in xrange(self.picker.model().rowCount()):
            index = self.picker.model().index(n, 0)
            entity = index.data(EntityNameRole).lower()
            if name in entity or entity in name:
                self.picker.setCurrentIndex(n)
                return

    def showEvent(self, event):
        self.init_timer.start()

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH(), (common.MARGIN() * 2) + (common.ROW_HEIGHT() * 2))

    @QtCore.Slot()
    def emit_entity_selected(self):
        self.entitySelected.emit(
            self.picker.currentData(EntityIDRole),
            self.picker.currentData(EntityNameRole)
        )

    @common.error
    @common.debug
    @QtCore.Slot(int)
    @QtCore.Slot(unicode)
    def save_data(self, entity_id, entity_name):
        server = self.sg_properties[settings.ServerKey]
        job = self.sg_properties[settings.JobKey]
        root = self.sg_properties[settings.RootKey]

        with bookmark_db.transactions(server, job, root) as db:
            db.setValue(
                db.source(),
                'shotgun_id',
                entity_id,
                table=bookmark_db.BookmarkTable
            )
            db.setValue(
                db.source(),
                'shotgun_name',
                entity_name,
                table=bookmark_db.BookmarkTable
            )
