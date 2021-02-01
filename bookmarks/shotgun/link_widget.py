# -*- coding: utf-8 -*-
"""Shotgun Entity linker widgets.

The widets are used to link a Shotgun entity with a local item.

"""
import re
import functools
from PySide2 import QtWidgets, QtCore, QtGui

from .. import common
from .. import log
from .. import images
from .. import common_ui
from .. import bookmark_db
from .. import settings
from .. import actions

from . import shotgun
from . import actions as sg_actions


instance = None


def close():
    global instance
    if instance is None:
        return
    instance.close()
    instance.deleteLater()
    instance = None


class BaseLinkWidget(QtWidgets.QDialog):
    """Widget used to link a Shotgun entity with a local item.

    Args:
        entity_type (unicode): A shotgun entity type.
        sg_properties (type): A `sg_properties` data dict.

    """
    def __init__(self, entity_type, sg_properties, parent=None):
        super(BaseLinkWidget, self).__init__(parent=parent)

        self.sg_properties = sg_properties
        self.entity_type = entity_type

        self.combobox = None
        self.link_button = None
        self.visit_button = None
        self.create_button = None

        self.init_timer = QtCore.QTimer(parent=self)
        self.init_timer.setInterval(250)
        self.init_timer.setSingleShot(True)

        if not self.parent():
            common.set_custom_stylesheet(self)

        self.setWindowTitle(
            u'Select a {} Entity to Link'.format(self.entity_type.title()))

        self._create_ui()
        self._connect_signals()

    def _create_ui(self):
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN()
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        row = common_ui.add_row(
            u'Select {}'.format(self.entity_type.title()),
            height=common.ROW_HEIGHT(),
            parent=self
        )

        self.combobox = QtWidgets.QComboBox(parent=self)
        self.combobox.setMinimumWidth(common.WIDTH() * 0.5)
        self.combobox.setFixedHeight(common.ROW_HEIGHT())

        self.create_button = common_ui.PaintedButton(
            u'Create New', parent=self)
        self.visit_button = common_ui.PaintedButton(u'Visit', parent=self)

        row.layout().addWidget(self.combobox, 1)
        row.layout().addWidget(self.visit_button, 0)
        row.layout().addWidget(self.create_button, 0)

        row = common_ui.add_row(None, height=common.ROW_HEIGHT(), parent=self)

        self.link_button = common_ui.PaintedButton(
            u'Link {} Entity'.format(self.entity_type.title()),
            parent=self
        )

        row.layout().addWidget(self.link_button, 1)

    def _connect_signals(self):
        self.link_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))

        self.visit_button.clicked.connect(self.visit)
        self.create_button.clicked.connect(self.create)

        self.init_timer.timeout.connect(self.init_items)
        self.init_timer.timeout.connect(self.select_candidate)

    @common.error
    @common.debug
    def init_items(self):
        """Loads a list of Shotgun entities.

        """
        self.combobox.clear()

        self.combobox.addItem(u'Connecting to Shotgun....')
        QtWidgets.QApplication.instance().processEvents()

        try:
            entities = self.get_entities()
        except:
            self.add_error_item(u'An error occured.')
            raise

        if not entities:
            s = u'No {} found.'.format(self.entity_type.title())
            self.add_error_item(s)
            return

        self.combobox.clear()

        self.combobox.addItem(u'Entity not linked')
        self.decorate_item(self.combobox.count() - 1, placeholder=True)

        for entity in sorted(entities, key=shotgun.name_key):
            if shotgun.IdColumn not in entity:
                return None
            self.add_entity(entity)
            self.decorate_item(self.combobox.count() - 1)

    def add_entity(self, entity):
        def has(column):
            return column in entity and entity[column] is not None

        cbox = self.combobox
        name = shotgun.name_key(entity)
        cbox.addItem(name)

        _set = functools.partial(cbox.setItemData, cbox.count() - 1)

        for k, v in shotgun.DB_KEYS.iteritems():
            if k == u'shotgun_name':
                _set(name, role=v['role'])

            for column in v['columns']:
                if not has(column):
                    continue

                # Data will be loaded in order of preference as set in DB_KEYS:
                _set(entity[column], role=v['role'])
                break

        return name

    def done(self, result):
        if result == QtWidgets.QDialog.Rejected:
            super(BaseLinkWidget, self).done(result)
            return

        self.save_data()

        super(BaseLinkWidget, self).done(result)

    def add_error_item(self, name):
        self.combobox.clear()
        self.combobox.addItem(name)
        self.decorate_item(
            self.combobox.count() - 1,
            error=True
        )

    def decorate_item(self, idx, error=False, placeholder=False):
        self.combobox.setItemData(
            idx,
            QtCore.QSize(1, common.ROW_HEIGHT() * 0.8),
            role=QtCore.Qt.SizeHintRole
        )

        if placeholder:
            return

        label = u'close' if error else u'shotgun'
        color = common.REMOVE if error else None
        pixmap = images.ImageCache.get_rsc_pixmap(
            label, color, common.MARGIN() * 2)

        self.combobox.setItemData(
            idx,
            QtGui.QIcon(pixmap),
            role=QtCore.Qt.DecorationRole
        )

    @QtCore.Slot()
    def select_candidate(self):
        candidate = self.candidate()

        for n in xrange(self.combobox.model().rowCount()):
            index = self.combobox.model().index(n, 0)

            _name = index.data(shotgun.NameRole)
            if not _name:
                continue

            match = re.search(
                candidate,
                _name,
                flags=re.IGNORECASE | re.UNICODE
            )
            if not match:
                continue

            self.combobox.setCurrentIndex(n)
            break

    @common.error
    @common.debug
    def save_data(self):
        """Saves the current entity data to the bookmark database.

        We're using the `shotgun.DB_KEYS` structure definitions to map entity
        values to our bookmark database values.

        We're notifying the gui of any changes made via
        `actions.signals.*ValueUpdated` signals.

        """
        server = self.sg_properties[settings.ServerKey]
        job = self.sg_properties[settings.JobKey]
        root = self.sg_properties[settings.RootKey]
        asset = self.sg_properties[settings.AssetKey]

        if not all((server, job, root)):
            return

        for k, v in shotgun.DB_KEYS.iteritems():

            # Skip keys not in the our database table
            if k not in bookmark_db.TABLES[self.db_table()]:
                continue

            # Get value and ensure type
            value = self.combobox.currentData(v['role'])
            if value is not None and not isinstance(value, v['type']):
                try:
                    value = v['type'](value)
                except:
                    continue

            # Save value and emit change
            with bookmark_db.transactions(server, job, root) as db:
                db.setValue(
                    self.db_source(),
                    k,
                    value,
                    table=self.db_table()
                )

            if asset is None:
                actions.signals.bookmarkValueUpdated.emit(
                    self.db_source(), k, value)
            else:
                actions.signals.assetValueUpdated.emit(
                    self.db_source(), k, value)

        # Finally, let's verify and emit the current shotgun status
        if asset is None:
            sg_actions.bookmark_configuration_changed(server, job, root)
        else:
            sg_actions.asset_configuration_changed(server, job, root, asset)


    def db_source(self):
        raise NotImplementedError('Abstract method.')

    def create(self):
        editor = QtWidgets.QInputDialog(parent=self)
        editor.setOkButtonText(u'Create {}'.format(self.entity_type.title()))
        editor.setInputMode(QtWidgets.QInputDialog.TextInput)
        editor.setLabelText(u'Entity Name:')
        editor.setTextValue(self.candidate())
        editor.setMinimumWidth(common.WIDTH() * 0.66)
        editor.textValueSelected.connect(self.create_entity)

        editor.open()

    @common.error
    @common.debug
    @QtCore.Slot(unicode)
    def create_entity(self, text):
        """Creates a new Shotgun entity.

        The data needed to create the entity must be provided by
        self.new_entity_data().

        """
        with shotgun.connection(self.sg_properties) as sg:
            entity = sg.create(
                self.entity_type,
                self.new_entity_data(text),
                return_fields=shotgun.columns()
            )

        name = self.add_entity(entity)
        self.combobox.setCurrentText(name)

        import pprint
        info = pprint.pformat(entity, indent=4)
        common_ui.OkBox(
            u'{} was created successfully.'.format(name),
            'Entity data:\n\n{}'.format(info)
        ).open()

    @common.error
    @common.debug
    def visit(self):
        _id = self.combobox.currentData(shotgun.IdRole)
        _name = self.combobox.currentData(shotgun.NameRole)
        _type = self.combobox.currentData(shotgun.TypeRole)

        url = shotgun.ENTITY_URL.format(
            domain=self.sg_properties[shotgun.SGDomain],
            shotgun_type=_type,
            shotgun_id=_id
        )
        url = QtCore.QUrl(url)
        QtGui.QDesktopServices.openUrl(url)

    def new_entity_data(self, text):
        raise NotImplementedError('Abstract method.')

    def candidate(self):
        raise NotImplementedError('Abstract method.')

    def get_entities(self):
        raise NotImplementedError('Abstract method.')

    def showEvent(self, event):
        self.init_timer.start()

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH(), (common.MARGIN() * 2) + (common.ROW_HEIGHT() * 2))


