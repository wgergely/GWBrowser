# -*- coding: utf-8 -*-
"""Settings window for editing bookmark properties.

Used to edit data in the bookmark database (see `bookmark_db.py`). The database
stores information about the bookmark's default `width`, `height`, `frame rate`
and connectivity information, such as `Slack` and `Shotgun` tokens.

Usage:

    widget = BookmarkPropertiesWidget(
        'server', 'job', 'root'
    ).open()


"""
import re
import  collections
import datetime

from PySide2 import QtCore, QtGui, QtWidgets

from .. import log
from .. import common
from .. import common_ui
from .. import images
from .. import settings
from .. import bookmark_db
from .. import shotgun
from .. import shotgun_widgets


_widget_instance = None


numvalidator = QtGui.QRegExpValidator()
numvalidator.setRegExp(QtCore.QRegExp(ur'[0-9]+[\.]?[0-9]*'))
textvalidator = QtGui.QRegExpValidator()
textvalidator.setRegExp(QtCore.QRegExp(ur'[a-zA-Z0-9]+'))
domainvalidator = QtGui.QRegExpValidator()
domainvalidator.setRegExp(QtCore.QRegExp(ur'[a-zA-Z0-9/:\.]+'))


EDITORS = collections.OrderedDict({
    0: {
        'name': 'Default Output Properties',
        'icon': 'settings',
        'editors': {
            'framerate': {
                'type': None,
                'validator': None,
                'widget': None
            },
            'width': {
                'type': None,
                'validator': None,
                'widget': None
            },
            'height': {
                'type': None,
                'validator': None,
                'widget': None
            },
        }
    },
        'prefix': {
            'type': None,
            'validator': None,
            'widget': None
        },
        'startframe': {
            'type': None,
            'validator': None,
            'widget': None
        },
        'duration': {
            'type': None,
            'validator': None,
            'widget': None
        },
        'format': {
            'type': None,
            'validator': None,
            'widget': None
        },
        'identifier': {
            'type': None,
            'validator': None,
            'widget': None
        },
        'slacktoken': {
            'type': None,
            'validator': None,
            'widget': None
        },
        'shotgun_domain': {
            'type': None,
            'validator': None,
            'widget': None
        },
        'shotgun_scriptname': {
            'type': None,
            'validator': None,
            'widget': None
        },
        'shotgun_api_key': {
            'type': None,
            'validator': None,
            'widget': None
        },
        'shotgun_id': {
            'type': None,
            'validator': None,
            'widget': None
        },
        'shotgun_name': {
            'type': None,
            'validator': None,
            'widget': None
        },
        'shotgun_type': {
            'type': None,
            'validator': None,
            'widget': None
        },
        'url1': {
            'type': None,
            'validator': None,
            'widget': None
        },
        'url2': {
            'type': None,
            'validator': None,
            'widget': None
        },
        'asset_config': {
            'type': None,
            'validator': None,
            'widget': None
        }
})

def add_title(icon, label, parent, color=None):
    o = common.MARGIN()
    h = common.ROW_HEIGHT()

    row = common_ui.add_row(u'', parent=parent)

    _label = QtWidgets.QLabel(parent=parent)
    pixmap = images.ImageCache.get_rsc_pixmap(icon, color, h * 0.7)
    _label.setPixmap(pixmap)
    row.layout().addWidget(_label, 0)

    label = common_ui.PaintedLabel(
        label,
        size=common.MEDIUM_FONT_SIZE(),
        parent=parent
    )
    row.layout().addWidget(label, 0)
    row.layout().addStretch(1)
    parent.layout().addSpacing(o * 0.5)


slack_hint = u'To send  messaged using Slack, create a new Slack App and paste a \
valid <span style="{h}">OAuth</span> token, usually starting with "xoxb-0123..." \
above. See <a href="https://api.slack.com/apps">api.slack.com/apps</a> for more \
information.<br><br> Make sure the app has the <span \
style="{h}">users:read</span> and <span style="{h}">chat:write</span> scopes \
enabled. To send messages to channels the bot is not part of, add <span \
style="{h}">chat:write.public</span>. Scopes <span \
style="{h}">channels:read</span> and <span style="{h}">groups:read</span> are \
needed to list available Slack Channels.<br><br>'

