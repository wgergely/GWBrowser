from PySide2 import QtWidgets, QtCore, QtGui
import bookmarks.common as common
import bookmarks.common_ui as common_ui

TABLE_ON = u'<table width="100%">'
TABLE_OFF = u'</table>'
TR = \
u'<tr>\
    <td align="center" style="background-color:rgba(0,0,0,80);padding:{pad}px;">\
        <span style="color:rgba({ADD});">{shortcut}</span>\
    </td>\
    <td align="left" style="background-color:rgba(0,0,0,30);padding:{pad}px;">\
        <span style="color:rgba({TEXT});">{description}</span>\
    </td>\
</tr>'


SHORTCUTS = (
    (u'Ctrl+N', u'Open new {} instance'.format(common.PRODUCT)),
    (u'Enter', u'Activate item'),
    (u'Space', u'Preview thumbnail'),
    (u'Arrow Up/Down', u'Navigate list'),
    (u'Ctrl+R', u'Reload'),
    (u'Ctrl+F', u'Edit filter'),
    (u'Ctrl+O', u'Reveal in file manager'),
    (u'Ctrl+C', u'Copy path'),
    (u'Ctrl+Shift+C', u'Copy path (alt)'),
    (u'Ctrl+S', u'Save/remove favourite'),
    (u'Ctrl+A', u'Archive/enable'),
    (u'Ctrl+T', u'Show Notes & Todos'),
    (u'Ctrl+H', u'Hide buttons'),
    (u'Ctrl+M', u'Toggle thumbnail loading'),
    (u'Ctrl+Shift+A', u'Show/Hide archived items'),
    (u'Ctrl+Shift+F', u'Show favourites only/Show all'),
    (u'Tab', u'Edit item description'),
    (u'Shift+Tab', u'Edit item description'),
    (u'Alt+Left', u'Show previous tab'),
    (u'Alt+Right', u'Show next tab'),
    (u'Ctrl+1', u'Show bookmarks'),
    (u'Ctrl+2', u'Show assets'),
    (u'Ctrl+3', u'Show files'),
    (u'Ctrl+4', u'Show favourites'),
    (u'Ctrl+Plus', u'Increase row height'),
    (u'Ctrl+Minus', u'Decrease row height'),
    (u'Ctrl+0', u'Reset row height'),
)

SCALE_FACTORS = (u'100%', u'125%', u'150%', u'175%', u'200%')
SCALE_FACTORS = (1.0, 1.25, 1.5, 1.75, 2.0)



class ScaleWidget(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(ScaleWidget, self).__init__(parent=parent)
        self.init_data()

    def init_data(self):
        size = QtCore.QSize(1, common.ROW_HEIGHT() * 0.66)

        self.blockSignals(True)
        for n in SCALE_FACTORS:
            name = u'{}%'.format(int(n * 100))
            self.addItem(name)

            self.setItemData(
                self.count() - 1,
                n,
                role=QtCore.Qt.UserRole
            )
            self.setItemData(
                self.count() - 1,
                size,
                role=QtCore.Qt.SizeHintRole
            )
        self.blockSignals(False)


class AboutWidget(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super(AboutWidget, self).__init__(parent=parent)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setStyleSheet(
            u'background-color:rgba({bg});border: {bd}px solid rgba({bc});border-radius:{r}px;color:rgba({c});padding: {r}px {r}px {r}px {r}px;'.format(
                bg=common.rgb(common.SECONDARY_BACKGROUND),
                bd=common.ROW_SEPARATOR(),
                bc=common.rgb(common.SEPARATOR),
                r=common.MARGIN() * 0.5,
                c=common.rgb(common.TEXT_DISABLED)
            )
        )
        self.init_data()

    def init_data(self):
        import importlib
        mod = importlib.import_module(__name__.split('.')[0])
        text = u'\n'.join(mod.get_info())
        self.setText(text)

    def mouseReleaseEvent(self, event):
        QtGui.QDesktopServices.openUrl(common.ABOUT_URL)



class ShortcutsViewer(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super(ShortcutsViewer, self).__init__(parent=parent)
        self.setWordWrap(True)
        self.init_data()

    def init_data(self):
        text = TABLE_ON
        for shortcut, description in SHORTCUTS:
            text += TR.format(
                shortcut=shortcut,
                description=description,
                pad=int(common.INDICATOR_WIDTH() * 1.5),
                ADD=common.rgb(common.ADD),
                TEXT=common.rgb(common.SECONDARY_TEXT),
            )
        text += TABLE_OFF

        self.setText(text)
