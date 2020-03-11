# -*- coding: utf-8 -*-
"""Basic test for the app.

The test leave a lot more to be desired but for now they will check bare-bone
functionality.

"""
import unittest


class TestImports(unittest.TestCase):

    def setUp(self):
        try:
            import gwbrowser
        except ImportError as err:
            self.fail(
                'Could not import <gwbrowser>. Is the modules available for Python?')

    def test_oiio_import(self):
        try:
            import OpenImageIO
        except ImportError as err:
            self.fail(err)

    def test_scandir_import(self):
        try:
            import gwbrowser.gwscandir
        except ImportError as err:
            self.fail(err)

    def test_qt_import(self):
        try:
            from PySide2 import QtCore, QtGui, QtWidgets
        except ImportError as err:
            self.fail(err)

    def test_slack_import(self):
        try:
            import slackclient
        except ImportError as err:
            self.fail(err)

    def test_psutil_import(self):
        try:
            import psutil
        except ImportError as err:
            self.fail(err)

    def test_alembic_import(self):
        try:
            import alembic
        except ImportError as err:
            self.fail(err)

    def test_numpy_import(self):
        try:
            import numpy
        except ImportError as err:
            self.fail(err)

    def test_sqlite_import(self):
        try:
            import sqlite3
        except ImportError as err:
            self.fail(err)


class TestSQLite(unittest.TestCase):
    root_dir = None
    server = None
    job = None

    @classmethod
    def setUpClass(cls):
        import uuid
        from PySide2 import QtCore
        tempdir = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.TempLocation)
        _id = uuid.uuid4()

        cls.root_dir = u'{tempdir}/testroot_{id}'.format(
            tempdir=tempdir,
            id=_id
        )
        _dir = QtCore.QDir(cls.root_dir)
        _dir.mkpath(u'.')

        cls.server = tempdir
        cls.job = u'testroot_{id}'.format(id=_id)
        _dir.mkpath(u'./bookmark_a')

    @classmethod
    def tearDownClass(cls):
        from PySide2 import QtCore
        _dir = QtCore.QDir(cls.root_dir)
        if _dir.exists():
            _dir.removeRecursively()

    def setUp(self):
        import os
        exists = os.path.exists(self.root_dir)
        if not exists:
            self.fail('Test directory does not exists')

        try:
            from PySide2 import QtCore
            import gwbrowser.bookmark_db as bookmark_db
            from gwbrowser.bookmark_db import BookmarkDB

            self.db = bookmark_db.get_db(
                QtCore.QModelIndex(),
                server=self.server,
                job=self.job,
                root='bookmark_a'
            )
        except Exception as err:
            self.fail('could not get the database: {}'.format(err))

        self.assertIsInstance(self.db, BookmarkDB)

    def tearDown(self):
        self.db.connection().close()
        self.db.deleteLater()
        self.db = None

    def test_row_id(self):
        self.assertEqual(self.db.row_id(-1), -1)
        self.assertEqual(self.db.row_id(0), 0)
        self.assertEqual(self.db.row_id(1), 1)

        self.assertEqual(self.db.row_id(u'UPPERCASE'), u'uppercase')
        self.assertEqual(self.db.row_id(u'ŰNICÓDE'), u'űnicóde')
        self.assertEqual(self.db.row_id(u'A\\B'), u'a/b')

        with self.assertRaises(TypeError):
            self.db.row_id('string')

    def test_set_get(self):
        k = 'description'
        id1 = u'ascii.key'
        id2 = u'ŰNICÓDE.key'

        self.db.setValue(id1, k, id1)
        v = self.db.value(id1, k)
        self.assertEqual(id1, v)

        self.db.setValue(id2, k, id2)
        v = self.db.value(id2, k)
        self.assertEqual(id2, v)

        self.db.setValue(id2, k, 0)
        v = self.db.value(id2, k)
        self.assertEqual(v, unicode(0))

        self.db.setValue(id2, k, 0.5)
        v = self.db.value(id2, k)
        self.assertEqual(v, unicode(0.5))

        self.db.setValue(id2, k, 99999.5)
        v = self.db.value(id2, k)
        self.assertEqual(v, unicode(99999.5))

        with self.assertRaises(TypeError):
            self.db.value(None, k)

        with self.assertRaises(TypeError):
            self.db.setValue(None, k, id1)

    def test_db_key(self):
        k = 'description'
        id1 = u'ŰNICÓDE.key'
        self.db.setValue(id1, k, id1)

        with self.assertRaises(ValueError):
            self.db.value(id1, 'bogustable')

        with self.assertRaises(ValueError):
            self.db.setValue(id1, 'bogustable', id1)


