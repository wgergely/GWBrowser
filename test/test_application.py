# -*- coding: utf-8 -*-
"""Bookmarks unittesting module."""
import unittest


class BaseCase(unittest.TestCase):
    """Base test class.

    Responsible for creating the sandbox environment used for testing.

    """
    app = None
    root_dir = None
    server = None
    job = None
    bookmarks = (u'apple', u'banana', u'orange')

    @classmethod
    def setUpClass(cls):
        import uuid
        from PySide2 import QtCore, QtWidgets
        import bookmarks.common as common
        import bookmarks.settings as settings
        import bookmarks.standalone as standalone

        common.PRODUCT = u'bookmarks_unittest'

        settings.local_settings.deleteLater()
        settings.local_settings = settings.LocalSettings()
        settings.local_settings.setValue(u'servers', None)

        # Add mock server dir
        tempdir = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.TempLocation)
        cls.server = tempdir

        # Mock job dir
        _id = uuid.uuid4()
        cls.job = u'testroot_{id}'.format(id=_id)

        cls.root_dir = u'{tempdir}/testroot_{id}'.format(
            tempdir=tempdir, id=_id)
        _dir = QtCore.QDir(cls.root_dir)
        _dir.mkpath(u'.')
        for bookmark in cls.bookmarks:
            _dir.mkpath(u'./{}'.format(bookmark))

        if not QtWidgets.QApplication.instance():
            cls.app = standalone.StandaloneApp([])
        else:
            cls.app = QtWidgets.QApplication.instance()

    @classmethod
    def tearDownClass(cls):
        from PySide2 import QtCore
        import bookmarks.settings as settings

        # Remove local settings file
        s = settings.local_settings.fileName()
        f = QtCore.QFileInfo(s)
        if f.exists():
            f.dir().removeRecursively()

        # Remove temp directory
        _dir = QtCore.QDir(cls.root_dir)
        if _dir.exists():
            _dir.removeRecursively()


class TestScandir(BaseCase):
    def test_scandir(self):
        import _scandir as scandir
        import os

        p = os.path.abspath(os.path.join(__file__, os.pardir))

        it = scandir.scandir(unicode(p))
        for entry in it:
            self.assertIsInstance(entry, scandir.DirEntry)
            self.assertIsInstance(entry.name, unicode)
            self.assertIsInstance(entry.path, unicode)


class TestDependencies(BaseCase):
    def test_oiio_import(self):
        try:
            import OpenImageIO
        except ImportError as err:
            self.fail(err)

    def test_scandir_import(self):
        try:
            import _scandir
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


class TestSQLite(BaseCase):

    @classmethod
    def setUpClass(cls):
        super(TestSQLite, cls).setUpClass()
        import bookmarks.bookmark_db as bookmark_db

        cls.db = bookmark_db.get_db(
            cls.server,
            cls.job,
            cls.bookmarks[0]
        )

    def test_get_hash(self):
        import bookmarks.common as common
        self.assertEqual(common.get_hash(-1), -1)
        self.assertEqual(common.get_hash(0), 0)
        self.assertEqual(common.get_hash(1), 1)

        a = common.get_hash(u'UPPERCASE')
        b = common.get_hash(u'uppercase')
        self.assertEqual(a, b)
        self.assertIsInstance(a, str)
        self.assertIsInstance(b, str)

        a = common.get_hash(u'ŰNICÓDE')
        b = common.get_hash(u'űnicóde')
        self.assertEqual(a, b)
        self.assertIsInstance(a, str)
        self.assertIsInstance(b, str)

        a = common.get_hash(u'A\\B')
        b = common.get_hash(u'a/b')
        self.assertEqual(a, b)
        self.assertIsInstance(a, str)
        self.assertIsInstance(b, str)

        with self.assertRaises(TypeError):
            common.get_hash('string')

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
        k = u'description'
        id1 = u'ŰNICÓDE.key'
        self.db.setValue(id1, k, id1)

        with self.assertRaises(ValueError):
            self.db.value(id1, 'bogustable')

        with self.assertRaises(ValueError):
            self.db.setValue(id1, 'bogustable', id1)

    def test_bookmark_properties(self):
        table = 'properties'
        with self.db.transactions():
            data = self.db.value(1, u'framerate', table=table)
            self.assertEqual(data, None)

            v = 24
            self.db.setValue(1, u'framerate', v, table=table)
            data = self.db.value(1, u'framerate', table=table)
            self.assertEqual(v, data)

            v = 24.976
            self.db.setValue(1, u'framerate', v, table=table)
            data = self.db.value(1, u'framerate', table=table)
            self.assertEqual(v, data)

            data = self.db.value(1, u'framerate', table=table)
            self.db.setValue(1, u'framerate', u'24.976', table=table)
            data = self.db.value(1, u'framerate', table=table)
            self.assertEqual(v, data)

            v = 1920
            self.db.setValue(1, 'width', v, table=table)
            data = self.db.value(1, u'width', table=table)
            self.assertEqual(v, data)

            v = 1080
            self.db.setValue(1, u'height', v, table=table)
            data = self.db.value(1, u'height', table=table)
            self.assertEqual(v, data)

            data = self.db.value(1, u'slacktoken', table=table)
            self.assertEqual(data, None)

            v = u'string'
            self.db.setValue(1, u'slacktoken', v, table=table)
            data = self.db.value(1, u'slacktoken', table=table)
            self.assertEqual(v, data)

        data = self.db.value(1, u'framerate', table=table)
        self.assertNotEqual(data, None)


