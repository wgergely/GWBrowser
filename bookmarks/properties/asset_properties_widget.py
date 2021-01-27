# -*- coding: utf-8 -*-
"""Defines `AssetPropertiesWidget`, the widget used to create and edit assets.

"""
import _scandir
import functools
from PySide2 import QtWidgets, QtGui, QtCore


from .. import log
from .. import common
from .. import common_ui
from .. import bookmark_db
from .. import templates
from . import base


instance = None


def close():
    global instance
    if instance is None:
        return
    instance.close()
    instance.deleteLater()
    instance = None


def show(server, job, root, asset=None):
    global instance

    close()
    instance = AssetPropertiesWidget(
        server,
        job,
        root,
        asset=asset
    )
    instance.open()
    return instance


SECTIONS = {
    0: {
        'name': u'Basic Settings',
        'icon': u'',
        'color': common.SECONDARY_BACKGROUND,
        'groups': {
            0: {
                0: {
                    'name': u'Name',
                    'key': None,
                    'validator': base.namevalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Name, eg. \'SH0010\'',
                    'description': u'The asset\'s name, eg. \'SH0010\'.',
                },
                1: {
                    'name': u'Description',
                    'key': u'description',
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'A description, eg. \'My first shot\'',
                    'description': u'A short description of the asset, eg. \'My first shot.\'.',
                },
            },
            1: {
                0: {
                    'name': u'Template',
                    'key': None,
                    'validator': None,
                    'widget': functools.partial(templates.TemplatesWidget, templates.AssetTemplateMode),
                    'placeholder': None,
                    'description': u'Select a folder template to create this asset.',
                },
            },
        },
    },
    1: {
        'name': u'Shotgun Entity',
        'icon': u'shotgun',
        'color': None,
        'groups': {
            0: {
                0: {
                    'name': 'Link',
                    'key': 'link',
                    'validator': None,
                    'widget': None,
                    'placeholder': None,
                    'description': u'Sync the current asset with a Shotgun Entity',
                    'button': u'Link or Update',
                    },
                1: {
                    'name': u'Type',
                    'key': u'shotgun_type',
                    'validator': base.intvalidator,
                    'widget': functools.partial(base.ShotgunTypeWidget, base.ShotgunTypeWidget.AssetTypes),
                    'placeholder': None,
                    'description': u'Select a Shotgun asset type',
                },
                2: {
                    'name': u'ID',
                    'key': u'shotgun_id',
                    'validator': base.intvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Shotgun Project ID, eg. \'774\'',
                    'description': u'The Shotgun ID number this bookmark is associated with. Eg. \'774\'. You can find your project\'s ID number using the \'Find Shotgun ID\' button, via the shotgun API, or Shotgun website.\'',
                },
                3: {
                    'name': u'Name',
                    'key': u'shotgun_name',
                    'validator': None,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Shotgun entity name, eg. \'MyProject\'',
                    'description': u'The Shotgun entity name. The entity can be a shot, sequence or asset.\nClick "Link with Shotgun" to get the name and the id from the Shotgun server.',
                },
            }
        }
    },
    2: {
        'name': u'Cut',
        'icon': u'todo',
        'color': common.SECONDARY_BACKGROUND,
        'groups': {
            0: {
                0: {
                    'name': u'In Frame',
                    'key': u'cut_in',
                    'validator': base.intvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'In frame, eg. \'1150\'',
                    'description': u'The frame this asset starts at, eg. \'1150\'.',
                },
                1: {
                    'name': u'Out Frame',
                    'key': u'cut_out',
                    'validator': base.intvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Out frame, eg. \'1575\'',
                    'description': u'The frame this asset ends at, eg. \'1575\'.',
                },
                2: {
                    'name': u'Cut Duration',
                    'key': u'cut_duration',
                    'validator': base.intvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': u'Duration in frames, eg. \'425\'',
                    'description': u'The asset\'s duration in frames, eg. \'425\'.',
                },
            },
        },
    },
    3: {
        'name': u'URLs',
        'icon': u'',
        'color': common.SECONDARY_BACKGROUND,
        'groups': {
            0: {
                0: {
                    'name': u'Primary',
                    'key': u'url1',
                    'validator': base.domainvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': 'https://my.custom-url.com',
                    'description': u'A custom url of the bookmarks, eg. https://sheets.google.com/123',
                    'button': u'Visit',
                },
                1: {
                    'name': u'Scondary',
                    'key': u'url2',
                    'validator': base.domainvalidator,
                    'widget': common_ui.LineEdit,
                    'placeholder': 'https://my.custom-url.com',
                    'description': u'A custom url of the bookmarks, eg. https://sheets.google.com/123',
                    'button': u'Visit',
                }
            }
        }
    }
}


