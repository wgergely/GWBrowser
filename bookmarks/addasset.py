# -*- coding: utf-8 -*-
"""The widget used to add a new asset (eg. a shot) to a bookmark.

See `addbookmark.TemplatesWidget` for more information, the main widget
responsible for listing, saving and expanding zip template files.

"""
import base64
from PySide2 import QtWidgets, QtGui, QtCore

from . import log
from . import common
from . import common_ui
from . import images
from . import bookmark_db
from . import addbookmark
from . import shotgun
from . import shotgun_widgets


_widget_instance = None

numvalidator = QtGui.QRegExpValidator()
numvalidator.setRegExp(QtCore.QRegExp(ur'[0-9]+[\.]?[0-9]*'))

hint = u'Independent of the template, basic <span \
style="color:rgba({ADD});">mode</span> and <span \
style="color:rgba({ADD});">task</span> are defined in <span \
style="color:rgba({H});">Preferences -> Default Paths</span>. Ideally, both \
the template and the preferences should define the same folders.'



class AddAssetWidget(QtWidgets.QDialog):
    """Widget used to create a new asset in a specified folder.

    Args:
        path (unicode): Destination path for the new assets.

    """
    descriptionUpdated = QtCore.Signal(unicode)

    def __init__(self, server, job, root, asset=None, update=False, parent=None):
        global _widget_instance
        _widget_instance = self

        super(AddAssetWidget, self).__init__(parent=parent)
        if not all((server, job, root)):
            raise RuntimeError(u'Bookmark not set.')

        if not parent:
            common.set_custom_stylesheet(self)

        if update:
            if not asset:
                raise RuntimeError(u'When update is true, the asset must be specified.')
            self.setWindowTitle(u'Update asset')
        else:
            self.setWindowTitle(u'Add a new asset')

        self.server = server
        self.job = job
        self.root = root
        self.asset = asset
        self._update = update

        self.check_status_timer = QtCore.QTimer(parent=self)
        self.check_status_timer.setInterval(333)
        self.check_status_timer.setSingleShot(False)
        self.check_status_timer.timeout.connect(self.update)

        self.templates_widget = None
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
        self.save_button = None

        self._create_UI()

        bookmark = u'{}/{}/{}'.format(server, job, root)
        self.templates_widget.set_path(bookmark)
        if all((update, asset)):
            self.templates_widget.name_widget.setText(asset)

        self.templates_widget.templateCreated.connect(self.save)
        self.templates_widget.templateCreated.connect(self.popup)
        self.shotgun_button.clicked.connect(self.find_shotgun_id)
        self.url1_button.clicked.connect(lambda: self.visit_url(1))
        self.url2_button.clicked.connect(lambda: self.visit_url(2))

        self.save_button.clicked.connect(self.save)
        self.save_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))

    @QtCore.Slot(int)
    def visit_url(self, idx):
        w = getattr(self, 'url{}_editor'.format(idx))
        url = w.text()
        if not url:
            return
        QtGui.QDesktopServices.openUrl(url)


    def _create_UI(self):
        def _add_title(icon, label, parent, color=None):
            row = common_ui.add_row(u'', parent=parent)
            if icon:
                _label = QtWidgets.QLabel(parent=self)
                pixmap = images.ImageCache.get_rsc_pixmap(icon, color, h)
                _label.setPixmap(pixmap)
                row.layout().addWidget(_label, 0)
            else:
                row.layout().addSpacing(common.MARGIN())
            label = common_ui.PaintedLabel(
                label,
                size=common.MEDIUM_FONT_SIZE(),
                parent=self
            )
            row.layout().addWidget(label, 0)
            row.layout().addStretch(1)

        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN()
        h = common.ROW_HEIGHT()
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        self.templates_widget = addbookmark.TemplatesWidget(
            u'asset', parent=self)
        self.description_editor = common_ui.LineEdit(parent=self)
        self.description_editor.setPlaceholderText(u'Enter a description...')
        self.description_editor.setFixedHeight(h)
        self.shotgun_id_editor = common_ui.LineEdit(parent=self)
        self.shotgun_id_editor.setPlaceholderText(u'1234...')
        self.shotgun_id_editor.setValidator(numvalidator)
        self.shotgun_name_editor = common_ui.LineEdit(parent=self)
        self.shotgun_name_editor.setPlaceholderText(u'asset name...')

        self.shotgun_type_editor = QtWidgets.QComboBox(parent=self)
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

        self.cut_duration_editor = common_ui.LineEdit(parent=self)
        self.cut_duration_editor.setPlaceholderText(u'1234...')
        self.cut_duration_editor.setValidator(numvalidator)
        self.cut_in_editor = common_ui.LineEdit(parent=self)
        self.cut_in_editor.setPlaceholderText(u'1234...')
        self.cut_in_editor.setValidator(numvalidator)
        self.cut_out_editor = common_ui.LineEdit(parent=self)
        self.cut_out_editor.setPlaceholderText(u'1234...')
        self.cut_out_editor.setValidator(numvalidator)

        self.url1_editor = common_ui.LineEdit(parent=self)
        self.url1_editor.setPlaceholderText(u'https://my.customurl1.com...')
        self.url2_editor = common_ui.LineEdit(parent=self)
        self.url2_editor.setPlaceholderText(u'https://my.customurl2.com...')

        self.shotgun_button = common_ui.PaintedButton(u'Find Shotgun ID and Name')
        self.shotgun_button.setFixedHeight(h * 0.7)
        self.url1_button = common_ui.PaintedButton(u'Visit')
        self.url1_button.setFixedHeight(h * 0.7)
        self.url2_button = common_ui.PaintedButton(u'Visit')
        self.url2_button.setFixedHeight(h * 0.7)

        self.save_button = common_ui.ClickableIconButton(
            u'check',
            (common.ADD, common.ADD),
            common.ROW_HEIGHT(),
            parent=self
        )

        bookmark = u'{}/{}/{}'.format(self.server, self.job, self.root)
        source = images.get_thumbnail_path(
            self.server,
            self.job,
            self.root,
            bookmark
        )
        pixmap = images.ImageCache.get_pixmap(source, h)
        if not pixmap:
            source = images.get_placeholder_path(
                bookmark, fallback=u'thumb_bookmark_gray')
            pixmap = images.ImageCache.get_pixmap(source, h)
        thumbnail = QtWidgets.QLabel(parent=self)
        thumbnail.setPixmap(pixmap)

        if self._update:
            title_text = u'{}/{}:  Edit'.format(
                self.job.upper(), self.root.upper())
        else:
            title_text = u'{}/{}:  Add Asset'.format(
                self.job.upper(), self.root.upper())
        title_label = common_ui.PaintedLabel(
            title_text, size=common.LARGE_FONT_SIZE())
        _hint = hint.format(
            ADD=common.rgb(common.ADD),
            H=common.rgb(common.TEXT_SELECTED),
        )

        row = common_ui.add_row(u'', height=h, parent=self)
        row.layout().addWidget(thumbnail, 0)
        row.layout().addSpacing(o * 0.5)
        row.layout().addWidget(title_label)
        row.layout().addStretch(1)
        row.layout().addWidget(self.save_button)
        self.save_button.setHidden(not self._update)

        self.layout().addWidget(self.templates_widget, 1)
        row = common_ui.add_row(None, padding=None, height=h * 2, parent=self)


        row.layout().addWidget(self.description_editor, 1)
        if not self._update:
            row.layout().addSpacing(o * 2.5)

        grp = common_ui.get_group(parent=self)

        if not self._update:
            self.templates_widget.layout().itemAt(0).widget().layout().addWidget(row)
            d = common_ui.add_description(_hint, label=None, parent=self)
            self.templates_widget.layout().itemAt(1).widget().layout().addWidget(d)
            self.templates_widget.layout().addWidget(grp)
        self.templates_widget.setHidden(self._update)
        self.templates_widget.setDisabled(self._update)

        _add_title(u'shotgun', u'Shotgun Settings', grp)
        row = common_ui.add_row(u'Shotgun Type', parent=grp, height=h)
        row.layout().addWidget(self.shotgun_type_editor, 1)
        row.layout().addWidget(self.shotgun_button, 0)
        row = common_ui.add_row(u'Shotgun ID', parent=grp, height=h)
        row.layout().addWidget(self.shotgun_id_editor, 0)
        row = common_ui.add_row(u'Shotgun Name', parent=grp, height=h)
        row.layout().addWidget(self.shotgun_name_editor, 0)

        grp = common_ui.get_group(parent=self)
        _add_title(None, u'Cut', grp)
        row = common_ui.add_row(u'Cut Duration', parent=grp, height=h)
        row.layout().addWidget(self.cut_duration_editor, 0)
        row = common_ui.add_row(u'Cut In', parent=grp, height=h)
        row.layout().addWidget(self.cut_in_editor, 0)
        row = common_ui.add_row(u'Cut Out', parent=grp, height=h)
        row.layout().addWidget(self.cut_out_editor, 0)

        grp = common_ui.get_group(parent=self)
        _add_title(None, u'Custom URLs', grp)
        row = common_ui.add_row(u'URL1', parent=grp, height=h)
        row.layout().addWidget(self.url1_editor, 0)
        row.layout().addWidget(self.url1_button, 0)
        row = common_ui.add_row(u'URL2', parent=grp, height=h)
        row.layout().addWidget(self.url2_editor, 0)
        row.layout().addWidget(self.url2_button, 0)

        self.layout().addStretch(1)

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
        self.verify_shotgun_token(silent=True)

        # These prolperties are stored in the bookmark 'properties' table
        domain = bookmark_db.get_property(u'shotgun_domain')
        script_name = bookmark_db.get_property(u'shotgun_scriptname')
        api_key = bookmark_db.get_property(u'shotgun_api_key')
        project_id = bookmark_db.get_property(u'shotgun_id')

        # Pick our
        shotgun_type = self.shotgun_type_editor.currentText()

        w = shotgun_widgets.LinkToShotgunWidget(
            self.templates_widget.name_widget.text(),
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
            'shotgun_type',
            'shotgun_id',
            'shotgun_name',
            'cut_duration',
            'cut_in',
            'cut_out',
            'url1',
            'url2',
        ):
            v = db.value(source, k)
            if v is None:
                continue
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
                self.templates_widget.name_widget.text()
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


    @QtCore.Slot(unicode)
    def popup(self, v):
        """Notify the user of success."""
        common_ui.OkBox(
            u'Successully created "{}"'.format(v),
            u'',
        ).open()

    def showEvent(self, event):
        if self._update:
            self.check_status_timer.start()
            self.init_values()

        app = QtWidgets.QApplication.instance()
        r = app.primaryScreen().availableGeometry()
        rect = self.frameGeometry()
        rect.moveCenter(r.center())
        self.move(rect.topLeft())


    def sizeHint(self):
        """Custom size hint"""
        return QtCore.QSize(common.WIDTH(), common.HEIGHT())


if __name__ == '__main__':
    import bookmarks.standalone as standalone
    app = standalone.StandaloneApp([])
    w = AddAssetWidget('a', 'b', 'c', 'e', update=True)
    w.show()
    app.exec_()