class TestBookmarksWidget(BaseCase):

    def setUp(self):
        import bookmarks.settings as settings
        settings.local_settings.setValue(u'servers', None)
        settings.local_settings.sync()

    def tearDown(self):
        import bookmarks.settings as settings
        settings.local_settings.setValue(u'servers', None)
        settings.local_settings.sync()

    def test_open_managebookmarks(self):
        import bookmarks.managebookmarks as managebookmarks
        w = managebookmarks.ManageBookmarks()

    def test_managebookmarks_add_bookmark(self):
        import bookmarks.managebookmarks as managebookmarks

        w = managebookmarks.ManageBookmarks()

        val = u'INVALID_SERVER'
        w.scrollarea.widget().server_editor.add_server_lineeditor.setText(val)
        w.scrollarea.widget().server_editor.add_server_button.clicked.emit()
        v = w.scrollarea.widget().get_saved_servers()
        self.assertEqual(v, [])

        val = self.server
        w.scrollarea.widget().server_editor.add_server_lineeditor.setText(self.server)
        w.scrollarea.widget().server_editor.add_server_button.clicked.emit()
        v = w.scrollarea.widget().get_saved_servers()
        self.assertEqual(v, [val.replace(u'\\', u'/').lower(), ])

        val = self.server.replace(u'/', u'\\')
        w.scrollarea.widget().server_editor.add_server_lineeditor.setText(self.server)
        w.scrollarea.widget().server_editor.add_server_button.clicked.emit()
        v = w.scrollarea.widget().get_saved_servers()
        self.assertEqual(v, [val.replace(u'\\', u'/').lower(), ])

    def test_read_jobs(self):
        import bookmarks.managebookmarks as managebookmarks

        w = managebookmarks.ManageBookmarks()

        val = self.server
        w.scrollarea.widget().server_editor.add_server_lineeditor.setText(self.server)
        w.scrollarea.widget().server_editor.add_server_button.clicked.emit()
        v = w.scrollarea.widget().get_saved_servers()
        self.assertEqual(v, [val.replace(u'\\', u'/').lower(), ])

        idx = w.scrollarea.widget().job_combobox.findText(self.job.upper())
        self.assertNotEqual(idx, -1)


