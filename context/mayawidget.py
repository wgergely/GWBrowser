# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, E0401
"""Maya wrapper for the BrowserWidget."""

import functools
from PySide2 import QtWidgets, QtGui, QtCore

import maya.cmds as cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import mixinWorkspaceControls

import maya.OpenMayaUI as OpenMayaUI
from shiboken2 import wrapInstance

import browser.common as common
from browser.context.basetoolbar import BaseToolbarWidget
from browser.context.basetoolbar import ToolbarButton
from browser.baselistwidget import BaseContextMenu
from browser.browserwidget import BrowserWidget
from browser.assetwidget import AssetWidget
from browser.fileswidget import FilesWidget
from browser.browserwidget import HeaderWidget
from browser.settings import local_settings
from browser.common import QSingleton


class MayaWidgetContextMenu(BaseContextMenu):
    """The context holding the Maya specific actions."""

    def __init__(self, index, parent=None):
        super(MayaWidgetContextMenu, self).__init__(index, parent=parent)

        if not index.isValid():
            return

        if self.parent().model().sourceModel().get_location() == common.ScenesFolder:
            self.add_scenes_menu()
        elif self.parent().model().sourceModel().get_location() == common.ExportsFolder:
            self.add_alembic_menu()

    def add_alembic_menu(self):
        menu_set = collections.OrderedDict()
        openpixmap = common.get_rsc_pixmap(
            u'files', common.TEXT, common.INLINE_ICON_SIZE)
        importpixmap = common.get_rsc_pixmap(
            u'import', common.TEXT, common.INLINE_ICON_SIZE)
        importrefpixmap = common.get_rsc_pixmap(
            u'import', common.FAVOURITE, common.INLINE_ICON_SIZE)

        path = self.index.data(QtCore.Qt.StatusTipRole)
        path = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(path)

        menu_set[u'separator'] = {}
        menu_set[u'open'] = {
            u'text': u'Open {}...'.format(file_info.fileName()),
            u'icon': openpixmap,
            u'action': functools.partial(open_alembic, file_info.filePath())
        }
        menu_set[u'separator2'] = {}
        menu_set[u'import'] = {
            u'text': u'Import  {} as reference...'.format(file_info.fileName()),
            u'icon': importrefpixmap,
            u'action': functools.partial(import_referenced_scene, file_info.filePath())
        }
        menu_set[u'importlocal'] = {
            u'text': u'Import  {}'.format(file_info.fileName()),
            u'icon': importpixmap,
            u'action': functools.partial(import_scene, file_info.filePath())
        }

        self.create_menu(menu_set)

    def add_scenes_menu(self):
        menu_set = collections.OrderedDict()
        openpixmap = common.get_rsc_pixmap(
            u'files', common.TEXT, common.INLINE_ICON_SIZE)
        importpixmap = common.get_rsc_pixmap(
            u'import', common.TEXT, common.INLINE_ICON_SIZE)
        importrefpixmap = common.get_rsc_pixmap(
            u'import', common.FAVOURITE, common.INLINE_ICON_SIZE)

        path = self.index.data(QtCore.Qt.StatusTipRole)
        path = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(path)

        menu_set[u'separator'] = {}
        menu_set[u'open'] = {
            u'text': u'Open  {}...'.format(file_info.fileName()),
            u'icon': openpixmap,
            u'action': functools.partial(open_scene, file_info.filePath())
        }
        menu_set[u'separator2'] = {}
        menu_set[u'import'] = {
            u'text': u'Import  {} as reference...'.format(file_info.fileName()),
            u'icon': importrefpixmap,
            u'action': functools.partial(import_referenced_scene, file_info.filePath())
        }
        menu_set[u'importlocal'] = {
            u'text': u'Import  {}'.format(file_info.fileName()),
            u'icon': importpixmap,
            u'action': functools.partial(import_scene, file_info.filePath())
        }

        self.create_menu(menu_set)


