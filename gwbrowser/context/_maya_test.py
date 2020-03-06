# -*- coding: utf-8 -*-
"""Maya standalone context."""

from maya import cmds as cmds
import maya.standalone
from PySide2 import QtWidgets
from gwbrowser.context.mayabrowserwidget import MayaBrowserButton
import gwbrowser.context.mayabrowserwidget as mayabrowserwidget


app = QtWidgets.QApplication([])
maya.standalone.initialize(name='python')
from maya import mel
mel.eval('')
cmds.loadPlugin("AbcExport.mll", quiet=True)
cmds.loadPlugin("AbcImport.mll", quiet=True)

# CUSTOM BLOCK -- START

import gwbrowser.common as common
common.DEBUG_ON = True
l = common.LogView()
l.show()
w = MayaBrowserButton()
w.show()
mayabrowserwidget.show()

meshes = []
for n in xrange(10):
    s = cmds.polyCube(name=u'testCube#')
    meshes.append(s[0])
cmds.sets(meshes, name=u'testCube_geo_set')


# CUSTOM BLOCK -- END
# Shutdown
app.exec_()
maya.standalone.uninitialize()