class TestGui(BaseCase):

    def test_addassetwidget(self):
        import bookmarks.addassetwidget as addassetwidget
        w = addassetwidget.AddAssetWidget(
            self.server,
            self.job,
            self.bookmarks[0],
        )
        w.open()

    def test_addfilewidget(self):
        import bookmarks.addfilewidget as addfilewidget
        w = addfilewidget.AddFileWidget(u'ma')
        w.open()

    def test_assetwidget(self):
        import bookmarks.assetswidget as assetswidget
        widget = assetswidget.AssetsWidget()
        widget.model().sourceModel().parent_path = (
            self.server, self.job, self.bookmarks[1 ],)
        widget.model().sourceModel().modelDataResetRequested.emit()
        widget.show()

    def test_basecontextmenu(self):
        from PySide2 import QtCore
        import bookmarks.basecontextmenu as basecontextmenu
        w = basecontextmenu.BaseContextMenu(QtCore.QModelIndex())
        w.show()

    def test_bookmark_properties_widget(self):
        from PySide2 import QtCore
        import bookmarks.bookmark_properties as bookmark_properties
        w = bookmark_properties.BookmarkPropertiesWidget(
            server=self.server,
            job=self.job,
            root=self.bookmarks[0]
        )
        w.open()

    def test_baselist_widget(self):
        import bookmarks.baselist as baselist

    def test_bookmarks_widget(self):
        import bookmarks.bookmarkswidget as bookmarkswidget
        widget = bookmarkswidget.BookmarksWidget()
        widget.model().sourceModel().modelDataResetRequested.emit()
        widget.show()

    def test_taskfolders_widget(self):
        import bookmarks.taskfolderwidget as taskfolderwidget
        widget = taskfolderwidget.TaskFolderWidget()
        widget.model().modelDataResetRequested.emit()
        widget.show()

    def test_main_widget(self):
        import bookmarks.mainwidget as mainwidget
        widget = mainwidget.MainWidget()
        widget.show()

    def test_favourites_widget(self):
        import bookmarks.favouriteswidget as favouriteswidget
        widget = favouriteswidget.FavouritesWidget()
        widget.show()

    def test_preferences_widget(self):
        import bookmarks.preferenceswidget as preferenceswidget
        widget = preferenceswidget.PreferencesWidget()
        widget.open()

    def test_slacker_widget(self):
        import bookmarks.slacker as slacker
        widget = slacker.SlackWidget(None, None)
        widget.open()

    def test_standalone_widget(self):
        import bookmarks.standalone as standalone
        import bookmarks.mainwidget as mainwidget
        if mainwidget._instance:
            mainwidget._instance.deleteLater()
            mainwidget._instance = None

        widget = standalone.StandaloneMainWidget()
        widget.show()
        with self.assertRaises(RuntimeError):
            standalone.StandaloneMainWidget()

    def test_files_widget(self):
        import bookmarks.fileswidget as fileswidget
        widget = fileswidget.FilesWidget()
        widget.model().sourceModel().parent_path = (
            self.server, self.job, self.bookmarks[0], u'asset_a')
        widget.model().sourceModel().modelDataResetRequested.emit()
        widget.model().sourceModel().taskFolderChanged.emit('taskdir_a')
        widget.show()

    def test_todo_editor(self):
        from PySide2 import QtCore
        import bookmarks.todo_editor as todo_editor
        widget = todo_editor.TodoEditorWidget(QtCore.QModelIndex())
        widget.add_item(
            idx=0, text=u'Hello world', checked=False)
        widget.add_item(
            idx=1, text=u'Hello world', checked=True)
        widget.add_item(idx=2, text='file://test.com', checked=False)
        widget.add_item(idx=0, text='First item', checked=False)
        widget.open()

class TestVersionControl(BaseCase):
    def test_versioncontrol(self):
        from PySide2 import QtCore
        import bookmarks.versioncontrol.versioncontrol as versioncontrol
        try:
            versioncontrol.check()
        except Exception as e:
            raise


class TestLocalSettings(unittest.TestCase):
    local_settings = None

    @classmethod
    def setUpClass(cls):
        from bookmarks.settings import LocalSettings
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


