# -*- coding: utf-8 -*-
"""Widget used to link a single local asset with a Shotgun entity.

"""
from PySide2 import QtWidgets, QtCore, QtGui

from .. import common
from .. import log
from .. import images
from .. import common_ui
from . import shotgun


__instance = None

DB_KEY = u'shotgun_id'


class LinkEntityWidget(QtWidgets.QDialog):
    """Widget used to link a local asset to a Shotgun entity.

    Args:
        server (type): Description of parameter `server`.
        job (type): Description of parameter `job`.
        root (type): Description of parameter `root`.

    """
    entitySelected = QtCore.Signal(int, unicode)

    def __init__(self, server, job, root, parent=None):
        global __instance
        __instance = self

        super(LinkEntityWidget, self).__init__(parent=parent)

        if not self.parent():
            common.set_custom_stylesheet(self)

        self.setWindowTitle(u'Link to Shotgun')

        self.server = server
        self.job = job
        self.root = root
        self.entity_type = shotgun.ProjectEntity

        self.picker = None
        self.link_button = None

        self.init_timer = QtCore.QTimer(parent=self)
        self.init_timer.setInterval(250)
        self.init_timer.setSingleShot(True)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum,
            QtWidgets.QSizePolicy.Maximum
        )

        self._create_UI()
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.link_button.clicked.connect(self.action)
        self.init_timer.timeout.connect(self.init_items)
        self.init_timer.timeout.connect(self.select_candidate)

    def _create_UI(self):
        QtWidgets.QHBoxLayout(self)
        o = common.MARGIN()
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        row = common_ui.add_row(
            self.entity_type.title(),
            height=common.ROW_HEIGHT(),
            parent=self
        )

        self.picker = QtWidgets.QComboBox(parent=self)
        self.link_button = common_ui.PaintedButton(u'Link')

        self.picker.setMinimumWidth(common.WIDTH() * 0.5)
        self.picker.setFixedHeight(common.ROW_HEIGHT() * 1)

        row.layout().addWidget(self.picker, 1)
        self.layout().addStretch(1)
        self.layout().addWidget(self.link_button)

    @QtCore.Slot()
    def init_items(self):
        """Loads a list of Shotgun entities.

        """
        try:
            with shotgun.connection(self.server, self.job, self.root) as sg:
                entities = sg.find_projects()

            for entity in sorted(entities, key=shotgun.name_key):
                name = shotgun.name_key(entity)
                if shotgun.IdColumn not in entity:
                    continue
                self.picker.addItem(
                    name,
                    userData=entity[shotgun.IdColumn]
                )
                self._decorate_item(self.picker.count() - 1)

            if not self.picker.model().rowCount():
                self.picker.addItem(u'No items found', userData=None)
                self._decorate_item(self.picker.count() - 1, error=True)
        except Exception as e:
            self.picker.addItem(u'Error getting items', userData=None)
            self._decorate_item(self.picker.count() - 1, error=True)
            log.error(e)

    def _decorate_item(self, idx, error=False):
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
        name = self.job
        for n in xrange(self.picker.model().rowCount()):
            index = self.picker.model().index(n, 0)
            entity = index.data(QtCore.Qt.DisplayRole).lower()
            if name in entity or entity in name:
                self.picker.setCurrentIndex(n)
                return

    def showEvent(self, event):
        self.init_timer.start()

    @QtCore.Slot()
    def action(self):
        entity_id = self.picker.currentData()
        entity_name = self.picker.currentText()
        self.entitySelected.emit(entity_id, entity_name)
        self.done(QtWidgets.QDialog.Accepted)