class TestBookmarksWidget(unittest.TestCase):
    app = None
    root_dir = None
    server = None
    job = None

    @classmethod
    def setUpClass(cls):
        import uuid
        from PySide2 import QtCore
        tempdir = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.TempLocation)
        _id = uuid.uuid4()
        cls.root_dir = u'{tempdir}/testroot_{id}'.format(
            tempdir=tempdir,
            id=_id
        )
        _dir = QtCore.QDir(cls.root_dir)
        _dir.mkpath(u'.')
        cls.server = tempdir
        cls.job = u'testroot_{id}'.format(id=_id)
        _dir.mkpath(u'./bookmark_a')
        ########################################
        import gwbrowser.common as common
        common.PRODUCT = '{}_unittest'.format(common.PRODUCT)

        import gwbrowser.settings as settings
        from gwbrowser.settings import LocalSettings
        settings.local_settings.deleteLater()
        settings.local_settings = LocalSettings()
        settings.local_settings.setValue(u'servers', None)

        from PySide2 import QtWidgets
        if not QtWidgets.QApplication.instance():
            cls.app = QtWidgets.QApplication([])
        else:
            cls.app = QtWidgets.QApplication.instance()

    @classmethod
    def tearDownClass(cls):
        import gwbrowser.settings as settings
        from PySide2 import QtCore
        QtCore.QFileInfo(settings.local_settings.fileName()
                         ).dir().removeRecursively()

        _dir = QtCore.QDir(cls.root_dir)
        if _dir.exists():
            _dir.removeRecursively()

    def setUp(self):
        import gwbrowser.settings as settings
        settings.local_settings.setValue(u'servers', None)
        settings.local_settings.sync()

    def tearDown(self):
        import gwbrowser.settings as settings
        settings.local_settings.setValue(u'servers', None)
        settings.local_settings.sync()

    def test_open_managebookmarks(self):
        import gwbrowser.managebookmarks as managebookmarks
        w = managebookmarks.Bookmarks()
        w.show()

    def test_managebookmarks_add_bookmark(self):
        import gwbrowser.managebookmarks as managebookmarks

        w = managebookmarks.Bookmarks()
        w.show()

        val = u'INVALID_SERVER'
        w.widget().server_editor.add_server_lineeditor.setText(val)
        w.widget().server_editor.add_server_button.clicked.emit()
        v = w.widget().get_saved_servers()
        self.assertEqual(v, [])

        val = self.server
        w.widget().server_editor.add_server_lineeditor.setText(self.server)
        w.widget().server_editor.add_server_button.clicked.emit()
        v = w.widget().get_saved_servers()
        self.assertEqual(v, [val.replace('\\', '/').lower(), ])

        val = self.server.replace(u'/', u'\\')
        w.widget().server_editor.add_server_lineeditor.setText(self.server)
        w.widget().server_editor.add_server_button.clicked.emit()
        v = w.widget().get_saved_servers()
        self.assertEqual(v, [val.replace('\\', '/').lower(), ])

    def test_read_jobs(self):
        import gwbrowser.managebookmarks as managebookmarks

        w = managebookmarks.Bookmarks()
        w.show()

        val = self.server
        w.widget().server_editor.add_server_lineeditor.setText(self.server)
        w.widget().server_editor.add_server_button.clicked.emit()
        v = w.widget().get_saved_servers()
        self.assertEqual(v, [val.replace(u'\\', u'/').lower(), ])

        idx = w.widget().job_combobox.findText(self.job.upper())
        self.assertNotEqual(idx, -1)


