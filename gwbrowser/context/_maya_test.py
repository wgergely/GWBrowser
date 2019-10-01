# -*- coding: utf-8 -*-
"""Maya standalone context."""

import os
import sys
import maya.standalone
from PySide2 import QtWidgets, QtCore, QtGui

# PySide2 needs an app before Maya is initialized:
app = QtWidgets.QApplication([])
maya.standalone.initialize(name='python')

# cmds and mel modules
from maya import cmds as cmds
from maya.mel import eval

cmds.loadPlugin("AbcExport.mll", quiet=True)
cmds.loadPlugin("AbcImport.mll", quiet=True)

# CUSTOM BLOCK -- START


import gwbrowser.context.mayabrowserwidget as mayabrowserwidget
from gwbrowser.context.mayabrowserwidget import MayaBrowserButton
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
