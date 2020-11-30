# -*- coding: utf-8 -*-
"""The widget used to add a new asset (eg. a shot) to a bookmark.

See `templates.TemplatesWidget` for more information, the widget
responsible for listing, saving and expanding zip template files.

"""
import base64
from PySide2 import QtWidgets, QtGui, QtCore

from . import log
from . import common
from . import common_ui
from . import images
from . import bookmark_db
from . import shotgun
from . import shotgun_widgets

from . import templates


_widget_instance = None

numvalidator = QtGui.QRegExpValidator()
numvalidator.setRegExp(QtCore.QRegExp(ur'[0-9]+[\.]?[0-9]*'))

hint = u'Independent of the template, basic <span \
style="color:rgba({ADD});">mode</span> and <span \
style="color:rgba({ADD});">task</span> are defined in <span \
style="color:rgba({H});">Preferences -> Default Paths</span>. Ideally, both \
the template and the preferences should define the same folders.'


def _add_title(icon, label, parent, color=None):
    h = common.ROW_HEIGHT()
    o = common.MARGIN()
    row = common_ui.add_row(u'', parent=parent)
    if icon:
        _label = QtWidgets.QLabel(parent=parent)
        pixmap = images.ImageCache.get_rsc_pixmap(icon, color, h)
        _label.setPixmap(pixmap)
        row.layout().addWidget(_label, 0)
    else:
        row.layout().addSpacing(common.MARGIN())
    label = common_ui.PaintedLabel(
        label,
        size=common.MEDIUM_FONT_SIZE(),
        parent=parent
    )
    row.layout().addWidget(label, 0)
    row.layout().addStretch(1)