class TestModules(unittest.TestCase):
    app = None
    root_dir = None
    server = None
    job = None

    @classmethod
    def setUpClass(cls):
        import uuid
        from PySide2 import QtCore
        tempdir = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.TempLocation)
        _id = uuid.uuid4()
        cls.root_dir = u'{tempdir}/testroot_{id}'.format(
            tempdir=tempdir,
            id=_id
        )
        _dir = QtCore.QDir(cls.root_dir)
        _dir.mkpath(u'.')
        cls.server = tempdir
        cls.job = u'testroot_{id}'.format(id=_id)
        _dir.mkpath(u'./bookmark_a')
        _dir.mkpath(u'./bookmark_a/asset_a')
        _dir.mkpath(u'./bookmark_a/taskdir_a')

        from PySide2 import QtWidgets
        if not QtWidgets.QApplication.instance():
            cls.app = QtWidgets.QApplication([])
        else:
            cls.app = QtWidgets.QApplication.instance()

    @classmethod
    def tearDownClass(cls):
        from PySide2 import QtCore
        _dir = QtCore.QDir(cls.root_dir)
        if _dir.exists():
            _dir.removeRecursively()

    def test_addassetwidget(self):
        import gwbrowser.addassetwidget as addassetwidget
        path = u'/'
        w = addassetwidget.AddAssetWidget(path)
        w.open()

    def test_addfilewidget(self):
        import gwbrowser.addfilewidget as addfilewidget
        w = addfilewidget.AddFileWidget(u'ma')
        w.open()

    def test_assetwidget(self):
        import gwbrowser.assetswidget as assetswidget
        widget = assetswidget.AssetsWidget()
        widget.model().sourceModel().parent_path = (
            self.server, self.job, 'bookmark_b',)
        widget.model().sourceModel().modelDataResetRequested.emit()
        widget.show()

    def test_basecontextmenu(self):
        from PySide2 import QtCore
        import gwbrowser.basecontextmenu as basecontextmenu
        widget = basecontextmenu.BaseContextMenu(QtCore.QModelIndex())
        widget.show()

    def test_bookmark_properties(self):
        from PySide2 import QtCore
        import gwbrowser.bookmark_properties as bookmark_properties
        widget = bookmark_properties.BookmarkPropertiesWidget(
            QtCore.QModelIndex(),
            server=self.server,
            job=self.job,
            root=u'bookmark_a'
        )
        widget.show()

    def test_baselistwidget(self):
        import gwbrowser.baselistwidget as baselistwidget

    def test_bookmarkswidget(self):
        import gwbrowser.bookmarkswidget as bookmarkswidget
        widget = bookmarkswidget.BookmarksWidget()
        widget.model().sourceModel().modelDataResetRequested.emit()
        widget.show()

    def test_datakeywidget(self):
        import gwbrowser.datakeywidget as datakeywidget
        widget = datakeywidget.DataKeyView()
        widget.model().modelDataResetRequested.emit()
        widget.show()

    def test_browserwidget(self):
        import gwbrowser.browserwidget as browserwidget
        widget = browserwidget.BrowserWidget()
        widget.show()

    def test_favouriteswidget(self):
        import gwbrowser.favouriteswidget as favouriteswidget
        widget = favouriteswidget.FavouritesWidget()
        widget.show()

    def test_preferenceswidget(self):
        import gwbrowser.preferenceswidget as preferenceswidget
        widget = preferenceswidget.PreferencesWidget()
        widget.show()

    def test_slacker(self):
        import gwbrowser.slacker as slacker
        widget = slacker.SlackWidget(None, None)
        widget.show()

    def test_standalonewidgets(self):
        import gwbrowser.standalonewidgets as standalonewidgets
        widget = standalonewidgets.StandaloneBrowserWidget()
        widget.show()

    def test_fileswidget(self):
        import gwbrowser.fileswidget as fileswidget
        widget = fileswidget.FilesWidget()
        widget.model().sourceModel().parent_path = (
            self.server, self.job, 'bookmark_a', u'asset_a')
        widget.model().sourceModel().modelDataResetRequested.emit()
        widget.model().sourceModel().dataKeyChanged.emit('taskdir_a')
        widget.show()

    def test_todo_editor(self):
        from PySide2 import QtCore
        import gwbrowser.todo_editor as todo_editor
        widget = todo_editor.TodoEditorWidget(QtCore.QModelIndex())
        widget.add_item(
            idx=0, text=u'Hello world', checked=False)
        widget.add_item(
            idx=1, text=u'Hello world', checked=True)
        widget.add_item(idx=2, text='file://test.com', checked=False)
        widget.add_item(idx=0, text='First item', checked=False)
        widget.show()

    def test_versioncontrol(self):
        from PySide2 import QtCore
        import gwbrowser.versioncontrol.versioncontrol as versioncontrol
        versioncontrol.check()


