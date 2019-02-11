# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, E0401
"""Maya wrapper for the BrowserWidget."""

import sys
import functools
from functools import wraps
import collections

from PySide2 import QtWidgets, QtGui, QtCore

try:
    from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
    from maya.app.general.mayaMixin import mixinWorkspaceControls
    import maya.OpenMayaUI as OpenMayaUI
    import maya.OpenMaya as OpenMaya
    from shiboken2 import wrapInstance
except ImportError:
    sys.stderr.write('# Browser context error.\n\n')
    raise ImportError(
        ':( This widget can only be initiated from within Maya compiled with PySide2.')

import browser.common as common
from browser.context.basetoolbar import BaseToolbarWidget
from browser.context.basetoolbar import ToolbarButton

from browser.baselistwidget import BaseContextMenu
from browser.browserwidget import BrowserWidget, ListControlWidget
from browser.assetwidget import AssetWidget
from browser.fileswidget import FilesWidget
from browser.browserwidget import HeaderWidget
from browser.settings import local_settings
from browser.common import QSingleton
from browser.context.saver import SaverWidget, SaverFileInfo, Custom


def mayacommand(func):
    """Decorator responsible for importing the ``Maya commands`` module."""
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        try:
            import maya.cmds
            return func(self, maya.cmds, *args, **kwargs)
        except ImportError:
            raise ImportError('Couldn\'t import the Maya commands module')
    return func_wrapper


def contextmenu(func):
    """Decorator to create a menu set."""
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        menu_set = collections.OrderedDict()
        menu_set['__separator__'] = None
        parent = self.parent().parent().parent().parent()

        menu_set = func(self, menu_set, *args, browserwidget=parent, **kwargs)

        if not isinstance(menu_set, collections.OrderedDict):
            raise ValueError(
                'Invalid return type from context menu function, expected an OrderedDict, got {}'.format(type(menu_set)))
        self.create_menu(menu_set)
        return menu_set
    return func_wrapper