class AssetPropertiesWidget(base.PropertiesWidget):
    """Widget used to create a new asset in a specified bookmark, or when
    the optional `asset` argument is set, updates the asset properties.

    Args:
        path (unicode): Destination path for the new assets.
        update (bool=False): Enables the update mode, if the widget is used to edit an existing asset.

    """
    assetUpdated = QtCore.Signal(unicode)

    def __init__(self, server, job, root, asset=None, parent=None):
        if asset:
            buttons = (u'Update', u'Cancel')
        else:
            buttons = (u'Create Asset', u'Cancel')

        super(AssetPropertiesWidget, self).__init__(
            SECTIONS,
            server,
            job,
            root,
            asset=asset,
            db_table=bookmark_db.AssetTable,
            fallback_thumb=u'thumb_item_gray',
            buttons=buttons,
            parent=parent
        )

        if asset:
            # When `asset` is set, the template_editor is no longer needed
            self.name_editor.setText(asset)
            self.name_editor.setDisabled(True)
            self.template_editor.parent().parent().setHidden(True)
            self.setWindowTitle(
                u'{}/{}/{}/{}'.format(server, job, root, asset))
        else:
            self.setWindowTitle(
                u'{}/{}/{}: Create Asset'.format(server, job, root))
            self.name_editor.setFocus()

    def name(self):
        """Returns the name of the asset.

        """
        name = self.name_editor.text()
        name = self.asset if self.asset else name
        return name if name else None

    def db_source(self):
        """The source used to associate the saved data in the database.

        """
        if not self.name():
            return None
        return u'{}/{}/{}/{}'.format(
            self.server,
            self.job,
            self.root,
            self.name()
        )

    def init_data(self):
        """Load the current data from the database.

        """
        self._init_db_data()
        self._set_completer()
        self._disable_shotgun()

    def _disable_shotgun(self):
        args = (self.server, self.job, self.root)
        with bookmark_db.transactions(*args) as db:
            source = u'/'.join(args)

            shotgun_api_key = db.value(
                source,
                u'shotgun_api_key',
                table=bookmark_db.BookmarkTable
            )
            shotgun_scriptname = db.value(
                source,
                u'shotgun_scriptname',
                table=bookmark_db.BookmarkTable
            )

            if not all((shotgun_api_key, shotgun_scriptname)):
                self.shotgun_type_editor.parent().parent().parent().setDisabled(True)
                self.shotgun_type_editor.parent().parent().parent().setHidden(True)

    def _set_completer(self):
        """Add the current list of assets to the name editor's completer.

        """
        source = u'/'.join((self.server, self.job, self.root))
        items = [f.name for f in _scandir.scandir(source) if f.is_dir()]
        completer = QtWidgets.QCompleter(items, parent=self)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        common.set_custom_stylesheet(completer.popup())
        self.name_editor.setCompleter(completer)

    def save_changes(self):
        """Save changed data to the database.

        """
        try:
            self._save_db_data()
            v = self.description_editor.text()
            self.valueUpdated.emit(self.db_source(), common.DescriptionRole, v)
        except:
            s = u'Could not save properties to the database.'
            log.error(s)
            common_ui.ErrorBox('Error', s).open()
            return False

        try:
            self.thumbnail_editor.save_image()
            self.thumbnailUpdated.emit(self.db_source())
        except:
            s = u'Failed to save the thumbnail.'
            log.error(s)
            common_ui.ErrorBox('Error', s).open()
            return False

        self.itemUpdated.emit(self.db_source())
        return True

    def done(self, result):
        if result == QtWidgets.QDialog.Accepted:
            if not self._create_asset():
                return
        super(AssetPropertiesWidget, self).done(result)

    def _create_asset(self):
        name = self.name()
        editor = self.template_editor.template_list_widget
        has_template = editor.selectionModel().hasSelection()

        if self.asset is None and not name:
            common_ui.ErrorBox(
                u'Could not create asset.',
                u'Enter a name and try again.'
            ).open()
            return False
        elif self.asset is None and not has_template:
            common_ui.ErrorBox(
                u'Could not create asset.',
                u'Select a template and try again.'
            ).open()
            return False
        elif self.asset is None and name and has_template:
            res = editor.create(
                name,
                u'/'.join((self.server, self.job, self.root))
            )
            if not res:
                log.error(u'Failed to create asset.')
                return False

            path = u'/'.join((self.server, self.job, self.root, name))
            self.itemCreated.emit(path)

            common_ui.OkBox(u'"{}" created.'.format(name), u'').open()

        return True

    def _get_project_id(self):
        source = u'{}/{}/{}'.format(self.server, self.job, self.root)
        with bookmark_db.transactions(self.server, self.job, self.root) as db:
            v = db.value(source, u'shotgun_id', table=bookmark_db.BookmarkTable)
        if not isinstance(v, int):
            raise RuntimeError(u'Shotgun Project ID has not yet been set.')
        return v

    @common.error
    @QtCore.Slot()
    def link_button_clicked(self):
        if self._db_table is not None:
            self.save_changes()

        from ..shotgun import bulk_link_widget
        if self.shotgun_name_editor.text():
            custom_suggestions = (self.shotgun_name_editor.text(), )
        else:
            custom_suggestions = ()

        w = bulk_link_widget.BulkLinkWidget(
            (self.name(), ),
            self.server,
            self.job,
            self.root,
            custom_suggestions=custom_suggestions,
        )
        w.dataSaved.connect(self.init_data)
        w.open()
