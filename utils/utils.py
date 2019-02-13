
import array
from contextlib import contextmanager

from PySide2 import QtWidgets, QtGui, QtCore

import browser.utils.OpenEXR as OpenEXR
import browser.utils.PIL.Image as Image
import browser.common as common


@contextmanager
def open_exr(s):
    exr = OpenEXR.InputFile(s)
    yield exr
    exr.close()


def encode_to_sRGB(v):
    if (v <= 0.0031308):
        return (v * 12.92) * 255.0
    else:
        return (1.055 * (v**(1.0 / 2.4)) - 0.055) * 255.0


def resize_Image(image, size):
    longer = float(max(image.size[0], image.size[1]))
    factor = float(float(size) / float(longer))
    if image.size[0] < image.size[1]:
        image = image.resize(
            (int(image.size[0] * factor), int(size)),
            Image.ANTIALIAS)
        return image
    image = image.resize(
        (int(size), int(image.size[1] * factor)),
        Image.ANTIALIAS)
    return image

def get_size(currentsize, size):
    longer = float(max(currentsize[0], currentsize[1]))
    factor = float(float(size) / float(longer))
    if currentsize[0] < currentsize[1]:
        return (int(currentsize[0] * factor), int(size))
    return (int(size), int(currentsize[1] * factor))


def ConvertEXRToJPG(exr_path, png_path):
    with open_exr(exr_path, ) as f:
        dw = f.header()['dataWindow']
        size = (dw.max.x - dw.min.x + 1, dw.max.y - dw.min.y + 1)

        data = f.channels('RGBA')
        Red = array.array('f', data[0])
        Green = array.array('f', data[1])
        Blue = array.array('f', data[2])
        Alpha = array.array('f', data[3])

        for I in range(len(Red)):
            Red[I] = encode_to_sRGB(Red[I])
        for I in range(len(Green)):
            Green[I] = encode_to_sRGB(Green[I])
        for I in range(len(Blue)):
            Blue[I] = encode_to_sRGB(Blue[I])
        for I in range(len(Alpha)):
            Alpha[I] = encode_to_sRGB(Alpha[I])

        rgbf = []
        rgbf.append(Image.frombytes('F', size, Red.tostring()))
        rgbf.append(Image.frombytes('F', size, Green.tostring()))
        rgbf.append(Image.frombytes('F', size, Blue.tostring()))
        rgbf.append(Image.frombytes('F', size, Alpha.tostring()))

        rgba8 = [im.convert('L') for im in rgbf]
        image = Image.merge('RGBA', rgba8)
        image = image.crop(image.getbbox())
        image = resize_Image(image, common.THUMBNAIL_IMAGE_SIZE)
        image.save(png_path, 'PNG')


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    path = r'\\gordo\jobs\audible_8100\films\vignettes\shots\AU_dragon_lady\renders\render\helmet_formado\helmet_formado_01\vignettes_AU_dragon_lady_fx_helmet_formado_01_0351.exr'
    ConvertEXRToJPG(path, 'C:/temp/temp2.png')