class MayaWidget(MayaQWidgetDockableMixin, QtWidgets.QWidget):  # pylint: disable=E1139
    """The main wrapper-widget to be used inside maya."""

    instances = {}
    __metaclass__ = QSingleton
    """Singleton metaclass."""

    # Signals for signalling show/hide status changes
    showEventTriggered = QtCore.Signal()
    hideEventTriggered = QtCore.Signal()

    def __init__(self, parent=None):
        super(MayaWidget, self).__init__(parent=parent)
        self.instances[self.objectName()] = self

        # Overriding the default name-filters
        common.NameFilters[common.ScenesFolder] = (
            u'*.ma',  # Maya ASCII
            u'*.mb',  # Maya Binary
        )

        self._workspacecontrol = None
        self.browserwidget = None

        self.setAutoFillBackground(True)
        self.setWindowTitle(u'Browser')

        self._createUI()
        self._connectSignals()

        self.browserwidget.showEvent = lambda event: None
        self.browserwidget.hideEvent = lambda event: None

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        common.set_custom_stylesheet(self)

        self.browserwidget = BrowserWidget()
        self.setFocusProxy(self.browserwidget)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        def func(*args, **kwargs):
            pass
        self.browserwidget.findChild(HeaderWidget).mouseMoveEvent = func
        self.browserwidget.findChild(HeaderWidget).setHidden(True)
        self.layout().addWidget(self.browserwidget)

    def _connectSignals(self):
        assetswidget = self.browserwidget.findChild(AssetWidget)
        fileswidget = self.browserwidget.findChild(FilesWidget)

        # Asset/project
        assetswidget.model().sourceModel().activeAssetChanged.connect(self.set_workspace)

        # Context menu
        fileswidget.customContextMenuRequested.connect(
            self.customFilesContextMenuEvent)

        fileswidget.model().sourceModel().activeFileChanged.connect(
            lambda path: open_scene(path))

    def customFilesContextMenuEvent(self, index, parent):
        """Shows the custom context menu."""
        width = parent.viewport().geometry().width()
        width = (width * 0.5) if width > 400 else width
        width = width - common.INDICATOR_WIDTH

        widget = MayaWidgetContextMenu(index, parent=parent)

        if index.isValid():
            rect = parent.visualRect(index)
            widget.move(
                parent.viewport().mapToGlobal(rect.bottomLeft()).x(),
                parent.viewport().mapToGlobal(rect.bottomLeft()).y() + 1,
            )
        else:
            cursor_pos = QtGui.QCursor().pos()
            widget.move(
                parent.mapToGlobal(parent.viewport().geometry().topLeft()).x(),
                cursor_pos.y() + 1
            )

        widget.setFixedWidth(width)
        widget.move(widget.x() + common.INDICATOR_WIDTH, widget.y())
        common.move_widget_to_available_geo(widget)
        widget.show()

    def set_workspace(self, asset):
        """Slot responsible for updating the maya worspace."""
        if not all(asset):
            return
        file_info = QtCore.QFileInfo(u'/'.join(asset))
        cmds.workspace(file_info.filePath(), openWorkspace=True)

    def floatingChanged(self, isFloating):
        """Triggered when QDockWidget.topLevelChanged() signal is triggered.
        Stub function.  Override to perform actions when this happens.
        """
        cls = self.__class__.__name__
        key = u'widget/{}/isFloating'.format(cls)
        local_settings.setValue(key, isFloating)

        wpcs = (f for f in mixinWorkspaceControls if u'MayaWidget' in f)
        if isFloating == u'0':  # why'o'why, this is a unicode value
            pass  # I can't implement this shit.

    def dockCloseEventTriggered(self):
        """riggered when QDockWidget.closeEventTriggered() signal is triggered.
        Stub function.  Override to perform actions when this happens.
        """
        cls = self.__class__.__name__
        if self.isFloating():
            x = u'widget/{}/x'.format(cls)
            y = u'widget/{}/y'.format(cls)
            local_settings.setValue(x, self.geometry().x())
            local_settings.setValue(y, self.geometry().y())

    def show(self, *args, **kwargs):
        """Initializes the Maya workspace control on show."""
        cls = self.__class__.__name__

        key = u'widget/{}/isFloating'.format(cls)
        isFloating = local_settings.value(key)

        kwargs = {
            u'dockable': True,
            u'floating': isFloating if isFloating else True,
            u'area': None,
            u'allowedArea': None,
            u'minWidth': 200,
            u'widthSizingProperty': None,
            u'heightSizingProperty': None,
            u'retain': True,
            u'closeCallback': None
        }
        super(MayaWidget, self).show(**kwargs)