class TestImages(BaseCase):
    def setUp(self):
        self.source = None
        import bookmarks.images as images
        import os

        test_image = u'icon.png'

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

    def test_oiio_get_buf(self):
        import bookmarks.images as images
        import OpenImageIO
        buf = images.oiio_get_buf(u'bogus_path')
        self.assertEqual(buf, None)
        buf = images.oiio_get_buf(self.source)
        self.assertIsInstance(buf, OpenImageIO.ImageBuf)

        with self.assertRaises(TypeError):
            buf = images.oiio_get_buf('wrong_type')

    def test_oiio_get_qimage(self):
        import bookmarks.images as images
        from PySide2 import QtGui
        image = images.oiio_get_qimage(self.source)

        self.assertIsInstance(image, QtGui.QImage)
        self.assertNotEqual(image.isNull(), None)

    def test_get_placeholder_path(self):
        import bookmarks.images as images
        from PySide2 import QtGui

        with self.assertRaises(TypeError):
            images.get_placeholder_path('invalid/str/path')

        image = images.get_placeholder_path(u'invalid/path')
        self.assertIsInstance(image, unicode)

        ext_image = images.get_placeholder_path(u'invalid/path.ma')
        self.assertIsInstance(ext_image, unicode)

        self.assertNotEqual(image, ext_image)

    def test_get_thumbnail_path(self):
        import bookmarks.images as images

        a = images.get_thumbnail_path(
            u'server',
            u'job',
            u'root',
            u'server/job/root/folder/file.png')
        self.assertIsInstance(a, unicode)
        b = images.get_thumbnail_path(
            u'server'.upper(),
            u'job'.upper(),
            u'root'.upper(),
            u'server/job/root/folder/file.png'.upper())
        self.assertIsInstance(b, unicode)

        self.assertEqual(a, b)

        a = images.get_thumbnail_path(
            u'server',
            u'job',
            u'root',
            u'server/job/root/folder/file_0001.exr')
        b = images.get_thumbnail_path(
            u'server',
            u'job',
            u'root',
            u'server/job/root/folder/file_0002.exr')
        self.assertNotEqual(a, b)

        a = images.get_thumbnail_path(
            u'server',
            u'job',
            u'root',
            u'server/job/root/folder/file_[1-2].exr')
        b = images.get_thumbnail_path(
            u'server',
            u'job',
            u'root',
            u'server/job/root/folder/file_[1-55].exr')
        self.assertEqual(a, b)

        a = images.get_thumbnail_path(
            u'server',
            u'job',
            u'root',
            u'server/job/root/folder/file_[1000,1001].exr')
        b = images.get_thumbnail_path(
            u'server',
            u'job',
            u'root',
            u'server/job/root/folder/file_[2001,2002].exr'.upper())
        self.assertEqual(a, b)

    def test_get_image(self):
        import bookmarks.images as images
        from PySide2 import QtGui

        image = images.ImageCache.get_image(self.source, 256)
        self.assertIsInstance(image, QtGui.QImage)
        self.assertNotEqual(image.isNull(), None)
        self.assertEqual(image.width(), 256)

        image2 = images.ImageCache.get_image(self.source, 256)
        self.assertEqual(image, image2)

        image = images.ImageCache.get_image(self.source, 128)
        self.assertNotEqual(image.isNull(), None)
        self.assertEqual(image.width(), 128)

        with self.assertRaises(TypeError):
            image = images.ImageCache.get_image('bogus/path', 128)

        image = images.ImageCache.get_image(u'bogus/path', 128)
        self.assertEqual(image, None)

    def test_get_color(self):
        import bookmarks.images as images
        from PySide2 import QtGui

        color = images.ImageCache.get_color(self.source)
        self.assertEqual(color, None)

        images.ImageCache.make_color(self.source)
        color = images.ImageCache.get_color(self.source)
        self.assertIsInstance(color, QtGui.QColor)

        color2 = images.ImageCache.get_color(self.source)
        self.assertEqual(color, color2)

    def test_get_pixmap(self):
        import bookmarks.images as images
        from PySide2 import QtGui

        image = images.ImageCache.get_pixmap(self.source, 256)
        self.assertIsInstance(image, QtGui.QPixmap)
        self.assertNotEqual(image.isNull(), None)
        self.assertEqual(image.width(), 256)

        image2 = images.ImageCache.get_pixmap(self.source, 256)
        self.assertEqual(image, image2)

        image = images.ImageCache.get_pixmap(self.source, 128)
        self.assertNotEqual(image.isNull(), None)
        self.assertEqual(image.width(), 128)

        with self.assertRaises(TypeError):
            image = images.ImageCache.get_pixmap('bogus/path', 128)

        image = images.ImageCache.get_pixmap(u'bogus/path', 128)
        self.assertEqual(image, None)

    def test_resize_image(self):
        import bookmarks.images as images
        from PySide2 import QtGui

        height = 1024
        image = images.ImageCache.get_image(self.source, 1024)
        self.assertIsInstance(image, QtGui.QImage)
        self.assertNotEqual(image.isNull(), None)
        self.assertEqual(image.width(), height)

        height = 512
        image2 = images.ImageCache.get_image(self.source, 512)
        self.assertIsInstance(image2, QtGui.QImage)
        self.assertNotEqual(image2.isNull(), None)
        self.assertEqual(image2.width(), height)

        self.assertNotEqual(image, image2)

    def test_get_rsc_pixmap(self):
        import bookmarks.images as images
        from PySide2 import QtGui

        height = 32.0
        pixmap = images.ImageCache.get_rsc_pixmap(u'icon', None, height)
        self.assertNotEqual(pixmap.isNull(), None)
        self.assertEqual(pixmap.width(), height)

        pixmap = images.ImageCache.get_rsc_pixmap(u'BOGUSIMAGE', None, height)
        self.assertEqual(pixmap.isNull(), True)

        path = images.ImageCache.get_rsc_pixmap(u'icon', None, height, get_path=True)
        self.assertEqual(path, self.source.replace(u'\\', u'/'))


