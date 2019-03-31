# GWBrowser - Install files

This folder contains the files necessary to install and run GWBrowser.

### Dependencies
`GWBrowser` was designed in-line with the current (as of writing this) [`VFX Reference Platform - CY2018`](https://www.vfxplatform.com/) specifications. This is a pure Python2 project but we rely on the Python port of [`OpenImageIO 2.0`](https://github.com/OpenImageIO), `Numpy` (a dependency of OpenImageIO) and [`PySide2`](https://doc.qt.io/qtforpython/index.html).

As per the specs, the Python version is 2.7 **but** on Windows Maya, Houdini and Nuke use Python 2.7 compiled Visual C++ 2015 (14.0) (MSV1900). The standard Python 2.7 version was compiled with MSV1500.

The `OpenImageIO` and `Numpy` versions included here were also compiled using MSV1900.
The Numpy build was kindly provided by [Eric Vignola](https://github.com/Eric-Vignola).
OpenImageIO 2 was built by me using Microsoft's vcpkg (the build project is not included).

### PySide2

The current version was tested against `PySide2` (`v5.6`) as specified by the [VFX Reference Platform - CY2018](https://www.vfxplatform.com/). This is the last version compatible with Python 2. The wheel included here is a copy of the official version available at the official Qt5 website.

### Building the dependencies

It took me a while to figure out how to get all the dependencies but luckily there's help out there. The build projects are not included in the repo but using Microsoft's `VCPKG` things get a little easier. It is relatively easily to build Python 2.7 if the right version of Visual Studio is installed, as is `OpenImageIO 2`, but  `Numpy` and `PySide2` wheels are pre-built packages. Building OpenImageIO was especially problematic as there's a lot of patching involved...

# Installation

I decided not to include the actual python environment but installing `python2.7.11_amd64_MSCv1900` and populating it with the `numpy-1.13.1+mkl-cp27-none-win_amd64.whl`, `OpenImageIO_pkg-2.0.0-cp27-cp27m-win_amd64.whl`, `PySide2-5.6.0a1.dev1528216830-5.6.4-cp27-cp27m-win_amd64.whl` will set up all the dependencies up.

The project itself is contained in the `gwbrowser_pkg-x.x.x-py2-none-any.whl` wheel file.
