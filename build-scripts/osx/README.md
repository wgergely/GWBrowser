<p align="center">
  <img src="./../../bookmarks/rsc/icon_bw.png" height=128px/>
</p>

# Bookmarks MacOSX Package

Use the utility scripts in this directory to build the standalone package for Bookmarks.

### make-libraries.sh

This script should give a good idea of the dependencies required. It will try, mostly using `brew`, to build all required dynamic and python libraries.

### make-package.sh

After building the dependencies make-package.sh will extract and package everything into an _app_ boundle, ready for distributing.

It will call `make-bin.sh` to build the binary wrapper for the python library exec_() call, and dislocate the dynamic libraries from the system using `install_name_tool`
