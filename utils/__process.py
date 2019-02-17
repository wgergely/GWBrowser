# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903, C0330

"""OpenImageIO thumbnail operations."""

import sys
from PySide2 import QtCore

import browser.common as common


def generate_thumbnail(source, dest):
    """A fast thumbnailer method using OpenImageIO."""
    import browser.modules.oiio.OpenImageIO as oiio
    from browser.modules.oiio.OpenImageIO import ImageBuf, ImageSpec, ImageBufAlgo

    img = ImageBuf(source)

    if img.has_error:
        sys.stderr.write('# OpenImageIO: Skipped reading {}\n{}\n'.format(source, img.geterror()))
        return

    size = int(common.THUMBNAIL_IMAGE_SIZE)
    spec = ImageSpec(size, size, 4, "uint8")
    spec.channelnames = ('R', 'G', 'B', 'A')
    spec.alpha_channel = 3
    spec.attribute('oiio:ColorSpace', 'Linear')
    b = ImageBuf(spec)
    b.set_write_format('uint8')

    oiio.set_roi_full(img.spec(), oiio.get_roi(img.spec()))
    ImageBufAlgo.fit(b, img)

    file_info = QtCore.QFileInfo(dest)
    if not file_info.dir().exists():
        QtCore.QDir().mkpath(file_info.path())

    b = ImageBufAlgo.flatten(b)

    spec = b.spec()
    if spec.get_string_attribute('oiio:ColorSpace') == 'Linear':
        roi = oiio.get_roi(b.spec())
        roi.chbegin = 0
        roi.chend = 3
        ImageBufAlgo.pow(b, b, 1.0/2.2, roi)

    if int(spec.nchannels) < 3:
        b = ImageBufAlgo.channels(
            b, (spec.channelnames[0], spec.channelnames[0], spec.channelnames[0]), ('R', 'G', 'B'))
    elif int(spec.nchannels) > 4:
        if spec.channelindex('A') > -1:
            b = ImageBufAlgo.channels(
                b, ('R', 'G', 'B', 'A'), ('R', 'G', 'B', 'A'))
        else:
            b = ImageBufAlgo.channels(b, ('R', 'G', 'B'), ('R', 'G', 'B'))

    if b.has_error:
        sys.stderr.write(
            '# OpenImageIO: Channel error {}.\n{}\n'.format(b.geterror()))

    if not b.write(dest, dtype='uint8'):
        sys.stderr.write('# OpenImageIO: Error saving {}.\n{}\n'.format(
            file_info.fileName(), b.geterror()))


dir_ = QtCore.QDir('C:/dev/oiio-images')
dir_.setFilter(QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)
dir_.setNameFilters(('*.exr',))
for entry in dir_.entryInfoList():
    source = entry.filePath()
    dest = '{}/__thumbnails/{}.png'.format(entry.path(),
                                           entry.completeBaseName())
    generate_thumbnail(source, dest)
