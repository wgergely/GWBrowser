import maya.cmds as cmds
import gwbrowser.common as common
import subprocess
from PySide2 import QtCore
import gwbrowser.context._mCapture as mCapture


@QtCore.Slot()
def capture_viewport():
    """
    Capture Viewport - Gergely Wootsch, Glassworks (c) 2019

    A capture script script to save a versioned capture to ``capture_folder``.
    The script will output to the an image sequence that is converted to a h264 using FFMpeg.
    It will also create a ``latest`` folder with a copy of the last exported image sequence.

    Usage:

        .. code-block:: python

        MayaBrowserWidget.capture_viewport()


    """
    file_format = u'png'

    DisplayOptions = {
        "displayGradient": True,
        "background": (0.5, 0.5, 0.5),
        "backgroundTop": (0.6, 0.6, 0.6),
        "backgroundBottom": (0.4, 0.4, 0.4),
    }

    capture_folder = get_preference(u'capture_path')
    capture_folder = capture_folder if capture_folder else common.CAPTURE_PATH

    workspace = cmds.workspace(q=True, rootDirectory=True).rstrip(u'/')
    file_info = QtCore.QFileInfo(cmds.file(q=True, expandName=True))
    complete_filename = u'{workspace}/{capture_folder}/{scene}/{scene}'.format(
        workspace=workspace,
        capture_folder=capture_folder,
        scene=file_info.baseName()
    )

    _dir = QtCore.QFileInfo(complete_filename).dir()
    if not _dir.exists():
        _dir.mkpath('.')

    panel = cmds.getPanel(withFocus=True)
    camera = cmds.modelPanel(panel, query=True, camera=True)
    options = mCapture.parse_view(panel)
    mCapture.capture(
        camera=camera,
        display_options=DisplayOptions,
        camera_options=options['camera_options'],
        viewport2_options=options['viewport2_options'],
        viewport_options=options['viewport_options'],
        format=u'image',
        compression=file_format,
        filename=complete_filename,
        overwrite=True,
        viewer=False
    )

    asset = workspace.split(u'/').pop()
    start = cmds.playbackOptions(q=True, animationStartTime=True)
    end = cmds.playbackOptions(q=True, animationEndTime=True)
    duration = (end - start) + 1

    # Publish master
    master_dir_path = u'{workspace}/{capture_folder}/latest'.format(
        workspace=workspace,
        capture_folder=capture_folder,
        asset=asset,
    )
    _dir = QtCore.QDir(master_dir_path)
    if not _dir.exists():
        _dir.mkpath('.')

    for n in xrange(int(duration)):
        versioned_path = u'{workspace}/{capture_folder}/{scene}/{scene}.{n}.{ext}'.format(
            workspace=workspace,
            capture_folder=capture_folder,
            scene=file_info.baseName(),
            n=str(n + int(start)).zfill(4),
            ext=file_format
        )
        master_path = u'{workspace}/{capture_folder}/latest/{asset}_capture_{n}.{ext}'.format(
            workspace=workspace,
            capture_folder=capture_folder,
            asset=asset,
            n=str(n + int(start)).zfill(4),
            ext=file_format
        )
        master_file = QtCore.QFile(master_path)
        if master_file.exists():
            master_file.remove()

        if QtCore.QFile.copy(versioned_path, master_path):
            u'# Copied: {}'.format(master_file.fileName())
        else:
            print u'# [Error]: {}'.format(master_file.fileName())


    # FFMPEG
    ffmpeg_bin_path = get_preference(u'ffmpeg_path')
    ffmpeg_bin_path = ffmpeg_bin_path if ffmpeg_bin_path else None
    if not ffmpeg_bin_path:
        return
    ffmpeg_info = QtCore.QFileInfo(ffmpeg_bin_path)
    if not ffmpeg_info.exists():
        return

    ffmpeg_in_path = u'{workspace}/{capture_folder}/{scene}/{scene}.%4d.{ext}'.format(
        workspace=workspace,
        capture_folder=capture_folder,
        scene=file_info.baseName(),
        ext=file_format
    )
    ffmpeg_out_path = u'{workspace}/{capture_folder}/{scene}.mov'.format(
        workspace=workspace,
        capture_folder=capture_folder,
        scene=file_info.baseName(),
        ext=file_format
    )
    ffmpeg_command = get_preference(u'ffmpeg_command')
    ffmpeg_command = ffmpeg_command if ffmpeg_command else common.FFMPEG_COMMAND
    args = ffmpeg_command.format(
        source=ffmpeg_in_path,
        framerate=24,
        start=int(cmds.playbackOptions(q=True, animationStartTime=True)),
        dest=ffmpeg_out_path
    )

    cmd = u'{} {}'.format(ffmpeg_bin_path, args)
    subprocess.Popen(cmd)
