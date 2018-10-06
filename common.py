# -*- coding: utf-8 -*-
"""Common classes, settings and methods."""

import os
from PySide2 import QtGui

# pylint: disable=E1101, C0103, R0913, I1101, R0903


MARGIN = 6
ROW_HEIGHT = 54
WIDTH = 360

FAVORUITE_SELECTED = QtGui.QColor(250, 250, 100)
FAVORUITE = QtGui.QColor(235, 235, 68)

BACKGROUND_SELECTED = QtGui.QColor(100, 100, 100)
SECONDARY_BACKGROUND = QtGui.QColor(80, 80, 80)
BACKGROUND = QtGui.QColor(68, 68, 68)

THUMBNAIL_BACKGROUND_SELECTED = QtGui.QColor(100, 100, 100)
THUMBNAIL_BACKGROUND = QtGui.QColor(90, 90, 90)

TEXT_SELECTED = QtGui.QColor(255, 255, 255)
TEXT = QtGui.QColor(230, 230, 230)
# TEXT_NOTE = QtGui.QColor(180, 180, 240)
SECONDARY_TEXT = QtGui.QColor(170, 170, 170)
TEXT_NOTE = QtGui.QColor(200, 200, 200)

SEPARATOR = QtGui.QColor(58, 58, 58)
SELECTION = QtGui.QColor(87, 163, 202)
ARCHIVED_OVERLAY = QtGui.QColor(68, 68, 68, 150)

LABEL1_SELECTED = QtGui.QColor(102, 173, 125)
LABEL1 = QtGui.QColor(82, 153, 105)
LABEL1_TEXT = QtGui.QColor(162, 233, 185)


# Label colors
ASSIGNED_LABELS = {}
# Thumbnail cache
IMAGE_CACHE = {}

def label_generator():
    """Generates QColors from an array of RGB values.

    Example:

    .. code-block:: python
        :linenos:

        colors = label_generator()
        next(colors)

    Yields:         QtCore.QColor

    """
    colors = (
        [115, 163, 131],
        [151, 112, 160],
        [160, 112, 136],
        [120, 112, 160],
        [113, 134, 161],
        [160, 112, 112],
        [114, 162, 160],
        [145, 160, 112],
        [112, 160, 112],
        [160, 141, 112],
    )
    for color in colors:
        yield QtGui.QColor(*color)


colors = label_generator()


def get_label(k):
    """Returns the QColor for the given key.

    Args:
        k (str):    The key, eg. the name of a folder.

    Raises:         StopIterationrError: When out of labels.
    Returns:        QColor.

    """
    if k not in ASSIGNED_LABELS:
        ASSIGNED_LABELS[k] = next(colors)
    return ASSIGNED_LABELS[k]


def revert_labels():
    ASSIGNED_LABELS = {}

    global colors
    colors = label_generator()


def _custom_thumbnail():
    """The path to the custom thumbnail."""
    return os.path.join(
        __file__,
        os.pardir,
        'thumbnails/custom_thumbnail.png'
    )

def _maya_thumbnail():
    """The path to the custom thumbnail."""
    return os.path.join(
        __file__,
        os.pardir,
        'thumbnails/maya.png'
    )


CUSTOM_THUMBNAIL = _custom_thumbnail()
MAYA_THUMBNAIL = _maya_thumbnail()


class LocalContext(object):
    """Calls to the unavailable methods are directed here when not loading from Maya."""

    def __init__(self, *args, **kwargs):
        super(LocalContext, self).__init__()
        self.args = args
        self.kwargs = kwargs

    def workspace(self, *args, **kwargs):
        return None

    def file(self, *args, **kwargs):
        return None


try:
    import maya.cmds as cmds  # pylint: disable=E0401
    import maya.OpenMayaUI as OpenMayaUI  # pylint: disable=E0401
    from maya.app.general.mayaMixin import MayaQWidgetDockableMixin  # pylint: disable=E0401
    import shiboken2  # pylint: disable=E0401
except ImportError:
    cmds = LocalContext()
    OpenMayaUI = LocalContext()
    MayaQWidgetDockableMixin = LocalContext
    shiboken2 = LocalContext()