class MayaWidgetContextMenu(BaseContextMenu):
    """The context holding the Maya specific actions."""

    def __init__(self, index, parent=None):
        super(MayaWidgetContextMenu, self).__init__(index, parent=parent)

        self.add_alembic_export_menu()
        self.add_save_as_menu()
        if index.isValid():
            if self.parent().model().sourceModel().get_location() == common.ScenesFolder:
                self.add_scenes_menu()
            elif self.parent().model().sourceModel().get_location() == common.ExportsFolder:
                self.add_alembic_menu()

    @contextmenu
    def add_alembic_export_menu(self, menu_set, browserwidget=None):
        objectset_pixmap = QtGui.QPixmap(':objectSet.svg')
        exporter = AbcExportCommand()            # saver.exec_()

        key = 'sets'
        menu_set[key] = collections.OrderedDict()
        menu_set[u'{}:icon'.format(key)] = objectset_pixmap
        menu_set[u'{}:text'.format(key)] = 'Export set as alembic...'

        for k, value in exporter.get_dag_sets().iteritems():
            menu_set[key][k.strip(':')] = {
                'text': k.strip(':').upper(),
                'icon': objectset_pixmap,
                'action': functools.partial(self.parent().parent().parent().parent().init_alembic_export, k.strip(':'), value, exporter)
            }

        return menu_set

    @contextmenu
    @mayacommand
    def add_save_as_menu(self, cmds, menu_set, browserwidget=None):
        scene = QtCore.QFileInfo(cmds.file(query=True, expandName=True))

        if common.get_sequence(scene.fileName()):
            menu_set[u'increment'] = {
                u'text': u'Save as increment...',
                u'icon': QtGui.QPixmap(':mayaIcon.png'),
                u'action': lambda: browserwidget.save_scene(increment=True)
            }
        menu_set[u'new'] = {
            u'text': u'Save as new...',
            u'icon': QtGui.QPixmap(':mayaIcon.png'),
            u'action': lambda: browserwidget.save_scene(increment=False)
        }
        return menu_set

    @contextmenu
    def add_alembic_menu(self, menu_set, browserwidget=None):
        """Actions associated with ``alembic`` cache operations."""
        path = self.index.data(QtCore.Qt.StatusTipRole)
        path = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(path)

        menu_set[u'open'] = {
            u'text': u'Open alembic...',
            u'icon': QtGui.QPixmap(':importAlembic.png'),
            u'action': functools.partial(browserwidget.open_alembic, file_info.filePath())
        }
        menu_set[u'importlocal'] = {
            u'text': u'Import alembic...',
            u'icon': QtGui.QPixmap(':importAlembic.png'),
            u'action': functools.partial(browserwidget.import_scene, file_info.filePath())
        }
        menu_set[u'import'] = {
            u'text': u'Import alembic as reference...',
            u'icon': QtGui.QPixmap(':importAlembic.png'),
            u'action': functools.partial(browserwidget.import_referenced_scene, file_info.filePath())
        }
        return menu_set

    @contextmenu
    def add_scenes_menu(self, menu_set, browserwidget=None):
        path = self.index.data(QtCore.Qt.StatusTipRole)
        path = common.get_sequence_endpath(path)
        file_info = QtCore.QFileInfo(path)

        menu_set[u'open'] = {
            u'text': u'Open scene',
            u'icon': QtGui.QPixmap(':mayaIcon.png'),
            u'action': functools.partial(browserwidget.open_scene, file_info.filePath())
        }
        menu_set[u'importlocal'] = {
            u'text': u'Import scene',
            u'icon': QtGui.QPixmap(':mayaIcon.png'),
            u'action': functools.partial(browserwidget.import_scene, file_info.filePath())
        }
        menu_set[u'import'] = {
            u'text': u'Import scene as reference',
            u'icon': QtGui.QPixmap(':mayaIcon.png'),
            u'action': functools.partial(browserwidget.import_referenced_scene, file_info.filePath())
        }
        return menu_set


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
        self._callbacks = []  # Maya api callbacks

        self.setAutoFillBackground(True)
        self.setWindowTitle(u'Browser')

        self._createUI()
        self._connectSignals()
        self.add_context_callbacks()

        self.unmark_active()
        self.mark_current_as_active()

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        common.set_custom_stylesheet(self)

        widget = BrowserWidget()
        widget.findChild(HeaderWidget).setHidden(True)
        self.layout().addWidget(widget)

    def unmark_active(self, *args):
        """Callback responsible for keeping the active-file in the list updated."""
        self.findChild(FilesWidget).unmark_active_index()

    @mayacommand
    def mark_current_as_active(self, cmds, *args):
        """Callback responsible for keeping the active-file in the list updated."""

        scene = common.get_sequence_endpath(cmds.file(query=True, expandName=True))
        fileswidget = self.findChild(FilesWidget)

        for n in xrange(fileswidget.model().rowCount()):
            index = fileswidget.model().index(n, 0, parent=QtCore.QModelIndex())
            data = common.get_sequence_endpath(index.data(QtCore.Qt.StatusTipRole))

            if data == scene:
                fileswidget.selectionModel().setCurrentIndex(
                    index, QtCore.QItemSelectionModel.ClearAndSelect)
                fileswidget.scrollTo(index)
                fileswidget.activate_current_index()
                break

    def add_context_callbacks(self):
        """This method is called by the Maya plug-in when initializing."""

        callback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kAfterOpen, self.mark_current_as_active)
        self._callbacks.append(callback)

        callback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kBeforeOpen, self.unmark_active)
        self._callbacks.append(callback)

        callback = OpenMaya.MSceneMessage.addCallback(
            OpenMaya.MSceneMessage.kBeforeNew, self.unmark_active)
        self._callbacks.append(callback)

    def remove_context_callbacks(self):
        """This method is called by the Maya plug-in when unloading."""
        sys.stdout.write('\n# Browser: Removing callbacks...\n\n')
        for callback in self._callbacks:
            res = OpenMaya.MMessage.removeCallback(callback)
            sys.stdout.write('# Callback status {}\n'.format(res))

    def _connectSignals(self):
        browserwidget = self.findChild(BrowserWidget)
        assetswidget = self.findChild(AssetWidget)
        fileswidget = self.findChild(FilesWidget)

        # Asset/project
        assetswidget.model().sourceModel().activeAssetChanged.connect(self.set_workspace)

        # Context menu
        fileswidget.customContextMenuRequested.connect(
            self.customFilesContextMenuEvent)

        def open_scene(index):
            if self.findChild(FilesWidget).model().sourceModel().get_location() != common.ScenesFolder:
                return
            self.open_scene(index.data(QtCore.Qt.StatusTipRole))
        fileswidget.itemDoubleClicked.connect(open_scene)

    @mayacommand
    def init_alembic_export(self, cmds, key, value, exporter):
        # Creating the saver with no current file set will generate a new filename
        # we can use to query the exports folder
        def _init_xport(file):
            """Slot called by the saver when finished."""
            exporter.export(
                file,
                value,
                cmds.playbackOptions(query=True, animationStartTime=True),
                cmds.playbackOptions(query=True, animationEndTime=True)
            )

        saver = SaverWidget(u'abc', '{}'.format(
            common.ExportsFolder), currentfile=None)
        saver.findChild(Custom).setText(key)  # Setting the group name
        file_info = SaverFileInfo(saver).fileInfo()

        path = '{}/{}'.format(file_info.path(), file_info.fileName())
        dir_ = QtCore.QFileInfo(path).dir()

        if not dir_.exists():
            raise RuntimeError(
                'The export destination path {} does not exist.'.format(dir_.path()))

        dir_.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
        dir_.setNameFilters(('*.abc',))

        match2 = common.get_sequence(file_info.fileName())
        versions = []
        for entry in dir_.entryList():
            # Checking if the entry is a sequence
            match = common.get_sequence(entry)
            if not all((match, match2)):
                continue

            # Comparing against the new version
            if match.group(1) == match2.group(1):
                versions.append(match.group(2))

        if versions:
            version = unicode(max([int(f) for f in versions])).zfill(
                len(versions[-1]))
            path = match.expand(
                r'{}/\1{}\3.\4').format(file_info.path(), version)
            saver = SaverWidget(u'abc', common.ExportsFolder, currentfile=path)

        # Start save
        saver.fileSaveRequested.connect(_init_xport)
        saver.exec_()

        # Refresh the view
        fileswidget = self.findChild(FilesWidget)
        if fileswidget.model().sourceModel().get_location() == common.ExportsFolder:
            self.findChild(FilesWidget).refresh()

    @mayacommand
    def save_scene(self, cmds, increment=True):
        """Launches the saver widget."""
        scene = QtCore.QFileInfo(cmds.file(query=True, expandName=True))
        currentfile = scene.filePath() if scene.exists() and increment else None

        # Setting the file-extension
        saver = SaverWidget(u'ma', common.ScenesFolder,
                            currentfile=currentfile)

        saver.fileSaveRequested.connect(self.save_as)
        saver.exec_()

        self.findChild(FilesWidget).refresh()

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
            widget.move(QtGui.QCursor().pos())

        widget.setFixedWidth(width)
        widget.move(widget.x() + common.INDICATOR_WIDTH, widget.y())
        common.move_widget_to_available_geo(widget)
        widget.show()

    @mayacommand
    def set_workspace(self, cmds, asset):
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
            # u'floating': isFloating if isFloating else True,
            # u'area': None,
            u'allowedArea': None,
            # u'minWidth': 200,
            # u'widthSizingProperty': None,
            # u'heightSizingProperty': None,
            u'retain': True,
            # u'closeCallback': None
        }
        super(MayaWidget, self).show(**kwargs)

    @mayacommand
    def save_as(self, cmds, path):
        """Saves the current scene as a new scene."""
        file_info = QtCore.QFileInfo(path)
        if file_info.exists():
            mbox = QtWidgets.QMessageBox()
            mbox.setText(
                u'{} already exists.'
            )
            mbox.setInformativeText(
                u'If you select save the the existing file will be overriden. Are you sure you want to continue?')
            mbox.setStandardButtons(
                QtWidgets.QMessageBox.Save |
                QtWidgets.QMessageBox.Cancel
            )
            mbox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
            if mbox.exec_() == QtWidgets.QMessageBox.Cancel:
                return

        cmds.file(rename=path)
        path = cmds.file(force=True, save=True, type='mayaAscii')

        print '# File saved to {}'.format(path)

    @mayacommand
    def open_scene(self, cmds, path):
        """Opens the given scene."""
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            return

        result = self.is_scene_modified()
        if result == QtWidgets.QMessageBox.Cancel:
            return

        cmds.file(file_info.filePath(), open=True, force=True)

    @mayacommand
    def import_scene(self, cmds, path):
        """Imports the given scene locally."""
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            return

        result = self.is_scene_modified()
        if result == QtWidgets.QMessageBox.Cancel:
            return

        match = common.get_sequence(file_info.fileName())
        cmds.file(
            file_info.filePath(),
            i=True,
            ns=u'{}#'.format(match.group(1) if match else file_info.baseName())
        )

    @mayacommand
    def import_referenced_scene(self, cmds, path):
        """Imports the given scene as a reference."""
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            return

        result = self.is_scene_modified()
        if result == QtWidgets.QMessageBox.Cancel:
            return

        match = common.get_sequence(file_info.fileName())
        cmds.file(
            file_info.filePath(),
            reference=True,
            ns=u'{}#'.format(match.group(
                1) if match else file_info.baseName()),
            rfn=u'{}RN#'.format(match.group(
                1) if match else file_info.baseName()),
        )

    @mayacommand
    def open_alembic(self, cmds, path):
        """Opens the given scene."""
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            return

        result = self.is_scene_modified()
        if result == QtWidgets.QMessageBox.Cancel:
            return

        cmds.AbcImport(file_info.filePath(), mode=u'open')

    @mayacommand
    def import_alembic(self, cmds, path):
        """Imports the given scene locally."""
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            return

        result = self.is_scene_modified()
        if result == QtWidgets.QMessageBox.Cancel:
            return

        cmds.AbcImport(
            (file_info.filePath(),),
            mode=u'import',
            filterObjects=".*Shape.*"
        )

    @mayacommand
    def import_referenced_alembic(self, cmds, path):
        """Imports the given scene as a reference."""
        file_info = QtCore.QFileInfo(path)
        if not file_info.exists():
            return

        result = self.is_scene_modified()
        if result == QtWidgets.QMessageBox.Cancel:
            return

        match = common.get_sequence(file_info.fileName())
        cmds.file(
            file_info.filePath(),
            type=u'Alembic',
            reference=True,
            ns=u'{}#'.format(match.group(
                1) if match else file_info.baseName()),
            rfn=u'{}RN#'.format(match.group(
                1) if match else file_info.baseName()),
        )

    @mayacommand
    def is_scene_modified(self, cmds):
        """If the current scene was modified since the last save, the user will be
        prompted to save the scene.

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


class MayaToolbar(QtWidgets.QWidget):
    """A dockable tool bar for showing/hiding the browser window."""

    def __init__(self, parent=None):
        super(MayaToolbar, self).__init__(parent=parent)

        self._createUI()
        self._connectSignals()
        self.setFocusProxy(self.toolbar)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setWindowTitle(u'Browser')

        # Hopefully deletes the workspaceControl
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        # Embeds this widget to the maya toolbox
        ptr = OpenMayaUI.MQtUtil.findControl(u'ToolBox')
        widget = wrapInstance(long(ptr), QtWidgets.QWidget)
        widget.layout().addWidget(self)

    def _createUI(self):
        QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.toolbar = BaseToolbarWidget(parent=self)
        self.layout().addWidget(self.toolbar)

    def contextMenuEvent(self, event):
        self.toolbar.contextMenuEvent(event)

    @mayacommand
    def show_browser(self, cmds):
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


class AbcExportCommand(QtCore.QObject):
    """Wrapper class for getting the current eligible sets for export."""

    def __init__(self, parent=None):
        super(AbcExportCommand, self).__init__(parent=parent)

    @mayacommand
    def setFilterScript(self, cmds, name):
        """From the good folks at cgsociety - filters the in-scene sets to return
        the user-created items only.
        https://forums.cgsociety.org/t/maya-mel-python-list-object-sets-visible-in-the-dag/1586067/2

        """
        # We first test for plug-in object sets.
        try:
            apiNodeType = cmds.nodeType(name, api=True)
        except RuntimeError:
            return False

        if apiNodeType == "kPluginObjectSet":
            return True

      # We do not need to test is the object is a set, since that test
        # has already been done by the outliner
        try:
            nodeType = cmds.nodeType(name)
        except RuntimeError:
            return False

        # We do not want any rendering sets
        if nodeType == "shadingEngine":
            return False

        # if the object is not a set, return false
        if not (nodeType == "objectSet" or
                nodeType == "textureBakeSet" or
                nodeType == "vertexBakeSet" or
                nodeType == "character"):
            return False

        # We also do not want any sets with restrictions
        restrictionAttrs = ["verticesOnlySet", "edgesOnlySet",
                            "facetsOnlySet", "editPointsOnlySet", "renderableOnlySet"]
        if any(cmds.getAttr("{0}.{1}".format(name, attr)) for attr in restrictionAttrs):
            return False

        # Do not show layers
        if cmds.getAttr("{0}.isLayer".format(name)):
            return False

        # Do not show bookmarks
        annotation = cmds.getAttr("{0}.annotation".format(name))
        if annotation == "bookmarkAnimCurves":
            return False

        # Whew ... we can finally show it
        return True

    @mayacommand
    def get_dag_sets(self, cmds):
        """Querries the scene for sets with dag objects inside."""
        setData = {}
        for s in sorted([k for k in cmds.ls(sets=True) if self.setFilterScript(k)]):
            dagMembers = cmds.listConnections(u'{}.dagSetMembers'.format(s))
            # Filters
            if not dagMembers:
                continue
            setData[s] = u' '.join(
                [u'-root {}'.format(cmds.ls(dag)[-1]) for dag in dagMembers])
        return setData

    @mayacommand
    def export(self, cmds, filepath, roots, startframe, endframe, step=1.0, preroll=100.0):
        """Main Alembic exports method."""

        kwargs = {
            'jobArg': '{f} {fr} {ro} {s} {sn} {uv} {wcs} {wfs} {wfg} {ws} {wuvs} {rt} {ef} {df}'.format(
                f='-file {}'.format(filepath),
                fr='-framerange {} {}'.format(startframe, endframe),
                # frs='-framerelativesample {}'.format(1.0),
                # no='-nonormals',
                # uvo='-uvsonly',
                # pr='-preroll {}'.format(bool(preroll)),
                ro='-renderableonly',
                s='-step {}'.format(step),
                # sl='-selection {}'.format(False),
                sn='-stripnamespaces',
                uv='-uvwrite',
                wcs='-writecolorsets',
                wfs='-writefacesets',
                wfg='-wholeframegeo',
                ws='-worldspace',
                wuvs='-writeuvsets',
                # as_='-autosubd',
                # mfc='-melperframecallback {}'.format(''),
                # pfc='-pythonperframecallback {}'.format(''),
                # mpc='-melpostjobcallback {}'.format(''),
                # ppc='-pythonpostjobcallback {}'.format(''),
                # atp='-attrprefix {}'.format(''),
                # uatp='-userattrprefix {}'.format(''),
                # u='-userattr {}'.format(''),
                rt=roots,
                ef='-eulerfilter',
                df='-dataformat {}'.format('ogawa'),
            ),
            'preRollStartFrame': float(int(startframe - preroll)),
            'dontSkipUnwrittenFrames': True,
        }
        cmds.AbcExport(**kwargs)
