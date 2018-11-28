"""This module defines the UI terminology used throughout the application.

It is important to define elements clearly so they're are easy to understand
in the global production context.

Names should also be short and easy to understand and should not refer to
techincal jargon.
"""


LOCATION = 'project'
"""A path to a shared network folder where a sequence of projects are located.
This can be a series of assets, or a list of shots, or private sandboxes.

Example:
    //server/job/shots
    //server/job/assets
    //server/job/sequences/seq_010
    //server/job/sandbox
"""

PROJECT = 'asset'
"""Refers to a folder structure where scene and render-files are stored.
A project can be anything but generally is a shared-asset, or a shot.

Example:
    //server/job/shots/sh_010
    //server/job/assets/king_arthur
    //server/job/sequences/seq_010/sh_010
    //server/job/sandbox/carlos
"""


TASK = 'task'
"""A task is a subfolder used to categorize and filter scene files.

Example:
    //server/job/shots/sh_010/scenes/layout
    //server/job/shots/sh_010/scenes/render
    //server/job/shots/sh_010/scenes/animation
"""

FILE = 'scene'
"""A scene file """