class MayaToolbar(QtWidgets.QWidget):
    """A dockable tool bar for showing/hiding the browser window."""

    def __init__(self, parent=None):
        super(MayaToolbar, self).__init__(parent=parent)
        self.callbacks = {}

        self._createUI()
        self._connectSignals()
        self.setFocusProxy(self.toolbar)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setWindowTitle(u'Browser')
        # Hopefully deletes the workspaceControl
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Adds the button to the
        ptr = OpenMayaUI.MQtUtil.findControl(u'ToolBox')
        widget = wrapInstance(long(ptr), QtWidgets.QWidget)
        widget.layout().addWidget(self)
        cmds.evalDeferred(self.show_browser)

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.toolbar = BaseToolbarWidget(parent=self)
        self.layout().addWidget(self.toolbar)

    def contextMenuEvent(self, event):
        self.toolbar.contextMenuEvent(event)

    def show_browser(self):
        """Slot responsible showing the maya browser widget."""
        app = QtWidgets.QApplication.instance()
        widget = next((f for f in app.allWidgets()
                       if u'MayaWidget' in f.objectName()), None)

        if not widget:  # browser has not been initiazed
            widget = MayaWidget()
            # Connecting the show/close signals to the button to indicate if
            # the Browser is visible or not.
            button = self.findChild(ToolbarButton)
            widget.show()  # showing with the default options
            button.setState(True)

            wpcs = (f for f in mixinWorkspaceControls if u'MayaWidget' in f)
            if not wpcs:  # Widget initialized
                return
            k = next(wpcs)
            widget = mixinWorkspaceControls[k]

            # Tabbing this to the attribute editor
            cmds.evalDeferred(
                lambda *args: cmds.workspaceControl(k, e=True, tabToControl=(u'AttributeEditor', -1)))
            cmds.evalDeferred(
                lambda: widget.raise_())

            return

        wpcs = (f for f in mixinWorkspaceControls if u'MayaWidget' in f)
        if not wpcs:  # Widget initialized
            return
        widget = mixinWorkspaceControls[next(wpcs)]

        if widget.isFloating():
            widget.raise_()
        else:
            widget.show()

    def _connectSignals(self):
        button = self.toolbar.findChild(ToolbarButton)
        button.clicked.connect(self.show_browser)


def open_scene(path):
    """Opens the given scene."""
    file_info = QtCore.QFileInfo(path)
    if not file_info.exists():
        return

    result = save_scene()
    if result == QtWidgets.QMessageBox.Cancel:
        return

    cmds.file(file_info.filePath(), open=True, force=True)


def import_scene(path):
    """Imports the given scene locally."""
    file_info = QtCore.QFileInfo(path)
    if not file_info.exists():
        return

    result = save_scene()
    if result == QtWidgets.QMessageBox.Cancel:
        return

    cmds.file(
        file_info.filePath(),
        i=True,
        ns=u'Reference_{}_#'.format(file_info.baseName()),
    )


def import_referenced_scene(path):
    """Imports the given scene as a reference."""
    file_info = QtCore.QFileInfo(path)
    if not file_info.exists():
        return

    result = save_scene()
    if result == QtWidgets.QMessageBox.Cancel:
        return

    cmds.file(
        file_info.filePath(),
        reference=True,
        ns=u'Reference_{}_#'.format(file_info.baseName()),
        rfn=u'Reference_{}RN'.format(file_info.baseName()),
    )


def open_alembic(path):
    """Opens the given scene."""
    file_info = QtCore.QFileInfo(path)
    if not file_info.exists():
        return

    result = save_scene()
    if result == QtWidgets.QMessageBox.Cancel:
        return

    cmds.AbcImport(file_info.filePath(), mode=u'open')


def import_alembic(path):
    """Imports the given scene locally."""
    file_info = QtCore.QFileInfo(path)
    if not file_info.exists():
        return

    result = save_scene()
    if result == QtWidgets.QMessageBox.Cancel:
        return

    group = u'Alembic_{}'.format(file_info.baseName())
    # Creating the root group
    if not cmds.objExist(group):
        cmds.group(empty=True, name=group)
        cmds.setAttr(u'{}.useOutlinerColor'.format(group), True)
        cmds.setAttr(u'{}.outlinerColor'.format(group),
                     0.9, 0.68, 0.3, type=u'double3')

    cmds.AbcImport(
        (file_info.filePath(),),
        mode=u'import',
        filterObjects=".*Shape.*",
        reparent=group
    )


def import_referenced_alembic(path):
    """Imports the given scene as a reference."""
    file_info = QtCore.QFileInfo(path)
    if not file_info.exists():
        return

    result = save_scene()
    if result == QtWidgets.QMessageBox.Cancel:
        return

    cmds.file(
        file_info.filePath(),
        type=u'Alembic',
        reference=True,
        ns=u'Reference_{}_#'.format(file_info.baseName()),
        rfn=u'Reference_{}RN'.format(file_info.baseName()),
    )


def save_scene():
    """If the current scene needs changing prompts the user with
    a pop - up message to save the scene.
    """
    if cmds.file(q=True, modified=True):
        mbox = QtWidgets.QMessageBox()
        mbox.setText(
            u'Current scene has unsaved changes.'
        )
        mbox.setInformativeText(u'Save the scene now?')
        mbox.setStandardButtons(
            QtWidgets.QMessageBox.Save |
            QtWidgets.QMessageBox.Discard |
            QtWidgets.QMessageBox.Cancel
        )
        mbox.setDefaultButton(QtWidgets.QMessageBox.Save)
        result = mbox.exec_()

        if result == QtWidgets.QMessageBox.Cancel:
            return result
        elif result == QtWidgets.QMessageBox.Save:
            cmds.SaveScene()
            return result
        return result
