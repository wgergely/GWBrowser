"""Run "python setup.py install" to install scandir."""

try:
    from setuptools import setup, Extension
    from setuptools.command.build_ext import build_ext as base_build_ext
except ImportError:
    import warnings
    import sys
    val = sys.exc_info()[1]

    warnings.warn("import of setuptools failed %r" % val)
    from distutils.core import setup, Extension
    from distutils.command.build_ext import build_ext as base_build_ext

import os
import re
import sys
import logging


class BuildExt(base_build_ext):

    # the extension is optional since in case of lack of c the api
    # there is a ctypes fallback and a slow python fallback

    def build_extension(self, ext):
        try:
            base_build_ext.build_extension(self, ext)
        except Exception:
            exception = sys.exc_info()[0]
            logging.warn("building the %s failed with %s", ext.name, exception)

ext_scandir = Extension('_scandir', ['_scandir.c'])


setup(
    name='scandir',
    version='1.10.0',
    author='Ben Hoyt',
    author_email='benhoyt@gmail.com',
    url='https://github.com/benhoyt/scandir',
    license='New BSD License',
    description='scandir, a better directory iterator and faster os.walk()',
    long_description='',
    py_modules=['scandir'],
    ext_modules=[ext_scandir],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Topic :: System :: Filesystems',
        'Topic :: System :: Operating System',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: CPython',
    ], cmdclass={'build_ext': BuildExt},
)
