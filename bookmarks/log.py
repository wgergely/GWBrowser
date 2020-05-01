# -*- coding: utf-8 -*-
"""Basic logging classes and methods.

Our custom log is stored in :const:`.stdout`. By default logging is inactive,
use :class:`.LogView` to browse the contents if the log. Logging will
automatically enabled when the widget is visible.

"""
import re
import time
import traceback
import cStringIO

from PySide2 import QtGui, QtCore, QtWidgets

import bookmarks.common as common


mutex = QtCore.QMutex()

stdout = cStringIO.StringIO()
"""File-like object to store our temporary log."""

_viewer_widget = None

HEADER = (0b000000001, u'\033[95m')
OKBLUE = (0b000000010, u'\033[94m')
OKGREEN = (0b000000100, u'\033[92m')
WARNING = (0b000001000, u'\033[93m')
FAIL = (0b000010000, u'\033[91m')
FAIL_SUB = (0b000100000, u'\033[91m')
ENDC = (0b001000000, u'\033[0m')
BOLD = (0b010000000, u'\033[1m')
UNDERLINE = (0b100000000, u'\033[4m')

LOGGING_ON = False
LOG_SUCCESS = True
LOG_DEBUG = False
LOG_ERROR = True


def _log(message):
    mutex.lock()
    print >> stdout, message
    print message
    mutex.unlock()


def success(message):
    """Logs a message when an action succeeds.

    """
    if not LOGGING_ON:
        return
    if not LOG_SUCCESS:
        return

    message = u'{color}{ts} [Ok]:  {default}{message}'.format(
        ts=time.strftime(u'%H:%M:%S'),
        color=OKGREEN[1],
        default=ENDC[1],
        message=message
    )
    _log(message)


def debug(message, cls=None):
    """Log a debug message to help analyze program flow.

    """
    if not LOGGING_ON:
        return
    if not LOG_DEBUG:
        return

    message = u'{color}{ts} [Debug]:{default}    {cls}{message}'.format(
        ts=time.strftime(u'%H:%M:%S'),
        color=OKBLUE[1],
        default=ENDC[1],
        message=message,
        cls=cls.__class__.__name__ + u'.' if cls else u''
    )
    _log(message)


def error(message):
    """Log an error.

    If available, a traceback will automatically be included in the output.

    """
    if not LOGGING_ON:
        return
    if not LOG_ERROR:
        return

    tb = traceback.format_exc()
    if tb:
        tb = u'\n\033[91m'.join(tb.strip(u'\n').split(u'\n'))

    message = u'{fail}{underline}{ts} [Error]:{default}{default}    {message}\n{fail}{traceback}\n'.format(
        ts=time.strftime(u'%H:%M:%S'),
        fail=FAIL[1],
        underline=UNDERLINE[1],
        default=ENDC[1],
        message=message,
        traceback=tb
    )
    _log(message)


@QtCore.Slot()
def reset(self):
    global stdout
    stdout = cStringIO.StringIO()


def _r(v): return v[1].replace(u'[', u'\\[')


class LogViewHighlighter(QtGui.QSyntaxHighlighter):
    """Syntax hightlighter used by the LogView.
    Applies the console color output syntax.

    """
    _f = re.IGNORECASE | re.UNICODE
    HIGHLIGHT_RULES = {
        OKBLUE[0]: re.compile(u'{}(.+?)(?:{})(.+)'.format(_r(OKBLUE), _r(ENDC)), flags=_f),
        OKGREEN[0]: re.compile(u'{}(.+?)(?:{})(.+)'.format(_r(OKGREEN), _r(ENDC)), flags=_f),
        FAIL[0]: re.compile(u'{}{}(.+?)(?:{})(.+)'.format(_r(FAIL), _r(UNDERLINE), _r(ENDC)), flags=_f),
        FAIL_SUB[0]: re.compile(u'{}(.*)'.format(_r(FAIL)), flags=_f),
    }

    def highlightBlock(self, text):
        font = QtGui.QFont()
        font.setStyleHint(QtGui.QFont.System)

        char_format = QtGui.QTextCharFormat()
        char_format.setFont(font)
        char_format.setForeground(QtGui.QColor(0, 0, 0, 0))

        block_format = QtGui.QTextBlockFormat()
        block_format.setLineHeight(
            150, QtGui.QTextBlockFormat.ProportionalHeight)
        self.setFormat(0, len(text), char_format)

        _font = char_format.font()
        _foreground = char_format.foreground()
        _weight = char_format.fontWeight()
        _psize = char_format.font().pixelSize()

        flag = 0

        position = self.currentBlock().position()
        cursor = QtGui.QTextCursor(self.currentBlock())
        cursor.mergeBlockFormat(block_format)
        cursor = QtGui.QTextCursor(self.document())

        for k in self.HIGHLIGHT_RULES:
            if k == OKGREEN[0]:
                it = self.HIGHLIGHT_RULES[k].finditer(text)
                for match in it:
                    flag = flag | k
                    font.setPixelSize(common.MEDIUM_FONT_SIZE())
                    char_format.setFont(font)

                    char_format.setForeground(QtGui.QColor(80, 230, 80, 255))

                    self.setFormat(match.start(1), len(
                        match.group(1)), char_format)
                    cursor = self.document().find(match.group(1), position)
                    cursor.mergeCharFormat(char_format)

                    char_format.setForeground(QtGui.QColor(157, 165, 180, 255))

                    self.setFormat(match.start(2), len(
                        match.group(2)), char_format)
                    cursor = self.document().find(match.group(2), position)
                    cursor.mergeCharFormat(char_format)

            if k == OKBLUE[0]:
                it = self.HIGHLIGHT_RULES[k].finditer(text)
                for match in it:
                    flag = flag | k
                    font.setPixelSize(common.MEDIUM_FONT_SIZE())
                    char_format.setFont(font)
                    char_format.setForeground(QtGui.QColor(85, 85, 255, 255))

                    self.setFormat(match.start(1), len(
                        match.group(1)), char_format)
                    cursor = self.document().find(match.group(1), position)
                    cursor.mergeCharFormat(char_format)

                    char_format.setForeground(QtGui.QColor(157, 165, 180, 255))

                    self.setFormat(match.start(2), len(
                        match.group(2)), char_format)
                    cursor = self.document().find(match.group(2), position)
                    cursor.mergeCharFormat(char_format)

            if k == FAIL[0]:
                match = self.HIGHLIGHT_RULES[k].match(text)
                if match:
                    flag = flag | k
                    font.setPixelSize(common.MEDIUM_FONT_SIZE())
                    char_format.setFont(font)
                    char_format.setForeground(QtGui.QColor(230, 80, 80, 255))
                    char_format.setFontUnderline(True)

                    self.setFormat(match.start(1), len(
                        match.group(1)), char_format)
                    cursor = self.document().find(match.group(1), position)
                    cursor.mergeCharFormat(char_format)

                    char_format.setForeground(QtGui.QColor(157, 165, 180, 255))

                    self.setFormat(match.start(2), len(
                        match.group(2)), char_format)
                    cursor = self.document().find(match.group(2), position)
                    cursor.mergeCharFormat(char_format)

            if k == FAIL_SUB[0]:
                # continue
                it = self.HIGHLIGHT_RULES[k].finditer(text)
                for match in it:
                    if flag & FAIL[0]:
                        continue
                    char_format.setFontUnderline(False)
                    font.setPixelSize(common.MEDIUM_FONT_SIZE())
                    char_format.setFont(font)
                    char_format.setForeground(QtGui.QColor(230, 80, 80, 255))

                    self.setFormat(match.start(1), len(
                        match.group(1)), char_format)
                    cursor = self.document().find(match.group(1), position)
                    cursor.mergeCharFormat(char_format)

            char_format.setFont(_font)
            char_format.setForeground(_foreground)
            char_format.setFontWeight(_weight)


