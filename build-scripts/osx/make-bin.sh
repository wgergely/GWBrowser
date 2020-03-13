PYTHON_ROOT=/usr/local/Cellar/python@2/2.7.17_1/Frameworks/Python.framework/Versions/2.7

clang \
-std=c++11 \
-stdlib=libc++ \
-I"$PYTHON_ROOT/include/python2.7/" \
-lc++ \
-lPython \
-framework CoreFoundation \
-L"$PYTHON_ROOT" \
-m64 \
-o ./bookmarks \
./bin.cpp

sudo install_name_tool \
-change \
/System/Library/Frameworks/Python.framework/Versions/2.7/Python \
@executable_path/lib/libpython2.7.dylib \
./bookmarks
