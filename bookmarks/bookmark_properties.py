# -*- coding: utf-8 -*-
"""Setings window for setting a bookmark's properties (width, height, frame
rate, etc...).

"""
import re

from PySide2 import QtCore, QtGui, QtWidgets

import bookmarks.common_ui as common_ui
import bookmarks.common as common
import bookmarks.images as images
import bookmarks.settings as settings
import bookmarks.bookmark_db as bookmark_db


class RectanglesWidget(QtWidgets.QLabel):
    """Previews the project format."""

    def __init__(self, parent=None):
        super(RectanglesWidget, self).__init__(parent=parent)
        self._width = 0.0
        self._height = 0.0
        self._fps = 0.0
        self._prefix = u''
        self._start = 0.0
        self._duration = 0.0
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setMinimumHeight(200)
        self.setMinimumWidth(100)

    @QtCore.Slot()
    def set_attr(self, k, v, type=float):
        v = type(v) if v else None
        if not v:
            return
        setattr(self, k, v)
        self.repaint()

    def paintEvent(self, event):
        """Custom paint event"""
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        w = self._width + 0.01
        h = self._height + 0.01

        factor = float(min((self.width(), self.height())) -
                       common.MARGIN) / max(float(w), float(h))
        w *= factor
        h *= factor

        painter.setBrush(common.SEPARATOR)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setOpacity(0.3)
        painter.drawRect(self.rect())
        painter.setOpacity(1.0)

        rect = QtCore.QRect(0, 0, w, h)
        rect.moveCenter(self.rect().center())

        # Outline
        painter.setOpacity(0.2)
        pen = QtGui.QPen(common.ADD)
        pen.setWidthF(2.0)
        pen.setStyle(QtCore.Qt.SolidLine)
        pen.setJoinStyle(QtCore.Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRect(rect)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(common.ADD)
        painter.drawRect(rect)
        painter.setOpacity(1.0)

        painter.setPen(common.TEXT)
        painter.setFont(common.font_db.secondary_font())
        _rect = self.rect()
        _rect.setLeft(rect.left() + 8)

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


class ScrollArea(QtWidgets.QScrollArea):

    def __init__(self, index, server=None, job=None, root=None, parent=None):
        super(ScrollArea, self).__init__(parent=parent)
        self.index = index
        self.server = server
        self.job = job
        self.root = root

        self.load_last_button = None
        self.save_button = None

        self.framerate_editor = None
        self.width_editor = None
        self.height_editor = None
        self.prefix_editor = None
        self.suggest_prefix_button = None
        self.startframe_editor = None
        self.duration_editor = None
        self.rectangles_widget = None
        self.identifier_editor = None
        self.slackurl_editor = None
        self.slacktoken_editor = None

        self.setWidgetResizable(True)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self._create_UI()
        self._connect_signals()

        self.init_database_values()
        # self.init_last_used_values()

    def _create_UI(self):
        o = common.INDICATOR_WIDTH
        self.setMinimumWidth(360)
        height = common.ROW_BUTTONS_HEIGHT * 0.8

        widget = QtWidgets.QWidget(parent=self)
        QtWidgets.QVBoxLayout(widget)
        widget.layout().setAlignment(QtCore.Qt.AlignCenter)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().setSpacing(o * 2)
        self.setWidget(widget)

        # Main group
        grpA = common_ui.get_group(parent=widget)

        # GROUP
        grp = common_ui.get_group(parent=grpA)

        numvalidator = QtGui.QRegExpValidator(parent=self)
        numvalidator.setRegExp(QtCore.QRegExp(ur'[0-9]+[\.]?[0-9]*'))
        textvalidator = QtGui.QRegExpValidator(parent=self)
        textvalidator.setRegExp(QtCore.QRegExp(ur'[a-zA-Z0-9]+'))

        #   ROW1
        self.rectangles_widget = RectanglesWidget(parent=self)
        grp.layout().addWidget(self.rectangles_widget, 1)

        #   ROW
        row = common_ui.add_row(u'Resolution', parent=grp, height=height)
        self.width_editor = common_ui.NameBase(parent=self, transparent=True)
        self.width_editor.setPlaceholderText(u'Width...')
        self.width_editor.setValidator(numvalidator)
        row.layout().addWidget(self.width_editor, 0)
        self.height_editor = common_ui.NameBase(parent=self, transparent=True)
        self.height_editor.setPlaceholderText(u'Height...')
        self.height_editor.setValidator(numvalidator)
        row.layout().addWidget(self.height_editor, 0)

        #   ROW
        row = common_ui.add_row(u'Frame rate', parent=grp, height=height)
        self.framerate_editor = common_ui.NameBase(
            parent=self, transparent=True)
        self.framerate_editor.setPlaceholderText(u'Frame rate...')
        self.framerate_editor.setValidator(numvalidator)
        row.layout().addWidget(self.framerate_editor, 0)

        # ********************************************
        grp = common_ui.get_group(parent=grpA)
        row = common_ui.add_row(u'Bookmark Prefix', parent=grp, height=height)
        self.prefix_editor = common_ui.NameBase(parent=self, transparent=True)
        self.prefix_editor.setPlaceholderText(u'Prefix (eg. \'MYJOB\')...')
        self.prefix_editor.setValidator(textvalidator)

        self.suggest_prefix_button = common_ui.PaintedButton(u'Suggest')
        self.suggest_prefix_button.setFixedHeight(height * 0.7)
        row.layout().addWidget(self.prefix_editor, 0)
        row.layout().addWidget(self.suggest_prefix_button, 0)

        # ********************************************
        grp = common_ui.get_group(parent=grpA)

        row = common_ui.add_row(u'Start Frame', parent=grp, height=height)
        self.startframe_editor = common_ui.NameBase(
            parent=self, transparent=True)
        self.startframe_editor.setPlaceholderText(u'Start Frame...')
        self.startframe_editor.setValidator(numvalidator)
        row.layout().addWidget(self.startframe_editor, 0)

        row = common_ui.add_row(u'Duration', parent=grp, height=height)
        self.duration_editor = common_ui.NameBase(
            parent=self, transparent=True)
        self.duration_editor.setPlaceholderText(u'Duration...')
        self.duration_editor.setValidator(numvalidator)
        row.layout().addWidget(self.duration_editor, 0)
        # ********************************************
        grp = common_ui.get_group(parent=widget)
        row = common_ui.add_row(u'Asset Identifier', parent=grp)
        self.identifier_editor = common_ui.NameBase(
            transparent=True, parent=row)
        self.identifier_editor.setPlaceholderText(
            u'Asset identifier, eg. \'workspace.mel\'')
        row.layout().addWidget(self.identifier_editor, 0)

        text = u'Only folders containing this file will be treated as assets.<br>\
Using the default Maya Workspace the identifier normally is \
<span style="text-decoration: underline;">workspace.mel</span>, but \
any other file can be used as long it is present in the root of \
the asset.<br>If not set, all folders inside the Bookmark \
will be read as assets.'.format(common.PRODUCT)
        common_ui.add_description(text, label='Hint', parent=grp)
        # ********************************************
        grpA = common_ui.get_group(parent=widget)

        # Slack API token
        label = common_ui.PaintedLabel(
            u'Slack Settings', size=common.MEDIUM_FONT_SIZE + 1)
        grpA.layout().addWidget(label, 0)
        grpA.layout().addSpacing(o * 2)

        grp = common_ui.get_group(parent=grpA)

        row = common_ui.add_row(u'Slack Workspace URL',
                                parent=grp, height=height)

        label = QtWidgets.QLabel(parent=self)
        pixmap = images.ImageCache.get_rsc_pixmap(u'slack', common.TEXT, height)
        label.setPixmap(pixmap)
        row.layout().addWidget(label)

        self.slackurl_editor = common_ui.NameBase(
            parent=self, transparent=True)
        self.slackurl_editor.setPlaceholderText(u'http://mystudio.slack.com')

        button = common_ui.PaintedButton(u'Visit')
        button.setFixedHeight(height * 0.7)
        button.clicked.connect(
            lambda: QtGui.QDesktopServices.openUrl(self.slackurl_editor.text()))

        row.layout().addWidget(self.slackurl_editor, 0)
        row.layout().addWidget(button, 0)

        row = common_ui.add_row(u'Slack API Token', parent=grp, height=height)
        self.slacktoken_editor = common_ui.NameBase(
            parent=self, transparent=True)
        self.slacktoken_editor.setPlaceholderText(
            u'xoxb-01234567890-0123456...')
        button = common_ui.PaintedButton(u'Test Token')
        button.setFixedHeight(height * 0.7)
        button.clicked.connect(self.test_slack_token)
        row.layout().addWidget(self.slacktoken_editor, 0)
        row.layout().addWidget(button)
        text = u'If you have a Slack Bot set up, {} can send messages to team-members.<br>\
Paste the o-auth token, usually starting with "xoxb-0123...", above.<br><br>\
Make sure the bot has permissions to "users.list" and to send messages.'.format(common.PRODUCT)
        common_ui.add_description(text, label=u'Slack API Hint', parent=grp)
        # ********************************************
        self.widget().layout().addStretch(1)

    def _connect_signals(self):
        self.framerate_editor.textEdited.connect(
            lambda v: self.feedback(v, self.framerate_editor))
        self.width_editor.textEdited.connect(
            lambda v: self.feedback(v, self.width_editor))
        self.height_editor.textEdited.connect(
            lambda v: self.feedback(v, self.height_editor))
        self.prefix_editor.textEdited.connect(
            lambda v: self.feedback(v, self.prefix_editor, type=unicode))
        self.startframe_editor.textEdited.connect(
            lambda v: self.feedback(v, self.startframe_editor))
        self.duration_editor.textEdited.connect(
            lambda v: self.feedback(v, self.duration_editor))
        self.identifier_editor.textEdited.connect(
            lambda v: self.feedback(v, self.identifier_editor, type=unicode))
        self.slackurl_editor.textEdited.connect(
            lambda v: self.feedback(v, self.slackurl_editor, type=unicode))
        self.slacktoken_editor.textEdited.connect(
            lambda v: self.feedback(v, self.slacktoken_editor, type=unicode))

        self.width_editor.textEdited.connect(
            lambda v: self.rectangles_widget.set_attr(u'_width', v))
        self.height_editor.textEdited.connect(
            lambda v: self.rectangles_widget.set_attr(u'_height', v))
        self.framerate_editor.textEdited.connect(
            lambda v: self.rectangles_widget.set_attr(u'_fps', v))
        self.prefix_editor.textEdited.connect(
            lambda v: self.rectangles_widget.set_attr(u'_prefix', v, type=unicode))
        self.startframe_editor.textEdited.connect(
            lambda v: self.rectangles_widget.set_attr(u'_start', v))
        self.duration_editor.textEdited.connect(
            lambda v: self.rectangles_widget.set_attr(u'_duration', v))

        def connect_save(k):
            getattr(self, k).textEdited.connect(
                lambda v: settings.local_settings.setValue(self.preference_key(k), v))

        connect_save(u'framerate_editor')
        connect_save(u'width_editor')
        connect_save(u'height_editor')
        connect_save(u'prefix_editor')
        connect_save(u'startframe_editor')
        connect_save(u'duration_editor')
        connect_save(u'identifier_editor')
        connect_save(u'slackurl_editor')
        connect_save(u'slacktoken_editor')

        self.suggest_prefix_button.clicked.connect(self.suggest_prefix)

    @QtCore.Slot()
    def suggest_prefix(self):
        if self.index.isValid():
            _, job, _ = self.index.data(common.ParentPathRole)
        else:
            job = self.job

        substrings = re.sub(ur'[\_\-\s]+', u';', job).split(u';')
        prefix = ''
        for s in substrings:
            prefix += s[0]

        self.prefix_editor.setText(prefix.upper())
        self.prefix_editor.textEdited.emit(self.prefix_editor.text())

    def preference_key(self, name):
        return u'preferences/{}'.format(name)

    def init_last_used_values(self):
        def set_saved(k):
            v = settings.local_settings.value(self.preference_key(k))
            getattr(self, k).setText(unicode(v) if v else u'')

        def emit_text(k):
            getattr(self, k).textEdited.emit(getattr(self, k).text())

        controls = (
            u'framerate_editor',
            u'width_editor',
            u'height_editor',
            u'prefix_editor',
            u'startframe_editor',
            u'duration_editor',
            u'identifier_editor',
            u'slackurl_editor',
            u'slacktoken_editor'
        )

        for control in controls:
            set_saved(control)
            emit_text(control)

    def init_database_values(self, compare=False):
        def set_saved(k):
            v = db.value(0, k.replace(u'_editor', u''), table=u'properties')
            if compare:
                return v
            getattr(self, k).setText(unicode(v) if v else u'')

        def emit_text(k):
            getattr(self, k).textEdited.emit(getattr(self, k).text())

        controls = (
            u'framerate_editor',
            u'width_editor',
            u'height_editor',
            u'prefix_editor',
            u'startframe_editor',
            u'duration_editor',
            u'identifier_editor',
            u'slackurl_editor',
            u'slacktoken_editor'
        )

        try:
            db = bookmark_db.get_db(
                self.index,
                server=self.server,
                job=self.job,
                root=self.root)
        except:
            common_ui.ErrorBox(
                u'Could not save the properties.',
                u'Could not open the database.',
                parent=self
            ).exec_()

        d = {}
        with db.transactions():
            try:
                for control in controls:
                    d[control] = set_saved(control)
                    if compare:
                        continue
                    emit_text(control)
            except Exception as e:
                common_ui.ErrorBox(
                    u'Could not save the properties.',
                    u'There seems to be an error with the database:\n{}'.format(
                        e),
                    parent=self
                ).exec_()
                common.Log.error(u'Error saving properties to the database')
                return
        return d

    def save_values_to_database(self, compare=False):
        def save(k):
            v = getattr(self, k).text()
            if compare:
                return v
            db.setValue(
                0,
                k.replace(u'_editor', u''),
                v,
                table=u'properties'
            )

        controls = (
            u'framerate_editor',
            u'width_editor',
            u'height_editor',
            u'prefix_editor',
            u'startframe_editor',
            u'duration_editor',
            u'identifier_editor',
            u'slackurl_editor',
            u'slacktoken_editor'
        )
        db = bookmark_db.get_db(
            self.index,
            server=self.server,
            job=self.job,
            root=self.root
        )

        d = {}
        with db.transactions():
            try:
                for control in controls:
                    d[control] = save(control)
                return d
            except Exception as e:
                common_ui.ErrorBox(
                    u'Could not save the properties.',
                    u'There seems to be an error with the database:\n{}'.format(
                        e),
                    parent=self
                ).exec_()
                common.Log.error(u'Error saving properties to the database')
                return

    def test_slack_token(self):
        if not self.slacktoken_editor.text():
            return

        try:
            import bookmarks.slacker as slacker
        except ImportError as err:
            common_ui.ErrorBox(
                u'Could not import SlackClient',
                u'The Slack API python module was not loaded:\n{}'.format(err),
                parent=self
            ).exec_()
            common.Log.error('Slack import error.')
            return

        try:
            client = slacker.Slacker(self.slacktoken_editor.text())
        except Exception as err:
            self.slacktoken_editor.setStyleSheet(
                u'color: rgba({});'.format(common.rgb(common.REMOVE)))
            common_ui.ErrorBox(
                u'An error occured validating the token.',
                unicode(err),
                parent=self
            ).exec_()
            return

        if not client.isValid():
            common_ui.ErrorBox(
                u'The token is invalid.',
                u'Check again if the token is active and has the necessary permissions.',
                parent=self
            ).exec_()
            return

        self.slacktoken_editor.setStyleSheet(
            u'color: rgba({});'.format(common.rgb(common.ADD)))
        common_ui.OkBox(
            u'Token is valid.',
            u'',
            parent=self
        ).exec_()

    @QtCore.Slot(unicode)
    def feedback(self, v, w, type=float):
        valid = type(v) if v else False
        if valid:
            w.set_transparent(color=common.rgb(common.ADD))
        else:
            w.set_transparent(color=common.rgb(common.TEXT_DISABLED))


class BookmarkPropertiesWidget(QtWidgets.QDialog):

    def __init__(self, index, server=None, job=None, root=None, parent=None):
        super(BookmarkPropertiesWidget, self).__init__(parent=parent)
        self.scrollarea = None
        self.index = index
        self.server = server
        self.job = job
        self.root = root

        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(QtCore.Qt.Widget)

        self._create_UI()

    def _create_UI(self):
        common.set_custom_stylesheet(self)
        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(0)

        height = common.ROW_BUTTONS_HEIGHT * 0.8
        # ********************************************
        row = common_ui.add_row(None, padding=None, parent=self)
        label = common_ui.PaintedLabel(
            u'Bookmark Properties', size=common.LARGE_FONT_SIZE)
        self.load_last_button = common_ui.PaintedButton(u'Load Used')
        self.load_last_button.setFixedHeight(height * 0.7)

        self.save_button = common_ui.ClickableIconButton(
            u'check',
            (common.ADD, common.ADD),
            height
        )
        row.layout().addWidget(label, 1)
        row.layout().addStretch(1)
        row.layout().addWidget(self.save_button, 0)

        row = common_ui.add_row(None, padding=None, parent=self)
        row.layout().addWidget(self.load_last_button, 0)
        row.layout().addStretch(1)

        self.scrollarea = ScrollArea(
            self.index,
            server=self.server,
            job=self.job,
            root=self.root,
            parent=self
        )
        self.layout().addWidget(self.scrollarea)
        self.save_button.clicked.connect(
            lambda: self.done(QtWidgets.QDialog.Accepted))
        self.load_last_button.clicked.connect(
            self.scrollarea.init_last_used_values)

    @QtCore.Slot()
    def done(self, r):
        if r == QtWidgets.QDialog.Rejected:
            # Let's compare the DB values with the the new set values
            # If there's any difference, prompt the user to save changes
            current = self.scrollarea.init_database_values(compare=True)
            current = [unicode(f) for f in current.itervalues()]
            proposed = self.scrollarea.save_values_to_database(compare=True)
            proposed = [unicode(f) for f in proposed.itervalues()]

            if not current == proposed:
                mbox = QtWidgets.QMessageBox(parent=self)
                mbox.setIcon(QtWidgets.QMessageBox.Information)
                mbox.setWindowTitle(u'Save changes?')
                mbox.setText(
                    u'Do you want to save the Bookmark Property changes?')
                mbox.setStandardButtons(
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel)
                mbox.setDefaultButton(QtWidgets.QMessageBox.Yes)

                res = mbox.exec_()
                if res == QtWidgets.QMessageBox.Yes:
                    self.scrollarea.save_values_to_database()
                elif res == QtWidgets.QMessageBox.Cancel:
                    return

            super(BookmarkPropertiesWidget, self).done(
                QtWidgets.QDialog.Rejected)
        elif r == QtWidgets.QDialog.Accepted:
            self.scrollarea.save_values_to_database()
            super(BookmarkPropertiesWidget, self).done(
                QtWidgets.QDialog.Accepted)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(common.BACKGROUND)
        pen = QtGui.QPen(common.SEPARATOR)
        pen.setWidthF(1.0)
        painter.setPen(pen)

        o = common.MARGIN * 0.5
        painter.setOpacity(0.95)
        painter.drawRoundedRect(self.rect().marginsRemoved(
            QtCore.QMargins(o, o, o, o)), 3, 3)
        painter.end()

    def showEvent(self, event):
        self.setFocus()


if __name__ == '__main__':
    common.DEBUG_ON = True
    app = QtWidgets.QApplication([])
    w = BookmarkPropertiesWidget(
        QtCore.QModelIndex(),
        server='C:/temp',
        job=u'EXAMPLE_JOB_A',
        root=u'ASSETS'
    )
    w.show()
    app.exec_()