identifier_hint = u'Only folders containing this file will be read as assets. \
Using the default Maya Workspace the identifier normally is <span \
style="text-decoration: underline;">workspace.mel</span>, but any other file can \
be used as long it is present in the root of the asset folder. When left empty, \
all folders in the bookmark folder will be interpeted as assets.'

shotgun_domain_hint = u'Dont\'t forget to include http:// or https://.'
shotgun_api_hint = u'Make sure your Shotgun project has a valid API Script set up. \
This can be done from the Shotgun Admin menu -> Scripts option. See the \
<a href="https://support.shotgunsoftware.com/">Shotgun</a> documentation for \
more information.'


SHOTGUN_TYPES = (
    u'Project',
)


def preference_key(name):
    return u'bookmark_properties_editor/{}'.format(name)


class FormatPreviewWidget(QtWidgets.QLabel):
    """Previews the current format."""

    def __init__(self, parent=None):
        super(FormatPreviewWidget, self).__init__(parent=parent)
        self._width = 0.0
        self._height = 0.0
        self._fps = 0.0
        self._prefix = u''
        self._start = 0.0
        self._duration = 0.0

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        self.setMinimumHeight(common.HEIGHT() * 0.30)
        self.setMinimumWidth(common.WIDTH() * 0.15)

    @QtCore.Slot()
    def set_attr(self, k, v, type=float):
        v = type(v) if v else None
        if not v:
            return
        setattr(self, k, v)
        self.repaint()

    def paintEvent(self, event):
        """Custom paint event for visualising the format rectangle.

        """
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        w = self._width + 0.01
        h = self._height + 0.01
        rect = self.rect()
        factor = rect.height() / h
        w *= factor
        h *= factor
        if w > rect.width():
            factor = rect.width() / w
            w *= factor
            h *= factor

        rect = QtCore.QRect(0, 0, w, h)
        rect.moveCenter(self.rect().center())
        i = common.INDICATOR_WIDTH()
        rect = rect.adjusted(i, i, -i, -i)

        # Outline
        painter.setOpacity(0.2)
        pen = QtGui.QPen(common.TEXT_SELECTED)
        pen.setWidthF(common.ROW_SEPARATOR() * 2.0)
        pen.setStyle(QtCore.Qt.SolidLine)
        pen.setJoinStyle(QtCore.Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)

        if (self._width and self._height):
            painter.drawRect(rect)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.TEXT)

        if (self._width and self._height):
            painter.drawRect(rect)
        painter.setOpacity(1.0)

        painter.setPen(common.TEXT)
        font, _ = common.font_db.primary_font(
            font_size=common.SMALL_FONT_SIZE())
        painter.setFont(font)
        _rect = self.rect()
        _rect.setLeft(rect.left() + common.SMALL_FONT_SIZE())

        text = u'{w}{h}{fps}{pre}{start}{duration}'.format(
            w=u'{}px'.format(int(self._width)) if self._width else u'',
            h=u' * {}px'.format(int(self._height)) if self._height else u'',
            fps=u'  |  {}fps'.format(self._fps) if self._fps else u'',
            pre=u'\n{}'.format(self._prefix) if self._prefix else u'',
            start=u'\nIn: {}'.format(int(self._start)) if self._start else u'',
            duration=u'\nOut: {}\nDuration: {}'.format(
                int(self._start) + int(self._duration),
                int(self._duration) if self._duration else u'') if self._duration else u''
        )
        painter.drawText(
            _rect,
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter | QtCore.Qt.TextWordWrap,
            text if text else u'Bookmark not yet configured'
        )
        painter.end()


