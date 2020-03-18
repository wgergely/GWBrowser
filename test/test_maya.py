#!mayapy
# -*- coding: utf-8 -*-
"""Make sure the $MAYA_ROOT/bin directory is in the path before running the test."""

import unittest


class TestMaya(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Modifiying the environment to add Bookmark's dependencies.
        This is a must, as otherwise the dependent DLLs would fail to load.

        """
        import os
        import sys

        p = os.path.dirname(__file__) + os.path.sep + '..' + os.path.sep
        p = os.path.normpath(p)
        sys.path.insert(0, p)

        k = 'BOOKMARKS_ROOT'
        if k not in os.environ:
            raise EnvironmentError(
                'Is Bookmarks installed? Could not find BOOKMARKS_ROOT environment variable')

        shared = os.environ[k] + os.path.sep + 'shared'
        sys.path.insert(1, shared)

        paths = os.environ['PATH'].split(';')
        _bin = os.environ[k] + os.path.sep + 'bin'
        paths.insert(1, _bin)
        os.environ['PATH'] = ';'.join(paths)

        try:
            from PySide2 import QtWidgets
            import maya.standalone as maya_standalone
            import maya.mel as mel
            import maya.cmds as cmds
        except ImportError as e:
            raise

        try:
            from bookmarks.maya.widget import MayaBrowserButton
            import bookmarks.common as common
            import bookmarks.standalone as standalone
            import bookmarks.maya as maya
        except ImportError as e:
            raise

        app = standalone.StandaloneApp([])
        maya_standalone.initialize(name='python')
        mel.eval('')

        # Let's initialize the plugin dependencies
        cmds.loadPlugin("AbcExport.mll", quiet=True)
        cmds.loadPlugin("AbcImport.mll", quiet=True)

    @classmethod
    def tearDownClass(cls):
        try:
            from PySide2 import QtWidgets
            import maya.standalone as maya_standalone
            import maya.mel as mel
            import maya.cmds as cmds
        except ImportError as e:
            raise

        try:
            from bookmarks.maya.widget import MayaBrowserButton
            import bookmarks.common as common
            import bookmarks.standalone as standalone
            import bookmarks.maya as maya
        except ImportError as e:
            raise

        cmds.unloadPlugin("AbcExport.mll")
        cmds.unloadPlugin("AbcImport.mll")
        maya_standalone.uninitialize()
        QtWidgets.QApplication.instance().quit()

    def setUp(self):
        import maya.cmds as cmds

        meshes = []
        for n in xrange(10):
            s = cmds.polyCube(name=u'testMesh#')
            meshes.append(s[0])
        cmds.sets(meshes, name=u'testMesh_geo_set')
        cmds.sets([], name=u'emptyTestMesh_geo_set')

    def tearDown(self):
        from maya import cmds as cmds
        cmds.file(newFile=True, force=True)

    def test_MayaBrowserButton(self):
        try:
            from bookmarks.maya.widget import MayaBrowserButton
            import bookmarks.common as common
            import bookmarks.standalone as standalone
            import bookmarks.maya as maya
        except ImportError as e:
            raise

        w = MayaBrowserButton()
        w.show()

        try:
            from PySide2 import QtCore, QtGui
        except ImportError as e:
            raise

        e = QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Mouse, w.geometry().center())
        w.contextMenuEvent(e)
        w.clicked.emit()

    def test_widget(self):
        try:
            import os
            from bookmarks.maya.widget import MayaBrowserButton
            import bookmarks.common as common
            import bookmarks.standalone as standalone
            import bookmarks.maya as maya
            import maya.cmds as cmds
        except ImportError as e:
            raise

        maya.widget.show()

        r = maya.widget.__instance__.save_scene()
        r = self.assertIsInstance(r, unicode)

        r = maya.widget.__instance__.save_scene(increment=True)
        r = self.assertIsInstance(r, unicode)
        new_scene = maya.widget.__instance__.save_scene(increment=True, modal=False)
        self.assertIsInstance(new_scene, unicode)
        self.assertEqual(os.path.isfile(new_scene), True)

        r = maya.widget.__instance__.open_scene(new_scene)
        self.assertIsInstance(r, unicode)
        with self.assertRaises(RuntimeError):
            r = maya.widget.__instance__.open_scene('BOGUS/SCENE/null.ma')

        cmds.file(newFile=True, force=True)

        r = maya.widget.__instance__.import_scene(new_scene)
        self.assertIsInstance(r, unicode)
        with self.assertRaises(RuntimeError):
            r = maya.widget.__instance__.import_scene('BOGUS/SCENE/null.ma')

        cmds.file(newFile=True, force=True)

        r = maya.widget.__instance__.import_referenced_scene(new_scene)
        self.assertIsInstance(r, unicode)
        with self.assertRaises(RuntimeError):
            r = maya.widget.__instance__.import_scene('BOGUS/SCENE/null.ma')


    def test_outliner_sets(self):
        try:
            import bookmarks.maya as maya
        except ImportError as e:
            raise

        sets = maya.widget.outliner_sets()
        self.assertIsInstance(sets, dict)
        self.assertIn(u'testMesh_geo_set', sets)

    def test_alembic(self):
        try:
            import os
            from PySide2 import QtCore
            import bookmarks.maya as maya
            import maya.cmds as cmds
        except ImportError as e:
            raise

        sets = maya.widget.outliner_sets()
        k = u'testMesh_geo_set'
        dest = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.TempLocation)
        dest = dest + os.path.sep + '{}.abc'.format(k)
        bogus_destination = 'INVALID_PATH/TO/NOWHERE/alembic.abc'

        with self.assertRaises(TypeError):
            maya.widget.export_alembic(dest, k, 1.0, 10.0, step=1.0)

        with self.assertRaises(OSError):
            maya.widget.export_alembic(bogus_destination, sets[k], 1.0, 10.0, step=1.0)

        maya.widget.export_alembic(dest, sets[k], 1.0, 10.0, step=1.0)
        self.assertTrue(os.path.isfile(dest))

        r = maya.widget.__instance__.open_alembic(dest)
        self.assertIsInstance(r, unicode)
        with self.assertRaises(RuntimeError):
            r = maya.widget.__instance__.open_alembic('BOGUS/SCENE/null.ma')

        cmds.file(newFile=True, force=True)

        r = maya.widget.__instance__.import_alembic(dest)
        self.assertIsInstance(r, unicode)
        with self.assertRaises(RuntimeError):
            r = maya.widget.__instance__.import_alembic('BOGUS/SCENE/null.ma')

        r = maya.widget.__instance__.import_referenced_alembic(dest)
        self.assertIsInstance(r, unicode)
        with self.assertRaises(RuntimeError):
            r = maya.widget.__instance__.import_referenced_alembic('BOGUS/SCENE/null.ma')

        os.remove(dest)

    def test_export_set_to_alembic(self):
        try:
            import os
            from PySide2 import QtCore
            import bookmarks.maya as maya
            import maya.cmds as cmds
        except ImportError as e:
            raise

        sets = maya.widget.outliner_sets()
        k = u'testMesh_geo_set'

        r = maya.widget.__instance__.export_set_to_alembic(k, sets[k], frame=False)
        self.assertIsInstance(r, unicode)
        os.remove(r)

    def test__capture_viewport_destination(self):
        try:
            import os
            from PySide2 import QtCore
            import bookmarks.maya as maya
            import bookmarks.maya._mCapture as mCapture
        except ImportError as e:
            raise

        capture_folder, workspace, dest = maya.widget._capture_viewport_destination()
        self.assertIsInstance(capture_folder, unicode)
        self.assertIsInstance(workspace, unicode)
        self.assertIsInstance(dest, unicode)

    def test_capture_viewport(self):
        try:
            import os
            from PySide2 import QtCore
            import maya.cmds as cmds
            import bookmarks.maya as maya
            import bookmarks.maya._mCapture as mCapture
        except ImportError as e:
            raise

        with self.assertRaises(RuntimeError):
            maya.widget.capture_viewport()

    def test_apply_settings(self):
        try:
            import os
            from PySide2 import QtCore
            import maya.cmds as cmds
            import bookmarks.maya as maya
            import bookmarks.maya._mCapture as mCapture
        except ImportError as e:
            raise

        maya.widget.__instance__.apply_settings()


if __name__ == '__main__':
    loader = unittest.TestLoader()
    cases = (
        loader.loadTestsFromTestCase(TestMaya),
    )

    suite = unittest.TestSuite(cases)
    unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
