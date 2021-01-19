# -*- coding: utf-8 -*-
"""Widget used to link all local assets with their Shotgun entity counterparts.

"""

from PySide2 import QtWidgets, QtCore, QtGui

from .. import common
from .. import log
from .. import images
from .. import common_ui
from .. import bookmark_db
from . import shotgun


SelectLabel = u'Select entity...'
__instance = None


class BulkLinkWidget(QtWidgets.QDialog):
    """Links a series of local items with Shotgun entities.

    Args:
        items (tuple): A list of local asset names.
        server (unicode): The name of the `server`.
        job (unicode): The name of the `job`.
        root (unicode): The name of the `root`.

    Signals:
        dataSaved (QtCore.Signal):

    """
    dataSaved = QtCore.Signal()

    def __init__(self, items, server, job, root, asset=None, entity_types=(shotgun.AssetEntity, shotgun.SequenceEntity, shotgun.ShotEntity), custom_suggestions=(), parent=None):
        if not isinstance(items, (list, tuple)):
            raise TypeError('Invalid type.')
        global __instance
        __instance = self

        super(BulkLinkWidget, self).__init__(parent=parent)
        if not self.parent():
            common.set_custom_stylesheet(self)
        self.server = server
        self.job = job
        self.root = root
        self.asset = asset # Not implemented
        self.entity_types = entity_types
        self.custom_suggestions = custom_suggestions

        self.items = {}
        for item in items:
            self.items[item] = None

        self.group = None
        self.scrollarea = None

        self.load_timer = QtCore.QTimer(parent=self)
        self.load_timer.setSingleShot(True)
        self.load_timer.setInterval(250)

        self.setMinimumWidth(common.WIDTH() * 0.66)
        self._create_UI()
        self._connect_signals()

    def _add_item(self, item, parent):
        """Adds a row for the specified item.

        """
        row = common_ui.add_row(item, parent=parent)
        self.items[item] = QtWidgets.QComboBox(parent=self)
        self.items[item].addItem(SelectLabel)
        row.layout().addWidget(self.items[item], 1)

    def _create_UI(self):
        self.link_button = common_ui.PaintedButton(u'Save')
        self.scrollarea = QtWidgets.QScrollArea(parent=self)
        self.scrollarea.setWidgetResizable(True)

        QtWidgets.QVBoxLayout()

        o = common.MARGIN()
        QtWidgets.QVBoxLayout(self)
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o * 0.5)

        from ..properties import base
        self.group = base.add_section(
            u'shotgun',
            u'Link with Shotgun',
            self
        )
        self.group.setAttribute(QtCore.Qt.WA_NoSystemBackground, on=False)
        self.group.setAttribute(QtCore.Qt.WA_TranslucentBackground, on=False)

        for item in sorted(self.items.keys()):
            self._add_item(item, self.group)

        self.layout().addWidget(self.scrollarea)
        self.scrollarea.setWidget(self.group)
        self.layout().addWidget(self.link_button)

    def _connect_signals(self):
        self.link_button.clicked.connect(self.action)
        self.load_timer.timeout.connect(self.init_data)

    def init_data(self):
        """Loads data from Shotgun.

        """
        sg_properties = shotgun.get_shotgun_properties(self.server, self.job, self.root)
        if not all(sg_properties.values()):
            return

        model = QtGui.QStandardItemModel()

        # Generic
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        self.append_item(model, SelectLabel, flags=flags, icon=u'branch_closed')

        # Let's get and store all entities:
        with shotgun.connection(self.server, self.job, self.root) as sg:
            for entity_type in self.entity_types:
                self.append_item(
                    model,
                    u'{}s'.format(entity_type.title()),
                    icon=u'',
                    color=common.SEPARATOR,
                )

                entities = []

                try:
                    # Get all columns
                    columns = ()
                    for v in shotgun.DB_KEYS.values():
                        columns += v['columns']

                    entities = sg.find_entities(
                        sg_properties['shotgun_id'],
                        entity_type,
                        columns=list(set((columns)))
                    )
                except:
                    log.error(u'Could not load Shotgun data for entity type "{}"'.format(entity_type))
                    name = u'Error loading {}s'.format(entity_type)
                    self.append_item(model, name, icon=u'close', color=common.REMOVE)
                    continue

                if not entities:
                    continue

                for entity in sorted(entities, key=shotgun.name_key):
                    self.append_entity(model, entity)

        # Let's apply the model to the QCombobox choices
        for item in self.items:
            self.items[item].setModel(model)

        self.select_suggestions()

    @QtCore.Slot()
    def action(self):
        self.save_data_to_database()

    def save_data_to_database(self):
        """Save selected values to the database.

        """
        with bookmark_db.transactions(self.server, self.job, self.root) as db:
            for item in self.items:
                editor = self.items[item]

                if not editor:
                    continue
                if not editor.currentData(shotgun.NameRole):
                    continue

                source = u'/'.join((self.server, self.job, self.root, item))
                for k, v in shotgun.DB_KEYS.iteritems():
                    data = editor.currentData(v['role'])
                    if not data:
                        continue
                    if not isinstance(data, v['type']):
                        try:
                            data = v['type'](data)
                        except:
                            log.error(u'Type conversion error.')
                            continue
                    db.setValue(source, k, data, table=bookmark_db.AssetTable)

        self.done(QtWidgets.QDialog.Accepted)
        self.dataSaved.emit()

    @QtCore.Slot()
    def select_suggestions(self):
        """Select any entities that match a local item name.

        """
        for k, v in self.items.iteritems():
            if self.custom_suggestions:
                for suggestion in self.custom_suggestions:
                    idx = v.findText(
                        suggestion,
                        flags=QtCore.Qt.MatchFixedString | QtCore.Qt.MatchContains)
                    if idx >= 0:
                        v.setCurrentIndex(idx)
                        continue
            idx = v.findText(
                k,
                flags=QtCore.Qt.MatchFixedString | QtCore.Qt.MatchContains)
            if idx >= 0:
                v.setCurrentIndex(idx)

    def append_item(self, model, name, flags=QtCore.Qt.NoItemFlags, icon=None, color=common.SEPARATOR):
        if icon:
            pixmap = images.ImageCache.get_rsc_pixmap(
                icon, color, common.MARGIN())
            icon = QtGui.QIcon(pixmap)

        size = QtCore.QSize(1, common.ROW_HEIGHT())

        item = QtGui.QStandardItem()
        item.setData(name, role=QtCore.Qt.DisplayRole)
        item.setData(size, role=QtCore.Qt.SizeHintRole)
        if icon:
            item.setData(icon, role=QtCore.Qt.DecorationRole)
        item.setFlags(flags)

        model.appendRow(item)

    @staticmethod
    def append_entity(model, entity):
        """Sets the data retrieved from Shotgun in the given model.

        """
        pixmap = images.ImageCache.get_rsc_pixmap(
            u'shotgun', common.BACKGROUND, common.MARGIN())
        icon = QtGui.QIcon(pixmap)
        size = QtCore.QSize(1, common.ROW_HEIGHT())
        name = shotgun.name_key(entity)

        item = QtGui.QStandardItem()
        item.setData(name, role=QtCore.Qt.DisplayRole)
        item.setData(size, role=QtCore.Qt.SizeHintRole)
        item.setData(icon, role=QtCore.Qt.DecorationRole)
        item.setFlags(
            QtCore.Qt.ItemIsEnabled |
            QtCore.Qt.ItemIsSelectable |
            QtCore.Qt.ItemNeverHasChildren
        )

        for k, v in shotgun.DB_KEYS.iteritems():
            if k == 'shotgun_name':
                data = name
            else:
                data = None
                for column in v['columns']:
                    if column in entity and entity[column] is not None:

                        # Attempt type verification
                        if not isinstance(entity[column], v['type']):
                            try:
                                data = v['type'](entity[column])
                                break
                            except:
                                log.error(u'Type conversion error.')
                                continue
                        else:
                            data = entity[column]

            item.setData(data, role=v['role'])

        model.appendRow(item)

    def showEvent(self, event):
        self.load_timer.start()