class TestAddFileWidget(BaseCase):
    @classmethod
    def setUpClass(cls):
        from PySide2 import QtCore
        super(TestAddFileWidget, cls).setUpClass()
        _dir = QtCore.QDir(cls.root_dir)
        for bookmark in cls.bookmarks:
            _dir.mkpath(u'./{}'.format(bookmark))
            _dir.mkpath(u'./{}/asset_a'.format(bookmark))
            _dir.mkpath(u'./{}/taskdir_a'.format(bookmark))

    def setUp(self):
        import os
        exists = os.path.exists(self.root_dir)
        if not exists:
            self.fail('Test directory does not exists')

    def testImport(self):
        import bookmarks.addfilewidget as addfilewidget

    def testWidget(self):
        import bookmarks.addfilewidget as addfilewidget

        with self.assertRaises(ValueError):
            w = addfilewidget.AddFileWidget(None)
            w.deleteLater()

        with self.assertRaises(ValueError):
            w = addfilewidget.AddFileWidget(u'')
            w.deleteLater()
            w.deleteLater()

        w = addfilewidget.AddFileWidget(u'ma')
        w.deleteLater()

        destination = u'{}/testfile.ma'.format(self.root_dir)
        w = addfilewidget.AddFileWidget(None, file=destination)
        destination = u'{}/testfile_v0001.ma'.format(self.root_dir)
        self.assertEqual(w.get_file_path(), destination)

        destination = u'{}/testfile_v0001.ma'.format(self.root_dir)
        w = addfilewidget.AddFileWidget(None, file=destination)
        self.assertEqual(w.get_file_path(), destination)

        with open(destination, 'w') as f:
            f.write(destination)

        destination = u'{}/testfile_v0001.ma'.format(self.root_dir)
        w = addfilewidget.AddFileWidget(None, file=destination)
        destination = u'{}/testfile_v0002.ma'.format(self.root_dir)
        self.assertEqual(w.get_file_path(), destination)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    cases = (
        loader.loadTestsFromTestCase(TestDependencies),
        loader.loadTestsFromTestCase(TestScandir),
        loader.loadTestsFromTestCase(TestImages),
        loader.loadTestsFromTestCase(TestSQLite),
        loader.loadTestsFromTestCase(TestLocalSettings),
        loader.loadTestsFromTestCase(TestAddFileWidget),
        loader.loadTestsFromTestCase(TestBookmarksWidget),
        loader.loadTestsFromTestCase(TestGui),
        loader.loadTestsFromTestCase(TestVersionControl),
    )
    suite = unittest.TestSuite(cases)
    unittest.TextTestRunner(verbosity=3, failfast=True).run(suite)
