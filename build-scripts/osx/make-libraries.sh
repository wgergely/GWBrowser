cd ~
mkdir ./code
cd ./code

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"

brew doctor
brew install https://raw.githubusercontent.com/Homebrew/homebrew-core/86a44a0a552c673a05f11018459c9f5faae3becc/Formula/python@2.rb
brew install
brew install boost
brew install boost-python
brew install autoconf
brew install automake
brew install libtool
brew install cmake
brew install glew
brew install hdf5

ln -s /usr/local/Cellar/boost-python/1.72.0/lib/libboost_python27.dylib /usr/local/lib/libboost_python.dylib
ln -s /usr/local/Cellar/boost-python/1.72.0/lib/libboost_python27.a /usr/local/lib/libboost_python.a
ln -s /usr/local/Cellar/boost-python/1.72.0/lib/libboost_python27-mt.dylib /usr/local/lib/libboost_python-mt.dylib
ln -s /usr/local/Cellar/boost-python/1.72.0/lib/libboost_python27-mt.a /usr/local/lib/libboost_python-mt.a

pip install --upgrade pip setuptools
pip install numpy

git clone https://github.com/openexr/openexr
cd openexr/IlmBase
./bootstrap
./configure
make; make install
cd ../PyIlmBase
./bootstrap
./configure
make; make install

cd ~/code
git clone https://github.com/alembic/alembic
cd ./alembic; mkdir ./build; cd ./build

cmake ../ \
-DUSE_PYALEMBIC=ON \
-DCMAKE_CXX_STANDARD=11 \
-DCXX_STANDARD=11 \
-DCMAKE_BUILD_TYPE=Release \
-DALEMBIC_LIB_USES_BOOST=ON \
-DPYTHON_EXECUTABLE=/usr/local/bin/python2 \
-DPYTHON_INCLUDE_DIR=/usr/local/Cellar/python@2/2.7.17_1/Frameworks/Python.framework/Versions/2.7/include/python2.7 \
-DPYTHON_LIBRARY=/usr/local/Cellar/python@2/2.7.17_1/Frameworks/Python.framework/Versions/2.7/lib/libpython2.7.dylib \
-DPYTHON_LIBRARY_DEBUG=/usr/local/Cellar/python@2/2.7.17_1/Frameworks/Python.framework/Versions/2.7/lib/libpython2.7.dylib
make; make install;


brew install ffmpeg
brew install freetype
brew install giflib
brew install jpeg
brew install jpeg-turbo
brew install libpng
brew install libraw
brew install libtiff
brew install opencolorio
brew install webp
brew install ptex
brew install opencv
brew install openvdb
brew install libheif
brew install pybind11
brew install libsquish

cd ~/code
git clone https://github.com/openimageio/oiio
cd ./oiio
mkdir ./build
cd ./build
cmake ../ \
-DPYTHON_EXECUTABLE=/usr/local/bin/python2 \
-DPYTHON_INCLUDE_DIR=/usr/local/Cellar/python@2/2.7.17_1/Frameworks/Python.framework/Versions/2.7/include/python2.7 \
-DPYTHON_LIBRARY=/usr/local/Cellar/python@2/2.7.17_1/Frameworks/Python.framework/Versions/2.7/lib/libpython2.7.dylib \
-DPYTHON_LIBRARY_DEBUG=/usr/local/Cellar/python@2/2.7.17_1/Frameworks/Python.framework/Versions/2.7/lib/libpython2.7.dylib \
-DUSE_QT=OFF \
-DUSE_PYTHON=ON

make; make install

brew install qt5
pip install pyside2
pip install psutil
pip install slackclient