class TestLocalSettings(unittest.TestCase):
    local_settings = None

    @classmethod
    def setUpClass(cls):
        from gwbrowser.settings import LocalSettings
        LocalSettings.filename = 'unittestconfig.ini'
        cls.local_settings = LocalSettings()
        cls.local_settings.sync()

    @classmethod
    def tearDownClass(cls):
        from PySide2 import QtCore
        p = cls.local_settings.config_path
        cls.local_settings.deleteLater()
        cls.local_settings = None
        QtCore.QFile.remove(p)

    def test_set_get(self):
        k = 'unittest'
        val = u'ascii'
        self.local_settings.setValue(k, val)
        v = self.local_settings.value(k)
        self.assertEqual(val, v)

        val = u'ŰNICÓDE'
        self.local_settings.setValue(k, val)
        v = self.local_settings.value(k)
        self.assertEqual(val, v)

        val = True
        self.local_settings.setValue(k, val)
        v = self.local_settings.value(k)
        self.assertEqual(val, v)

        val = False
        self.local_settings.setValue(k, val)
        v = self.local_settings.value(k)
        self.assertEqual(val, v)

        val = None
        self.local_settings.setValue(k, val)
        v = self.local_settings.value(k)
        self.assertEqual(val, v)

        val = 0
        self.local_settings.setValue(k, val)
        v = self.local_settings.value(k)
        self.assertEqual(val, v)

        val = 1
        self.local_settings.setValue(k, val)
        v = self.local_settings.value(k)
        self.assertEqual(val, v)

        val = -1
        self.local_settings.setValue(k, val)
        v = self.local_settings.value(k)
        self.assertEqual(val, v)

        val = 0.00001
        self.local_settings.setValue(k, val)
        v = self.local_settings.value(k)
        self.assertEqual(val, v)


class TestImages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide2 import QtWidgets
        app = QtWidgets.QApplication.instance()
        if not app:
            app = QtWidgets.QApplication([])

    def setUp(self):
        self.source = None
        import gwbrowser.images as images
        import os

        test_image = 'custom.png'

        p = os.path.normpath(images.__file__)
        p = os.path.abspath(p)
        p = os.path.dirname(p)
        f = p + os.path.sep + 'rsc' + os.path.sep + test_image

        if not os.path.isfile(f):
            self.fail('Could not find "{}"'.format(test_image))
            return

        self.source = f

    def tearDown(self):
        self.source = None

    def test_oiio_get_qimage(self):
        import gwbrowser.images as images
        from PySide2 import QtGui
        image = images.oiio_get_qimage(self.source)

        self.assertIsInstance(image, QtGui.QImage)
        self.assertNotEqual(image.isNull(), None)

    def test_get(self):
        import gwbrowser.images as images
        from PySide2 import QtGui

        image = images.ImageCache.get(self.source)

        self.assertIsInstance(image, QtGui.QPixmap)
        self.assertNotEqual(image.isNull(), None)
        self.assertEqual(image.width(), 256)

    def test_resize_image(self):
        import gwbrowser.images as images
        from PySide2 import QtGui

        height = 1024
        image = images.ImageCache.get(self.source, 1024)
        self.assertIsInstance(image, QtGui.QPixmap)
        self.assertNotEqual(image.isNull(), None)
        self.assertEqual(image.width(), height)

    def test_get_color_average(self):
        import gwbrowser.images as images
        from PySide2 import QtGui
        color = images.ImageCache.get_color_average(self.source)
        self.assertIsInstance(color, QtGui.QColor)


    def test_get_rsc_pixmap(self):
        import gwbrowser.images as images
        from PySide2 import QtGui

        height = 32.0
        pixmap = images.ImageCache.get_rsc_pixmap('custom', None, height)
        self.assertNotEqual(pixmap.isNull(), None)
        self.assertEqual(pixmap.width(), height)

        pixmap = images.ImageCache.get_rsc_pixmap('BOGUSIMAGE', None, height)
        self.assertEqual(pixmap.isNull(), True)

        path = images.ImageCache.get_rsc_pixmap('custom', None, height, get_path=True)
        self.assertEqual(path, self.source.replace('\\', '/'))


if __name__ == '__main__':
    loader = unittest.TestLoader()
    cases = (
        loader.loadTestsFromTestCase(TestImports),
        loader.loadTestsFromTestCase(TestSQLite),
        loader.loadTestsFromTestCase(TestImages),
        loader.loadTestsFromTestCase(TestLocalSettings),
        loader.loadTestsFromTestCase(TestBookmarksWidget),
        loader.loadTestsFromTestCase(TestModules),
    )

    suite = unittest.TestSuite(cases)
    unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
