# -*- coding: utf-8 -*-
# pylint: disable=E1101, C0103, R0913, I1101, R0903, C0330

"""__init__ responsible for making the package's modules folder available
for the os.env and sys.path."""

import sys
import os
import browser

module_root ='{file}{sep}{parent}{sep}modules'.format(
    file=browser.__file__,
    sep=os.path.sep,
    parent=os.pardir
)

# Modules
module_root = os.path.abspath(module_root)
sys.path.insert(0, module_root)
path = '{}{}bin'.format(module_root, os.path.sep)
os.environ['PATH'] = '{};{}'.format(path, os.environ['PATH'])

# OpenImageIO libs
path = '{}{}oiio'.format(module_root, os.path.sep)
os.environ['PATH'] = '{};{}'.format(path, os.environ['PATH'])