class LinkBookmarkWidget(BaseLinkWidget):
    def __init__(self, sg_properties, parent=None):
        super(LinkBookmarkWidget, self).__init__(
            shotgun.ProjectEntity, sg_properties)

    @classmethod
    def show_editor(cls, sg_properties):
        global instance
        close()
        instance = cls(sg_properties)
        instance.open()
        return instance

    @common.error
    @common.debug
    def candidate(self):
        return self.sg_properties[settings.JobKey]

    @common.error
    @common.debug
    def get_entities(self):
        with shotgun.connection(self.sg_properties) as sg:
            return sg.find_projects()

    def db_source(self):
        server = self.sg_properties[settings.ServerKey]
        job = self.sg_properties[settings.JobKey]
        root = self.sg_properties[settings.RootKey]

        if not all((server, job, root)):
            return None

        return u'/'.join((server, job, root))

    def db_table(self):
        return bookmark_db.BookmarkTable

    def new_entity_data(self, text):
        return {
            shotgun.NameColumn: text
        }


class LinkAssetWidget(BaseLinkWidget):
    def __init__(self, sg_properties, parent=None):
        super(LinkAssetWidget, self).__init__(
            sg_properties[shotgun.SGAssetEntityType],
            sg_properties,
            parent=parent
        )

    @classmethod
    def show_editor(cls, sg_properties):
        if not sg_properties[shotgun.SGAssetEntityType]:
            common_ui.MessageBox(
                u'Shotgun Entity type is not selected.',
                'To link an asset, first select a shotgun type then try again.'
            ).open()
            return

        global instance
        close()
        instance = cls(sg_properties)
        instance.open()
        return instance

    @common.error
    @common.debug
    def candidate(self):
        return self.sg_properties[settings.AssetKey]

    @common.error
    @common.debug
    def get_entities(self):
        with shotgun.connection(self.sg_properties) as sg:
            entities = sg.find_entities(
                self.sg_properties[shotgun.SGBookmarkEntityID],
                self.entity_type,
                columns=shotgun.columns()
            )
            return entities

    def db_source(self):
        server = self.sg_properties[settings.ServerKey]
        job = self.sg_properties[settings.JobKey]
        root = self.sg_properties[settings.RootKey]
        asset = self.sg_properties[settings.AssetKey]

        if not all((server, job, root, asset)):
            return None

        return u'/'.join((server, job, root, asset))

    def db_table(self):
        return bookmark_db.AssetTable

    def new_entity_data(self, text):
        return {
            'project': {
                shotgun.TypeColumn: shotgun.ProjectEntity,
                shotgun.IdColumn: self.sg_properties[shotgun.SGBookmarkEntityID]
            },
            shotgun.CodeColumn: text,
        }