class LogView(QtWidgets.QTextBrowser):

    format_regex = u'({h})|({b})|({g})|({w})|({f})|({e})|({o})|({u})'
    format_regex = format_regex.format(
        h=HEADER[1],
        b=OKBLUE[1],
        g=OKGREEN[1],
        w=WARNING[1],
        f=FAIL[1],
        e=ENDC[1],
        o=BOLD[1],
        u=UNDERLINE[1],
    )
    format_regex = re.compile(format_regex.replace(u'[', '\\['))

    def __init__(self, parent=None):
        super(LogView, self).__init__(parent=parent)

        if parent is None:
            common.set_custom_stylesheet(self)

        self.document().setDocumentMargin(common.MARGIN())
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

        self.setUndoRedoEnabled(False)
        self._cached = u''
        self.highlighter = LogViewHighlighter(self.document())

        self.timer = QtCore.QTimer(parent=self)
        self.timer.setSingleShot(False)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.load_log)

    def load_log(self):
        app = QtWidgets.QApplication.instance()
        if app.mouseButtons() != QtCore.Qt.NoButton:
            return

        self.document().blockSignals(True)
        v = stdout.getvalue()
        if self._cached == v:
            return

        self._cached = v
        self.setText(v[-99999:])  # Limit the number of characters
        self.highlighter.rehighlight()
        v = self.format_regex.sub(u'', self.document().toHtml())
        self.setHtml(v)
        self.document().blockSignals(False)

        m = self.verticalScrollBar().maximum()
        self.verticalScrollBar().setValue(m)

    def sizeHint(self):
        return QtCore.QSize(common.WIDTH(), common.HEIGHT())


class LogWidget(QtWidgets.QWidget):
    """The Widget used to view and control logging.

    """

    def __init__(self, parent=None):
        global _viewer_widget
        _viewer_widget = self

        super(LogWidget, self).__init__(parent=parent)

        if not self.parent():
            common.set_custom_stylesheet(self)

        self.logview = None
        self.log_debug = None
        self.reset_button = None
        self.success_button = None

        self._create_UI()
        self._connect_signals()

    def _connect_signals(self):
        self.reset_button.clicked.connect(reset)

    def _create_UI(self):
        import bookmarks.common_ui as common_ui

        QtWidgets.QVBoxLayout(self)
        o = common.MARGIN() * 0.5
        self.layout().setContentsMargins(o, o, o, o)
        self.layout().setSpacing(o)

        row = common_ui.add_row(None, parent=self)
        label = common_ui.PaintedLabel(
            u'Console', size=common.LARGE_FONT_SIZE(), parent=self)

        self.reset_button = common_ui.PaintedButton(u'Clear log', parent=self)
        self.enable_debug = QtWidgets.QCheckBox(
            'Log debug messages', parent=self)
        self.enable_debug.toggled.connect(self.toggle_debug)

        row.layout().addWidget(label)
        row.layout().addStretch(1)
        row.layout().addWidget(self.enable_debug)
        row.layout().addWidget(self.reset_button)

        self.logview = LogView(parent=self)
        self.layout().addWidget(self.logview, 1)

    def toggle_debug(self, args):
        v = self.enable_debug.isChecked()
        global LOG_DEBUG
        LOG_DEBUG = v

    def showEvent(self, event):
        global LOGGING_ON
        LOGGING_ON = True
        self.logview.timer.start()

    def hideEvent(self, event):
        global LOGGING_ON
        LOGGING_ON = False
        self.logview.timer.stop()