class BookmarkPropertiesWidget(QtWidgets.QDialog):
    """The widget containing all the UI elements used to edit
    Bookmark properties, such as frame rate, resolution and Shotgun properties.

    Usage:
        Initialize with the server, job, root name, eg:

        widget = BookmarkPropertiesWidget(
            'server', 'job', 'root'
        ).open()

    """

    def __init__(self, server, job, root, parent=None):
        global _widget_instance
        _widget_instance = self

        super(BookmarkPropertiesWidget, self).__init__(parent=parent)
        if not self.parent():
            common.set_custom_stylesheet(self)

        self.scrollarea = None
        self.server = server
        self.job = job
        self.root = root

        self.save_button = None
        self.cancel_button = None
        self.load_combobox = None

        for k in EDITORS:
            setattr(self, k, None)

        self.framerate_editor = None
        self.width_editor = None
        self.height_editor = None
        self.prefix_editor = None
        self.startframe_editor = None
        self.duration_editor = None
        self.format_widget = None
        self.identifier_editor = None
        self.slacktoken_editor = None
        self.shotgun_domain_editor = None
        self.shotgun_scriptname_editor = None
        self.shotgun_api_key_editor = None
        self.shotgun_id_editor = None
        self.shotgun_name_editor = None
        self.shotgun_type_editor = None
        self.url1_editor = None
        self.url2_editor = None

        self.suggest_prefix_button = None
        self.shotgun_button = None

        self.check_status_timer = QtCore.QTimer(parent=self)
        self.check_status_timer.setInterval(333)
        self.check_status_timer.setSingleShot(False)
        self.check_status_timer.timeout.connect(self.update)

        self.setMinimumWidth(common.WIDTH())
        self.setMinimumHeight(common.HEIGHT() * 1.5)
        self.setWindowTitle(u'Bookmark Properties')
        self.setObjectName(u'BookmarkProperties')

        self._create_UI()
        self._connect_signals()


    def _create_UI(self):
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN()
        h = common.ROW_HEIGHT()
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(o * 0.5)

        self.scrollarea = QtWidgets.QScrollArea(parent=self)
        self.scrollarea.setWidgetResizable(True)

        parent = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(parent)
        parent.layout().setAlignment(QtCore.Qt.AlignCenter)
        parent.layout().setContentsMargins(o, o, o, o)
        parent.layout().setSpacing(o * 0.5)
        self.scrollarea.setWidget(parent)

        self.format_widget = FormatPreviewWidget(parent=self)

        self.width_editor = common_ui.LineEdit(parent=self)
        self.width_editor.setPlaceholderText(u'Width...')
        self.width_editor.setValidator(numvalidator)

        self.height_editor = common_ui.LineEdit(parent=self)
        self.height_editor.setPlaceholderText(u'Height...')
        self.height_editor.setValidator(numvalidator)

        self.framerate_editor = common_ui.LineEdit(parent=self)
        self.framerate_editor.setPlaceholderText(u'Frame rate...')
        self.framerate_editor.setValidator(numvalidator)

        self.prefix_editor = common_ui.LineEdit(parent=self)
        self.prefix_editor.setPlaceholderText(u'Prefix (eg. \'MYJOB\')...')
        self.prefix_editor.setValidator(textvalidator)

        self.suggest_prefix_button = common_ui.PaintedButton(
            u'Suggest', parent=self)
        self.suggest_prefix_button.setFixedHeight(h * 0.7)

        self.startframe_editor = common_ui.LineEdit(parent=self)
        self.startframe_editor.setPlaceholderText(u'Start Frame...')
        self.startframe_editor.setValidator(numvalidator)

        self.duration_editor = common_ui.LineEdit(parent=self)
        self.duration_editor.setPlaceholderText(u'Duration...')
        self.duration_editor.setValidator(numvalidator)

        self.identifier_editor = common_ui.LineEdit(parent=self)
        self.identifier_editor.setPlaceholderText(
            u'Asset identifier, eg. \'workspace.mel\'')

        self.slacktoken_editor = common_ui.LineEdit(parent=self)
        self.slacktoken_editor.setEchoMode(QtWidgets.QLineEdit.Password)
        self.slacktoken_editor.setPlaceholderText(
            u'xoxb-01234567890-0123456...')

        self.slacktoken_button = common_ui.PaintedButton(u'Test')
        self.slacktoken_button.setFixedHeight(h * 0.7)

        self.shotgun_domain_editor = common_ui.LineEdit(parent=self)
        self.shotgun_domain_editor.setPlaceholderText(
            u'https://studio.shotgunstudio.com')
        self.shotgun_domain_editor.setValidator(domainvalidator)
        self.shotgun_api_key_editor = common_ui.LineEdit(parent=self)
        self.shotgun_api_key_editor.setEchoMode(QtWidgets.QLineEdit.Password)
        self.shotgun_api_key_editor.setPlaceholderText(
            u'abcdefghijklmno3bqr*1')
        self.shotgun_api_key_button = common_ui.PaintedButton(
            u'Verify Application Key')
        self.shotgun_api_key_button.setFixedHeight(h * 0.7)

        self.shotgun_scriptname_editor = common_ui.LineEdit(parent=self)
        self.shotgun_scriptname_editor.setEchoMode(
            QtWidgets.QLineEdit.Password)
        self.shotgun_scriptname_editor.setPlaceholderText(u'myapiscript')

        self.shotgun_id_editor = common_ui.LineEdit(parent=self)
        self.shotgun_id_editor.setPlaceholderText(u'Shotgun ID, eg. "75"')
        self.shotgun_id_editor.setValidator(numvalidator)

        self.shotgun_name_editor = common_ui.LineEdit(parent=self)
        self.shotgun_name_editor.setPlaceholderText(u'Shotgun name...')

        self.shotgun_type_editor = QtWidgets.QComboBox(parent=self)
        self.shotgun_type_editor.setFixedHeight(h * 0.7)
        for t in SHOTGUN_TYPES:
            self.shotgun_type_editor.addItem(t, userData=t)

        self.shotgun_button = common_ui.PaintedButton(
            u'Find Shotgun ID and Name')
        self.shotgun_button.setFixedHeight(h * 0.7)

        self.url1_editor = common_ui.LineEdit(parent=self)
        self.url1_editor.setPlaceholderText(u'http://my.custom-link.com')

        self.url2_editor = common_ui.LineEdit(parent=self)
        self.url2_editor.setPlaceholderText(u'http://my.custom-link.com')

        self.load_combobox = QtWidgets.QComboBox(parent=self)
        self.load_combobox.setFixedHeight(h * 0.7)

        self.save_button = common_ui.PaintedButton(
            u'Save Properties',
            parent=self
        )
        self.save_button.setFixedHeight(h * 0.7)

        self.cancel_button = common_ui.PaintedButton(
            u'Cancel',
            parent=self
        )
        self.cancel_button.setFixedHeight(h * 0.7)

        # Thumbnail and Title
        row = common_ui.add_row(None, padding=None, parent=parent, height=None)

        pixmap, color = images.get_thumbnail(
            (self.server, self.job, self.root),
            u'{}/{}/{}'.format(self.server, self.job, self.root),
            int(h * 1.5),
            fallback_thumb=u'thumb_bookmark_gray'
        )
        if pixmap:
            thumbnail = QtWidgets.QLabel(parent=self)
            thumbnail.setPixmap(pixmap)
            row.layout().addWidget(thumbnail, 0)

        title = u'{}  -  {}'.format(
            self.job.replace(u'_', u' '),
            self.root
        )
        label = common_ui.PaintedLabel(title, size=common.LARGE_FONT_SIZE())

        row.layout().addStretch(1)
        row.layout().addWidget(label)

        # Load settings
        row = common_ui.add_row(u'Load settings', parent=parent, height=h)
        row.layout().addStretch(1)
        row.layout().addWidget(self.load_combobox, 0)

        # Default properties
        maingroup = common_ui.get_group(margin=o, parent=parent)
        add_title(
            u'settings',
            u'Default Output Properties',
            maingroup,
            color=common.SECONDARY_BACKGROUND
        )
        grp = common_ui.get_group(parent=maingroup)
        grp.layout().addWidget(self.format_widget, 1)
        row = common_ui.add_row(u'Resolution', parent=grp, height=h)
        row.layout().addWidget(self.width_editor, 0)
        row.layout().addWidget(self.height_editor, 0)
        row = common_ui.add_row(u'Frame rate', parent=grp, height=h)
        row.layout().addWidget(self.framerate_editor, 0)
        grp = common_ui.get_group(parent=maingroup)
        row = common_ui.add_row(u'Bookmark prefix', parent=grp, height=h)
        row.layout().addWidget(self.prefix_editor, 0)
        row.layout().addWidget(self.suggest_prefix_button, 0)
        grp = common_ui.get_group(parent=maingroup)
        row = common_ui.add_row(u'Start frame', parent=grp, height=h)
        row.layout().addWidget(self.startframe_editor, 0)
        row = common_ui.add_row(u'Duration', parent=grp, height=h)
        row.layout().addWidget(self.duration_editor, 0)
        grp = common_ui.get_group(parent=maingroup)
        row = common_ui.add_row(u'Asset identifier', parent=grp)
        row.layout().addWidget(self.identifier_editor, 0)
        text = identifier_hint
        common_ui.add_description(text, label=u'Hint', parent=grp)

        # Custom URLs
        maingroup = common_ui.get_group(margin=o, parent=parent)

        add_title(
            u'bookmark',
            u'Bookmark URLs',
            maingroup,
            color=common.SECONDARY_BACKGROUND
        )
        grp = common_ui.get_group(parent=maingroup)
        row = common_ui.add_row(u'URL', parent=grp, height=h)
        row.layout().addWidget(self.url1_editor, 0)
        row = common_ui.add_row(u'URL', parent=grp, height=h)
        row.layout().addWidget(self.url2_editor, 0)

        # Shotgun
        maingroup = common_ui.get_group(parent=parent)
        maingroup.layout().setContentsMargins(o, o, o, o)

        add_title(
            u'shotgun',
            u'Shotgun',
            maingroup
        )

        grp = common_ui.get_group(parent=maingroup)
        row = common_ui.add_row(u'Domain', parent=grp, height=h)
        row.layout().addWidget(self.shotgun_domain_editor, 0)
        common_ui.add_description(
            shotgun_domain_hint, label=u'Hint', parent=grp)
        grp = common_ui.get_group(parent=maingroup)
        row = common_ui.add_row(u'Script name', parent=grp, height=h)
        row.layout().addWidget(self.shotgun_scriptname_editor, 0)
        row = common_ui.add_row(u'Application key', parent=grp, height=h)
        row.layout().addWidget(self.shotgun_api_key_editor, 0)
        row.layout().addWidget(self.shotgun_api_key_button, 0)
        common_ui.add_description(shotgun_api_hint, label=u'Hint', parent=grp)

        row = common_ui.add_row(u'', parent=grp, height=h)
        row = common_ui.add_row(u'Type', parent=grp, height=h)
        row.layout().addWidget(self.shotgun_type_editor, 1)
        row.layout().addWidget(self.shotgun_button, 0)
        row = common_ui.add_row(u'ID', parent=grp, height=h)
        row.layout().addWidget(self.shotgun_id_editor, 0)
        row = common_ui.add_row(u'Name', parent=grp, height=h)
        row.layout().addWidget(self.shotgun_name_editor, 0)


        # Slack
        maingroup = common_ui.get_group(parent=parent)
        maingroup.layout().setContentsMargins(o, o, o, o)

        add_title(
            u'slack_color',
            u'Slack',
            maingroup
        )

        # Slack
        grp = common_ui.get_group(parent=maingroup)
        row = common_ui.add_row(u'API token', parent=grp, height=h)
        row.layout().addWidget(self.slacktoken_editor, 0)
        row.layout().addWidget(self.slacktoken_button)
        text = slack_hint.format(
            h=u'color: rgba({});'.format(common.rgb(common.ADD)))
        common_ui.add_description(text, label=u'Hint', parent=grp)


        # Info group
        maingroup = common_ui.get_group(margin=o, parent=parent)
        maingroup.layout().setSpacing(0)
        add_title(
            u'bookmark',
            u'Database Info',
            maingroup,
            color=common.SECONDARY_BACKGROUND
        )

        db = bookmark_db.get_db(
            self.server,
            self.job,
            self.root
        )

        for k in bookmark_db.BOOKMARK_DB[u'info']:
            if k.startswith('id'):
                continue
            row = common_ui.add_row(k.title(), parent=maingroup, height=h * 0.7)
            with db.transactions():
                try:
                    source = u'{}/{}/{}'.format(self.server, self.job, self.root)

                    val = db.value(source, k, table=u'info')
                    if k == u'created':
                        try:
                            val = datetime.datetime.fromtimestamp(float(val)).strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            val = u'error'
                    if not val:
                        continue

                    label = QtWidgets.QLabel(parent=parent)
                    label.setText(unicode(val))
                    label.setDisabled(True)

                    row.layout().addWidget(label, 1)
                except:
                    pass

        self.layout().addWidget(self.scrollarea)

        row = common_ui.add_row(None, padding=None, height=h, parent=self)
        row.layout().addStretch(1)
        row.layout().addWidget(self.cancel_button, 0)
        row.layout().addWidget(self.save_button, 0)
        row.layout().addStretch(1)

    def _connect_signals(self):
        self.slacktoken_button.clicked.connect(self.verify_slack_token)
        self.shotgun_button.clicked.connect(self.find_shotgun_id)
        self.shotgun_api_key_button.clicked.connect(self.verify_shotgun_token)

        self.width_editor.textEdited.connect(
            lambda v: self.format_widget.set_attr(u'_width', v))
        self.height_editor.textEdited.connect(
            lambda v: self.format_widget.set_attr(u'_height', v))
        self.framerate_editor.textEdited.connect(
            lambda v: self.format_widget.set_attr(u'_fps', v))
        self.prefix_editor.textEdited.connect(
            lambda v: self.format_widget.set_attr(u'_prefix', v, type=unicode))
        self.startframe_editor.textEdited.connect(
            lambda v: self.format_widget.set_attr(u'_start', v))
        self.duration_editor.textEdited.connect(
            lambda v: self.format_widget.set_attr(u'_duration', v))

        self.suggest_prefix_button.clicked.connect(self.suggest_prefix)

        self.save_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))

        self.cancel_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Rejected))

        self.load_combobox.activated.connect(self.load_from_previous)

    @QtCore.Slot()
    def suggest_prefix(self):
        substrings = re.sub(ur'[\_\-\s]+', u';', self.job).split(u';')
        prefix = ''
        for s in substrings:
            prefix += s[0]

        self.prefix_editor.setText(prefix.upper())
        self.prefix_editor.textEdited.emit(self.prefix_editor.text())

    def init_database_values(self, root=None, compare=False):
        """Load the properties from the database and apply them to the UI.

        When compare is True, we only load values from the database.
        Loading from an adjasent bookmark can done by providing a custom 'root'.

        """
        def set_saved(k):
            v = db.value(1, k, table=u'properties')
            if not v:
                return None
            if compare:
                return v

            if not hasattr(self, k + u'_editor'):
                return None

            w = getattr(self, k + u'_editor')
            if u'shotgun_type' in k:
                return w.setCurrentText(unicode(v) if v else u'')
            return w.setText(unicode(v) if v else u'')

        def emit_text(k):
            if not hasattr(self, k + u'_editor'):
                return

            w = getattr(self, k + u'_editor')
            if u'shotgun_type' in k:
                w.currentTextChanged.emit(w.currentText())
                return
            w.textEdited.emit(w.text())

        if root is None:
            root = self.root

        db = bookmark_db.get_db(
            self.server,
            self.job,
            root
        )

        d = {}
        with db.transactions():
            try:
                for k in bookmark_db.BOOKMARK_DB[u'properties']:
                    if k.startswith('id'):
                        continue
                    d[k] = set_saved(k)
                    if compare:
                        continue
                    emit_text(k)
            except Exception as e:
                common_ui.ErrorBox(
                    u'Could not load the properties.',
                    u'There seems to be an error with the database:\n{}'.format(
                        e),
                ).open()
                log.error(u'Error loading properties from the database')
                raise

        return d

    def save_values_to_database(self, compare=False):
        """Save the current UI values to the database.

        """
        def save(k, db):
            """Performs the save to the database."""
            if not hasattr(self, k + u'_editor'):
                return None

            w = getattr(self, k + u'_editor')
            if u'shotgun_type' in k:
                v = w.currentText()
            else:
                v = w.text()

            if compare:
                return v
            db.setValue(1, k, v, table=u'properties')
            return None

        db = bookmark_db.get_db(
            self.server,
            self.job,
            self.root
        )

        d = {}
        with db.transactions():
            for k in bookmark_db.BOOKMARK_DB[u'properties']:
                if k.startswith('id'):
                    continue
                d[k] = save(k, db)
        return d

    @QtCore.Slot()
    def verify_slack_token(self):
        """Tests the validity of the entered Slack API."""
        if not self.slacktoken_editor.text():
            return

        try:
            from . import slack
        except ImportError as err:
            common_ui.ErrorBox(
                u'Could not import SlackClient',
                u'The Slack API python module was not loaded:\n{}'.format(err),
            ).open()
            log.error('Slack import error.')
            raise

        client = slack.Client(self.slacktoken_editor.text())
        client.verify_token(silent=False)

        self.slacktoken_editor.setStyleSheet(
            u'color: rgba({});'.format(common.rgb(common.ADD)))
        pretty_response = u'Slack URL: {url}\nTeam: {team}'.format(
            url=client._response['url'],
            team=client._response['team'],
        )
        common_ui.MessageBox(
            u'Token is valid.',
            pretty_response,
        ).open()

    @QtCore.Slot()
    def find_shotgun_id(self):
        self.verify_shotgun_token(silent=True)
        w = shotgun_widgets.LinkToShotgunWidget(
            self.parent().job,
            self.shotgun_type_editor.currentText(),
            self.shotgun_domain_editor.text(),
            self.shotgun_scriptname_editor.text(),
            self.shotgun_api_key_editor.text(),
            project_id=None,
        )
        w.linkRequested.connect(self.set_shotgun_id)
        w.exec_()

    @QtCore.Slot()
    def verify_shotgun_token(self, silent=False):
        """Check the validity of the Shotgun token."""
        domain = self.shotgun_domain_editor.text()
        if not domain:
            common_ui.ErrorBox(
                u'Enter a valid Shotgun domain.',
                u'Make sure the domain starts with https://'
            ).open()
            log.error(u'Domain not yet entered.')
            return
        script_name = self.shotgun_scriptname_editor.text()
        if not script_name:
            common_ui.ErrorBox(
                u'Enter a valid Shotgun API Script name.',
            ).open()
            log.error(u'Script name not yet entered.')
            return

        api_key = self.shotgun_api_key_editor.text()
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
            common_ui.MessageBox(
                u'Successfully connected to Shotgun.', _info).open()

    @QtCore.Slot(int)
    def set_shotgun_id(self, name, id):
        self.shotgun_id_editor.setText(unicode(id))
        self.shotgun_name_editor.setText(name)

    @QtCore.Slot(int)
    def load_from_previous(self, idx):
        """Slot used to load settings from a previous bookmark.

        """
        data = self.load_combobox.itemData(idx)
        if data == u'Select...':
            pass
        else:
            self.init_database_values(root=data)

        self.load_combobox.blockSignals(True)
        self.load_combobox.setCurrentText(u'Select...')
        self.load_combobox.blockSignals(False)

    def init_load_combobox(self):
        def decorate():
            self.load_combobox.setItemData(
                self.load_combobox.count() - 1, size, role=QtCore.Qt.SizeHintRole
            )

        bookmarks = settings.local_settings.bookmarks()
        b = (self.server + u'/' + self.job)
        ks = [f for f in bookmarks if b in f]

        size = QtCore.QSize(0, common.ROW_HEIGHT() * 0.7)
        self.load_combobox.addItem(u'Select...', userData=u'Select...')
        decorate()
        for k in ks:
            if k == (b + u'/' + self.root):
                continue
            self.load_combobox.addItem(k, userData=bookmarks[k]['root'])
            decorate()

    @QtCore.Slot()
    def needs_saving(self):
        """Check if the currently set values differ from the ones already set
        in the database.

        """
        def _values(data):
            data = [f for f in data.iteritems()]
            data = sorted(data, key=lambda x: x[0])
            return [unicode(f[1]) if f[1] else None for f in data]

        current = _values(self.init_database_values(compare=True))
        proposed = _values(
            self.save_values_to_database(compare=True))

        if current != proposed:
            return True
        return False

    @QtCore.Slot()
    def done(self, r):
        if r == QtWidgets.QDialog.Rejected:
            # Let's compare the DB values with the the new set values
            # If there's any difference, prompt the user to save changes

            if self.needs_saving():
                mbox = QtWidgets.QMessageBox(parent=self)
                mbox.setIcon(QtWidgets.QMessageBox.Information)
                mbox.setWindowTitle(u'Save changes?')
                mbox.setText(
                    u'Do you want to save changes?')
                mbox.setStandardButtons(
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel)
                mbox.setDefaultButton(QtWidgets.QMessageBox.Yes)

                res = mbox.exec_()
                if res == QtWidgets.QMessageBox.Yes:
                    self.save_values_to_database()
                elif res == QtWidgets.QMessageBox.Cancel:
                    return

            super(BookmarkPropertiesWidget, self).done(
                QtWidgets.QDialog.Rejected)
        elif r == QtWidgets.QDialog.Accepted:
            self.save_values_to_database()
            super(BookmarkPropertiesWidget, self).done(
                QtWidgets.QDialog.Accepted)

    def showEvent(self, event):
        self.setFocus()
        self.init_database_values()
        self.init_load_combobox()
        self.check_status_timer.start()

        app = QtWidgets.QApplication.instance()
        r = app.primaryScreen().availableGeometry()
        rect = self.frameGeometry()
        rect.moveCenter(r.center())
        self.move(rect.topLeft())

    def hideEvent(self, event):
        self.check_status_timer.stop()
