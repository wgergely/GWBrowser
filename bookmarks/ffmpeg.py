# -*- coding: utf-8 -*-
"""Common FFMpeg functionality."""

import os
from datetime import datetime
import subprocess
import _scandir

from PySide2 import QtCore, QtWidgets
import bookmarks.log as log
import bookmarks.common as common
import bookmarks.common_ui as common_ui
import bookmarks.settings as settings
import bookmarks.bookmark_db as bookmark_db


IMAGESEQ_TO_H264 = '"{BIN}" -y -hwaccel auto -framerate {FRAMERATE} -start_number {STARTFRAME} -i "{INPUT}" -vf "pad=ceil(iw/2)*2:ceil(ih/2)*2, drawtext=fontfile={FONT}: text=\'{LABEL} %{{frame_num}}\': start_number={STARTFRAME}: x=10: y=h-lh-10: fontcolor=white: fontsize=ceil(h/40): box=1: boxcolor=black: boxborderw=10" -c:v libx264 -preset slow -b:v 9500K -x264-params "colormatrix=bt709" -pix_fmt yuv420p -colorspace bt709 -color_primaries bt709 -color_trc gamma22 -map 0:v:0? -map_chapters 0 -c:s mov_text -map 0:s? -an -map_metadata 0 -f mp4 -threads 0 -movflags +faststart "{OUTPUT}"'


def get_font_path(name='bmRobotoMedium'):
    """The font used to label the generated files."""
    font_file = __file__ + os.path.sep + os.path.pardir + os.path.sep + 'rsc' + os.path.sep + 'fonts' + os.path.sep + '{}.ttf'.format(name)
    font_file = os.path.abspath(os.path.normpath(font_file))
    return font_file.replace(u'\\', u'/').replace(u':', u'\\\\:') # needed for ffmpeg


def launch_ffmpeg_command(input, preset, server=None, job=None, root=None, asset=None, task_folder=None):
    """Calls FFMpeg to process an input using the given preset.

    """
    w = common_ui.MessageBox(u'Converting...', u'Should take a few minutes...')
    try:
        FFMPEG_BIN = settings.local_settings.value(u'preferences/ffmpeg_path')
        if not FFMPEG_BIN:
            raise RuntimeError(
                u'The path to FFMpeg has not yet been set.\nYou can set the path in the General > External Applications section.')
        if not QtCore.QFileInfo(FFMPEG_BIN):
            raise RuntimeError('FFMpeg was not found!')

        server = server if server else settings.ACTIVE['server']
        job = job if job else settings.ACTIVE['job']
        root = root if root else settings.ACTIVE['root']
        asset = asset if asset else settings.ACTIVE['asset']
        task_folder = task_folder if task_folder else settings.ACTIVE['task_folder']

        input = input.replace(u'\\', '/').lower()

        # We want to get the first item  of any sequence
        if common.is_collapsed(input):
            input = common.get_sequence_startpath(input)
        else:
            seq = common.get_sequence(input)
            if not seq:
                raise RuntimeError(u'{} is not a sequence.'.format(input))
            _dir = QtCore.QFileInfo(input).dir().path()
            if not QtCore.QFileInfo(_dir):
                raise RuntimeError(u'{} does not exists.'.format(_dir))

            f = []
            for entry in _scandir.scandir(_dir):
                _path = entry.path.replace(u'\\', u'/').lower()
                if not seq.group(1) in _path:
                    continue
                _seq = common.get_sequence(_path)
                if not _seq:
                    continue
                f.append(int(_seq.group(2)))
            if not f:
                raise RuntimeError(u'Could not find the first frame of the sequence.')

        startframe = min(f)
        endframe = max(f)

        # Framerate
        db = bookmark_db.get_db(
            server,
            job,
            root
        )
        framerate = db.value(1, 'framerate', table=u'properties')
        if not framerate:
            framerate = 24

        input = seq.group(1) + '%0{}d'.format(len(seq.group(2))) + seq.group(3) + '.' + seq.group(4)
        output = seq.group(1).rstrip(u'.').rstrip(u'_').rstrip() + u'.mp4'

        # Add informative label
        label = u''
        if job:
            label += job
            label += u'_'
        if asset:
            label += asset
            label += u'_'
        if task_folder:
            label += task_folder
            label += u' \\| '
        vseq = common.get_sequence(output)
        if vseq:
            label +='v' + vseq.group(2) + u' '
            label += datetime.now().strftime('(%a %d/%m/%Y) \\| ')
        label += u'{}-{} \\| '.format(startframe, endframe)

        w.open()
        QtWidgets.QApplication.instance().processEvents()

        cmd = preset.format(
            BIN=FFMPEG_BIN,
            FRAMERATE=framerate,
            STARTFRAME=startframe,
            INPUT=os.path.normpath(input),
            OUTPUT=os.path.normpath(output),
            FONT=get_font_path(),
            LABEL=label,
        )
        subprocess.check_output(cmd, shell=True)

        w.close()
        log.success('Successfully saved {}'.format(output))
        common_ui.OkBox(u'Finished converting', 'Saved to {}'.format(output)).open()
    except Exception as e:
        w.close()
        log.error(u'Conversion failed.')
        common_ui.ErrorBox(u'Conversion failed', unicode(e)).open()

# launch_ffmpeg_command(
#     ur'\\aka03\pjct01\frills\data\shot\060_0030\captures\latest\060_0030_capture_1056.png',
#     IMAGESEQ_TO_H264
# )
