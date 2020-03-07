# -*- coding: utf-8 -*-
"""Maya standalone context."""

import gwbrowser.common as common
from maya import mel
from maya import cmds as cmds
import maya.standalone
from PySide2 import QtWidgets
from gwbrowser.maya.widget import MayaBrowserButton
import gwbrowser.maya as maya


app = QtWidgets.QApplication([])
maya.standalone.initialize(name='python')
mel.eval('')
cmds.loadPlugin("AbcExport.mll", quiet=True)
cmds.loadPlugin("AbcImport.mll", quiet=True)

common.DEBUG_ON = True
l = common.LogView()
l.show()

w = MayaBrowserButton()
w.show()
maya.widget.show()

meshes = []
for n in xrange(10):
    s = cmds.polyCube(name=u'testCube#')
    meshes.append(s[0])
cmds.sets(meshes, name=u'testCube_geo_set')

app.exec_()
maya.standalone.uninitialize()