class AddAssetWidget(templates.TemplatesWidget):
    """Widget used to create a new asset in a specified folder.

    Args:
        path (unicode): Destination path for the new assets.
        update (bool=False): Enables the update mode, if the widget is used to edit an existing asset.

    """
    descriptionUpdated = QtCore.Signal(unicode)

    def __init__(self, server, job, root, asset=None, update=False, parent=None):
        global _widget_instance
        _widget_instance = self

        self.server = server
        self.job = job
        self.root = root
        self.asset = asset
        self._update = update

        self.description_editor = None
        self.shotgun_id_editor = None
        self.shotgun_name_editor = None
        self.shotgun_type_editor = None
        self.cut_duration_editor = None
        self.cut_in_editor = None
        self.cut_out_editor = None
        self.url1_editor = None
        self.url2_editor = None
        self.url1_button = None
        self.url2_button = None

        self.shotgun_button = None

        super(AddAssetWidget, self).__init__(u'asset', parent=parent)

        self.check_status_timer = QtCore.QTimer(parent=self)
        self.check_status_timer.setInterval(333)
        self.check_status_timer.setSingleShot(False)
        self.check_status_timer.timeout.connect(self.update)

        if not all((server, job, root)):
            raise RuntimeError(u'Bookmark not set.')

        if not parent:
            common.set_custom_stylesheet(self)

        if update:
            if not asset:
                raise ValueError(u'When update is true, the asset must be specified.')
            self.setWindowTitle(u'Update asset')
        else:
            self.setWindowTitle(u'Create asset')


        bookmark = u'{}/{}/{}'.format(server, job, root)
        self.set_path(bookmark)

        self.name_widget.setDisabled(update)
        self.templates_group.setHidden(update)
        if all((update, asset)):
            self.add_button.setText(u'Update asset')
            self.name_widget.setText(asset)

        self.templateCreated.connect(self.save)

        self.shotgun_button.clicked.connect(self.find_shotgun_id)
        self.url1_button.clicked.connect(lambda: self.visit_url(1))
        self.url2_button.clicked.connect(lambda: self.visit_url(2))

        if self._update:
            self.add_button.clicked.disconnect()
            self.add_button.clicked.connect(self.save)
            self.add_button.clicked.connect(self.close)
        else:
            self.add_button.clicked.connect(self.save)

    def _create_UI(self):
        """We extend the template widget with property fields for setting
        asset properties upon creation.

        """
        super(AddAssetWidget, self)._create_UI()

        h = common.ROW_HEIGHT()
        o = common.MARGIN()

        parent = self.scrollarea.widget()

        self.description_editor = common_ui.LineEdit(parent=parent)
        self.description_editor.setPlaceholderText(u'Enter a description...')
        self.description_editor.setFixedHeight(h)
        self.shotgun_id_editor = common_ui.LineEdit(parent=parent)
        self.shotgun_id_editor.setPlaceholderText(u'eg. 4')
        self.shotgun_id_editor.setValidator(numvalidator)
        self.shotgun_name_editor = common_ui.LineEdit(parent=parent)
        self.shotgun_name_editor.setPlaceholderText(u'Shotgun asset name, eg. "SH010"')

        self.shotgun_type_editor = QtWidgets.QComboBox(parent=parent)
        self.shotgun_type_editor.setFixedHeight(h * 0.7)
        for t in shotgun_widgets.SHOTGUN_TYPES:
            self.shotgun_type_editor.addItem(t, userData=t)

        pixmap = images.ImageCache.get_rsc_pixmap(
            u'shotgun', None, common.MARGIN() * 2)
        for n in xrange(self.shotgun_type_editor.model().rowCount()):
            index = self.shotgun_type_editor.model().index(n, 0)
            self.shotgun_type_editor.model().setData(
                index,
                QtCore.QSize(common.ROW_HEIGHT() * 0.66, common.ROW_HEIGHT() * 0.66),
                QtCore.Qt.SizeHintRole,
            )
            self.shotgun_type_editor.model().setData(
                index,
                QtGui.QIcon(pixmap),
                QtCore.Qt.DecorationRole,
            )

        self.cut_duration_editor = common_ui.LineEdit(parent=parent)
        self.cut_duration_editor.setPlaceholderText(u'Frame duration, eg. "150"')
        self.cut_duration_editor.setValidator(numvalidator)
        self.cut_in_editor = common_ui.LineEdit(parent=parent)
        self.cut_in_editor.setPlaceholderText(u'Start frame, eg. "1001"')
        self.cut_in_editor.setValidator(numvalidator)
        self.cut_out_editor = common_ui.LineEdit(parent=parent)
        self.cut_out_editor.setPlaceholderText(u'End frame, eg. "1150"')
        self.cut_out_editor.setValidator(numvalidator)

        self.url1_editor = common_ui.LineEdit(parent=parent)
        self.url1_editor.setPlaceholderText(u'https://my.customurl1.com...')
        self.url2_editor = common_ui.LineEdit(parent=parent)
        self.url2_editor.setPlaceholderText(u'https://my.customurl2.com...')

        self.shotgun_button = common_ui.PaintedButton(u'Find Shotgun ID and Name')
        self.shotgun_button.setFixedHeight(h * 0.7)
        self.url1_button = common_ui.PaintedButton(u'Visit')
        self.url1_button.setFixedHeight(h * 0.7)
        self.url2_button = common_ui.PaintedButton(u'Visit')
        self.url2_button.setFixedHeight(h * 0.7)

        grp = common_ui.get_group(parent=parent)

        row = common_ui.add_row(u'Description', height=h, parent=grp)
        row.layout().addWidget(self.description_editor, 1)

        grp = common_ui.get_group(parent=parent)

        _add_title(u'shotgun', u'Shotgun', grp)
        row = common_ui.add_row(u'Type', parent=grp, height=h)
        row.layout().addWidget(self.shotgun_type_editor, 1)
        row.layout().addWidget(self.shotgun_button, 0)
        row = common_ui.add_row(u'ID', parent=grp, height=h)
        row.layout().addWidget(self.shotgun_id_editor, 0)
        row = common_ui.add_row(u'Name', parent=grp, height=h)
        row.layout().addWidget(self.shotgun_name_editor, 0)

        grp = common_ui.get_group(parent=parent)
        _add_title(None, u'Cut', grp)
        row = common_ui.add_row(u'Duration', parent=grp, height=h)
        row.layout().addWidget(self.cut_duration_editor, 0)
        row = common_ui.add_row(u'In frame', parent=grp, height=h)
        row.layout().addWidget(self.cut_in_editor, 0)
        row = common_ui.add_row(u'Out frame', parent=grp, height=h)
        row.layout().addWidget(self.cut_out_editor, 0)

        grp = common_ui.get_group(parent=parent)
        _add_title(None, u'Custom URLs', grp)
        row = common_ui.add_row(u'URL1', parent=grp, height=h)
        row.layout().addWidget(self.url1_editor, 0)
        row.layout().addWidget(self.url1_button, 0)
        row = common_ui.add_row(u'URL2', parent=grp, height=h)
        row.layout().addWidget(self.url2_editor, 0)
        row.layout().addWidget(self.url2_button, 0)

    @QtCore.Slot(int)
    def visit_url(self, idx):
        w = getattr(self, 'url{}_editor'.format(idx))
        url = w.text()
        if not url:
            return
        QtGui.QDesktopServices.openUrl(url)


    @QtCore.Slot(int)
    def set_shotgun_id(self, name, id):
        self.shotgun_id_editor.setText(unicode(id))
        self.shotgun_name_editor.setText(name)

    @QtCore.Slot()
    def verify_shotgun_token(self, silent=False):
        """Check the validity of the Shotgun token."""
        domain = bookmark_db.get_property(u'shotgun_domain')
        script_name = bookmark_db.get_property(u'shotgun_scriptname')
        api_key = bookmark_db.get_property(u'shotgun_api_key')

        if not domain:
            common_ui.ErrorBox(
                u'Enter a valid Shotgun domain.',
                u'Make sure the domain starts with https://'
            ).open()
            log.error(u'Domain not yet entered.')
            return
        if not script_name:
            common_ui.ErrorBox(
                u'Enter a valid Shotgun API Script name.',
            ).open()
            log.error(u'Script name not yet entered.')
            return

        if not api_key:
            common_ui.ErrorBox(
                u'Enter a valid Shotgun Script Key.',
            ).open()
            log.error(u'Script key not yet entered.')
            return

        with shotgun.init_sg(domain, script_name, api_key) as sg:
            info = sg.info()
            if silent:
                return

            _info = u''
            for k, v in info.iteritems():
                _info += u'{}: {}'.format(k, v)
                _info += u'\n'
            common_ui.MessageBox(u'Successfully connected to Shotgun.', _info).open()

    @QtCore.Slot()
    def find_shotgun_id(self):
        """Opens a dialog to associate an asset with a shotgun entity.

        """
        print self.verify_shotgun_token(silent=True)

        # These properties are stored in the bookmark 'properties' table
        domain = bookmark_db.get_property(u'shotgun_domain')
        script_name = bookmark_db.get_property(u'shotgun_scriptname')
        api_key = bookmark_db.get_property(u'shotgun_api_key')
        project_id = bookmark_db.get_property(u'shotgun_id')

        # Pick our
        shotgun_type = self.shotgun_type_editor.currentText()

        w = shotgun_widgets.LinkToShotgunWidget(
            self.name_widget.text(),
            shotgun_type,
            domain,
            script_name,
            api_key,
            project_id=project_id,
        )
        w.linkRequested.connect(self.set_shotgun_id)
        w.exec_()

    @QtCore.Slot()
    def init_values(self):
        """Called when in update mode, populates the editable fields with the
        current values.

        """
        source = u'{}/{}/{}/{}'.format(
            self.server,
            self.job,
            self.root,
            self.asset
        )
        try:
            db = bookmark_db.get_db(self.server, self.job, self.root)
        except:
            common_ui.ErrorBox(
                u'Could not open the bookmark database',
                u'',
            ).open()
            log.error(u'Error saving properties.')
            return

        description = db.value(source, u'description')
        if description:
            description = base64.b64decode(description)
            self.description_editor.setText(description)

        for k in (
            u'shotgun_type',
            u'shotgun_id',
            u'shotgun_name',
            u'cut_duration',
            u'cut_in',
            u'cut_out',
            u'url1',
            u'url2',
        ):
            v = db.value(source, k)

            if v is None:
                continue
            elif not isinstance(v, (str, unicode)):
                v = unicode(v)

            w = getattr(self, k + '_editor')
            if 'shotgun_type' in k.lower():
                w.setCurrentText(v)
                continue

            w.setText(v)

    @QtCore.Slot()
    def save(self):
        """Save the thumbnail, description and shotgun properties."""
        try:
            db = bookmark_db.get_db(self.server, self.job, self.root)
        except:
            common_ui.ErrorBox(
                u'Could not open the bookmark database',
                u'',
            ).open()
            log.error(u'Error saving properties.')
            return

        if self._update:
            source = u'{}/{}/{}/{}'.format(
                self.server,
                self.job,
                self.root,
                self.asset
            )
        else:
            source = u'{}/{}/{}/{}'.format(
                self.server,
                self.job,
                self.root,
                self.name_widget.text()
            )

        # Description
        description = self.description_editor.text()
        description = base64.b64encode(description)
        db.setValue(source, u'description', description)

        if self._update:
            self.descriptionUpdated.emit(self.description_editor.text())

        for k in (
            u'shotgun_type',
            u'shotgun_id',
            u'shotgun_name',
            u'cut_duration',
            u'cut_in',
            u'cut_out',
            u'url1',
            u'url2',

        ):
            w = getattr(self, k + '_editor')
            if 'shotgun_type' in k.lower():
                v = w.currentText()
            else:
                v = w.text()
            db.setValue(source, k, v)

    def showEvent(self, event):
        if self._update:
            self.check_status_timer.start()
            self.init_values()

        app = QtWidgets.QApplication.instance()
        r = app.primaryScreen().availableGeometry()
        rect = self.frameGeometry()
        rect.moveCenter(r.center())
        self.move(rect.topLeft())
