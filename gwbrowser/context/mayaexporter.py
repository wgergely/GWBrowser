# -*- coding: utf-8 -*-
"""Maya wrapper for the BrowserWidget."""

import sys
import time

from PySide2 import QtCore

import maya.OpenMayaUI as OpenMayaUI
import maya.OpenMaya as OpenMaya
from shiboken2 import wrapInstance
import maya.cmds as cmds


class BaseExporter(QtCore.QObject):
    """Just a baseclass to wrap the more abstract methods."""

    _instance = None
    progress = QtCore.Signal(int, int, int)
    progressPercentile = QtCore.Signal(float)

    def __new__(cls, *args, **kwargs):
        cls._instance = QtCore.QObject.__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, parent=None):
        super(BaseExporter, self).__init__(parent=parent)
        self.time = 0.0
        self.progress.connect(self.report_progress)

    def report_progress(self, start, current, end):
        elapsed = time.time() - self.time
        elapsed = time.strftime('%H:%M.%Ssecs', time.localtime(elapsed))

        start = int(start)
        current = int(current)
        end = int(end)

        _current = current - start
        _end = end - start

        progress = float(_current) / float(_end) * 100
        progress = '{}%'.format(int(progress))

        msg = '\n\n# Exporting frame {current} of {end} ({progress})\n# Elapsed: {elapsed}\n\n'.format(
            current=current,
            end=end,
            progress=progress,
            elapsed=elapsed
        )
        self.progressPercentile.emit((float(_current) / float(_end)))
        sys.stdout.write(msg)

    @classmethod
    def instance(cls):
        return cls._instance

    def _setFilterScript(self, name):
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

    def get_outliner_set_members(self):
        """Returns the available outliner sets and the objects inside."""
        setData = {}
        for s in sorted([k for k in cmds.ls(sets=True) if self._setFilterScript(k)]):
            dagMembers = cmds.listConnections(u'{}.dagSetMembers'.format(s))
            # Filters
            if not dagMembers:
                continue
            setData[s] = [cmds.ls(dag)[-1] for dag in dagMembers]
        return setData


class AlembicExport(BaseExporter):
    """Utility class for exporting alembic caches from maya.
    Exportable objects are those that are in a user-added objectSet (one, that is
    visible in the outliner.).

    Prior to exporting the hierarchy will be flattened, to avoid any issues with
    parenting.

    """

    def export(self, filepath, outliner_set, startframe, endframe, step=1.0, preroll=100.0):
        """Main Alembic export script. We will querry the outliner_set items and
        we'll flatten the hierarchy before exporting."""

        def is_intermediate(s): return cmds.getAttr(
            '{}.intermediateObject'.format(s))

        def is_template(s): return cmds.getAttr('{}.template'.format(s))

        roots = []
        for item in outliner_set:
            relatives = cmds.listRelatives(item, shapes=True)
            if not relatives:
                continue
            sources = [f for f in relatives if not is_intermediate(
                f) and not is_template(f)]
            if not sources:
                continue
            for source in sources:
                if not cmds.attributeQuery('worldMesh', node=source, exists=True):
                    continue
                dest = cmds.createNode('mesh', name='abc_{}'.format(source))

                cmds.connectAttr('{}.worldMesh[0]'.format(
                    source), '{}.inMesh'.format(dest), force=True)
                cmds.connectAttr('{}.uvSet'.format(source),
                                 '{}.uvSet'.format(dest), force=True)

                transform = cmds.listRelatives(dest, type='transform', p=True)
                if transform:
                    roots.append(transform[-1])

        if not roots:
            sys.stdout.write(
                '# Alembic export: No valid root nodes were specified.\n')
            return

        perframecallback = '"import gwbrowser.context.mayabrowserwidget as mb; mb.AlembicExport.instance().progress.emit({}, #FRAME#, {})"'.format(
            int(startframe), int(endframe))
        kwargs = {
            'jobArg': '{f} {fr} {s} {uv} {ws} {wv} {wuvs} {rt} {ef} {df} {pfc} {ppc}'.format(
                f='-file {}'.format(filepath),
                fr='-framerange {} {}'.format(startframe, endframe),
                # frs='-framerelativesample {}'.format(1.0),
                # no='-nonormals',
                # uvo='-uvsonly',
                # pr='-preroll {}'.format(bool(preroll)),
                # ro='-renderableonly',
                s='-step {}'.format(step),
                # sl='-selection {}'.format(False),
                # sn='-stripnamespaces',
                uv='-uvwrite',
                # wcs='-writecolorsets',
                # wfs='-writefacesets',
                # wfg='-wholeframegeo',
                ws='-worldspace',
                wv='-writevisibility',
                wuvs='-writeuvsets',
                # as_='-autosubd',
                # mfc='-melperframecallback {}'.format(''),
                pfc='-pythonperframecallback {}'.format(perframecallback),
                # pfc='-pythonperframecallback {}'.format('"\'Exporting #FRAME# of {}\'"'.format(endframe)),
                # mpc='-melpostjobcallback {}'.format(''),
                ppc='-pythonpostjobcallback {}'.format(
                    '"\'Finished alembic export!\'"'),
                # ppc='-pythonpostjobcallback {}'.format(perframecallback),
                # atp='-attrprefix {}'.format(''),
                # uatp='-userattrprefix {}'.format(''),
                # u='-userattr {}'.format(''),
                rt='-root {}'.format(' -root '.join(roots)),
                ef='-eulerfilter',
                df='-dataformat {}'.format('ogawa'),
            ),
            'preRollStartFrame': float(int(startframe - preroll)),
            'dontSkipUnwrittenFrames': True,
        }

        self.time = time.time()
        cmds.AbcExport(**kwargs)

        # Teardown:
        for root in roots:
            cmds.delete(root)
