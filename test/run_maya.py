#!mayapy
# -*- coding: utf-8 -*-
"""Make sure the $MAYA_ROOT/bin directory is in the path before running the test."""

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

meshes = []
for n in xrange(10):
    s = cmds.polyCube(name=u'testMesh#')
    meshes.append(s[0])
cmds.sets(meshes, name=u'testMesh_geo_set')
cmds.sets([], name=u'emptyTestMesh_geo_set')


common.STANDALONE = False
w = MayaBrowserButton()
w.show()

try:
    from PySide2 import QtCore, QtGui
except ImportError as e:
    raise

w.clicked.emit()
app.exec_()
