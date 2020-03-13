# Bookmarks library packager.
#
# The script copies all the dependencies to needed to run Bookmarks to the $DEST
# folder. Starting from $TOPLIBS the script copies recursively all dependencies
# and changes the linking settings using install_name_tool
#

clear && printf "\x1B[3J"


PRODUCT=bookmarks
VERSION="0.3.0"
COPYRIGHT="(c) 2020 Gergely Wootsch"
DOMAIN="org.bookmarks.com"


LIB_SSL=/usr/local/Cellar/openssl@1.1/1.1.1d/lib/libssl.1.1.dylib
LIB_CRYPTO=/usr/local/Cellar/openssl@1.1/1.1.1d/lib/libcrypto.1.1.dylib
LIB_ALEMBIC=/usr/local/lib/python2.7/site-packages/alembic.so
LIB_ALEMBIC_D=/usr/local/lib/libAlembic.1.7.12.dylib
LIB_IEX=/usr/local/lib/python2.7/site-packages/iexmodule.so
LIB_IMATH=/usr/local/lib/python2.7/site-packages/imathmodule.so
LIB_OIIO=/usr/local/lib/python2.7/site-packages/OpenImageIO.so
LIB_OIIO_D=/usr/local/lib/libOpenImageIO.2.2.2.dylib
LIB_PYTHON=/usr/local/Cellar/python@2/2.7.17_1/Frameworks/Python.framework/Versions/2.7/Python
DIR_PYTHON=/usr/local/Cellar/python@2/2.7.17_1/Frameworks/Python.framework/Versions/2.7/lib/python2.7
PYTHON_BIN=/usr/local/Cellar/python@2/2.7.17_1/Frameworks/Python.framework/Versions/2.7/Resources/Python.app/Contents/MacOS/Python

TOPLIBS=(\
[0]=$LIB_OIIO \
[1]=$LIB_OIIO_D \
[2]=$LIB_ALEMBIC_D \
[3]=$LIB_ALEMBIC \
[5]=$LIB_IEX \
[6]=$LIB_IMATH \
[7]=$LIB_SSL \
[8]=$LIB_CRYPTO \
);

_ROOT=~/code
MODULE_ROOT=$_ROOT/bookmarks/bookmarks
ROOT=$_ROOT/$PRODUCT.app/Contents
RES=$ROOT/MacOS
DEST=$RES/lib

make_dirs() {
	mkdir "$_ROOT"
	mkdir "$_ROOT/$PRODUCT.app"
	mkdir "$_ROOT/$PRODUCT.app/Contents"
	# touch "$ROOT/Info.plist"
	mkdir "$ROOT/MacOS"
	mkdir "$ROOT/MacOS/lib"
	mkdir "$ROOT/Resources"


	{ cat << '***'; cat << EOF; } > "$ROOT/Info.plist"
***
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>English</string>
	<key>CFBundleExecutable</key>
	<string>$PRODUCT</string>
	<key>CFBundleGetInfoString</key>
	<string>$VERSION, $COPYRIGHT</string>
	<key>CFBundleIconFile</key>
	<string>icon.icns</string>
	<key>CFBundleIdentifier</key>
	<string>$DOMAIN</string>
	<key>CFBundleInfoDictionaryVersion</key>
	<string>6.0</string>
	<key>CFBundleLongVersionString</key>
	<string>$VERSION, $COPYRIGHT</string>
	<key>CFBundleName</key>
	<string>$PRODUCT</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleShortVersionString</key>
	<string>$VERSION</string>
	<key>CFBundleSignature</key>
	<string>$DOMAIN</string>
	<key>CFBundleVersion</key>
	<string>$VERSION</string>
	<key>NSHumanReadableCopyright</key>
	<string>$COPYRIGHT</string>
	<key>NSHighResolutionCapable</key>
	<true/>
</dict>
</plist>
EOF

	./make-bin.sh
	cp ./bookmarks "$ROOT/MacOS/bookmarks"
	cp ./../../bookmarks/rsc/icon.icns "$ROOT/Resources/icon.icns"
}


change_lib() {
	echo -e "\x1B[4;34m\n$name:\x1B[0m"
	name=$(basename "$1")
	dir=$(dirname "$1")
	otool -L $1 | grep -o -i -E "[\@\/].*?\s" | while read line;
	do
		name=$(basename "$line")
		case $line in */usr/lib*) continue;; esac
		case $line in */System/*) continue;; esac

		case $line in */Python*)
			name="libpython2.7.dylib";;
		esac

		echo -e "\x1B[39m$line\x1B[0m  ->  \x1B[32m@executable_path/lib/$name\x1B[0m"
		sudo install_name_tool -change $line "@executable_path/lib/$name" "$1"
		sudo install_name_tool -id @loader_path/$name "$1"
	done
}

otool_copy() {
	_name=$(basename "$1")
	if test -f "$DEST/$_name"; then
		:
	else
		if test -f "$1"; then
			cp "$1" "$DEST/$_name"
			EXITCODE=$?
			test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied "$1" \x1B[0m\n"
		else
			echo -e "\x1B[31m$1 does not exist\x1B[0m\n"
		fi
	fi

	otool -L "$1" | grep -o -i -E "[\@\/].*?\s" | while read line;
  do
		name=$(basename "$line")
		if test -f "$DEST/$name"; then
			continue;
		fi

		# Skip built-ins and relative references
    case "$line" in */usr/lib*) continue;; esac
		case "$line" in */System/*) continue;; esac
		case "$line" in *@*) continue;; esac

		otool_copy $line
		if test -f "$DEST/$_name"; then
			sudo install_name_tool -id "@loader_path/$name" "$DEST/$_name";

			if test -f "$DEST/$name"; then
				sudo install_name_tool -change $line @executable_path/lib/$name "$DEST/$_name";
			else
				echo -e "\x1B[31minstall_name_tool: $name does not exist \x1B[0m\n"

			fi
		else
				echo -e "\x1B[31minstall_name_tool: $DEST/$_name does not exist \x1B[0m\n"
		fi

	done
}


copy_python() {
	cp "$LIB_PYTHON" "$DEST/libpython2.7.dylib"
	EXITCODE=$?
	test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied $LIB_PYTHON \x1B[0m"

	cp -r "$DIR_PYTHON" "$DEST"
	test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied $DIR_PYTHON \x1B[0m"
	SITE_PACKAGES=$DEST/python2.7/site-packages

	rm -r "$SITE_PACKAGES"
	mkdir "$SITE_PACKAGES"

	cp -r "$DIR_PYTHON/site-packages/PySide2" "$SITE_PACKAGES/PySide2"
	test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied $SITE_PACKAGES/PySide2 \x1B[0"
	cp -r "$DIR_PYTHON/site-packages/shiboken2" "$SITE_PACKAGES/shiboken2"
	test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied $SITE_PACKAGES/shiboken2 \x1B[0m"
	cp -r "$DIR_PYTHON/site-packages/numpy" "$SITE_PACKAGES/numpy"
	test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied $SITE_PACKAGES/numpy \x1B[0m"
	cp -r "$DIR_PYTHON/site-packages/psutil" "$SITE_PACKAGES/psutil"
	test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied $SITE_PACKAGES/psutil \x1B[0m"
	cp -r "$DIR_PYTHON/site-packages/slackclient" "$SITE_PACKAGES/slackclient"
	test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied $SITE_PACKAGES/slackclient \x1B[0m"
	cp -r "$DIR_PYTHON/site-packages/requests" "$SITE_PACKAGES/requests"
	test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied $SITE_PACKAGES/requests \x1B[0m"
	cp -r "$DIR_PYTHON/site-packages/urllib3" "$SITE_PACKAGES/urllib3"
	test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied $SITE_PACKAGES/urllib3 \x1B[0m"
	cp -r "$DIR_PYTHON/site-packages/idna" "$SITE_PACKAGES/idna"
	test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied $SITE_PACKAGES/idna \x1B[0m"
	cp -r "$DIR_PYTHON/site-packages/chardet" "$SITE_PACKAGES/chardet"
	test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied $SITE_PACKAGES/chardet \x1B[0m"
	cp -r "$DIR_PYTHON/site-packages/certifi" "$SITE_PACKAGES/certifi"
	test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied $SITE_PACKAGES/certifi \x1B[0m"
	cp -r "$DIR_PYTHON/site-packages/websocket-client" "$SITE_PACKAGES/websocket-client"
	test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied $SITE_PACKAGES/websocket-client \x1B[0m"
	cp -r "$DIR_PYTHON/site-packages/websocket" "$SITE_PACKAGES/websocket"
	test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied $SITE_PACKAGES/websocket \x1B[0m"
	cp -r "$DIR_PYTHON/site-packages/six.py" "$SITE_PACKAGES/six.py"
	test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied $SITE_PACKAGES/six.py \x1B[0m"

	cp "$PYTHON_BIN" "$RES/Python"
	EXITCODE=$?
	test $EXITCODE -eq 0 && echo -e "\x1B[32mCopied $RES/Python \x1B[0m"
	otool -L "$RES/Python" | grep -o -i -E "[\@\/].*?\s" | while read line;
  do
		name=$(basename "$line")
		# Skip built-ins and relative references
    case "$line" in */usr/lib*) continue;; esac
		case "$line" in */System/*) continue;; esac
		echo "$line"
		sudo install_name_tool -change $line "@executable_path/lib/libpython2.7.dylib" "$RES/Python"
		sudo install_name_tool -id "@loader_path/lib/libpython2.7.dylib" "$RES/Python"
	done

	for i in $DEST/*.so;
	do
		mv "$i" "$SITE_PACKAGES/"
	done

	cp -r "$MODULE_ROOT" "$SITE_PACKAGES"
}

test_install() {
	"$RES/Python" -c "import imath; print 'imath -- \x1B[32mok\x1B[0m'"
	"$RES/Python" -c "import iex; print 'iex -- \x1B[32mok\x1B[0m'"
	"$RES/Python" -c "import alembic; print 'alembic -- \x1B[32mok\x1B[0m'"
	"$RES/Python" -c "import OpenImageIO; print 'OpenImageIO -- \x1B[32mok\x1B[0m'"
	"$RES/Python" -c "import bookmarks; print 'bookmarks -- \x1B[32mok\x1B[0m'"
	"$RES/Python" -c "import slackclient; print 'slackclient -- \x1B[32mok\x1B[0m'"
	"$RES/Python" -c "from PySide2 import QtCore, QtWidgets, QtGui; print 'PySide2 -- \x1B[32mok\x1B[0m'"
	"$RES/Python" $MODULE_ROOT/../test/test_application.py
}

# Create directory structure
make_dirs
for i in "${TOPLIBS[@]}"
do
	# Copy recursively all dependent libraries and change linking
	otool_copy $i
done

for i in $DEST/*;
do
	sudo chmod 777 "$i"
	change_lib $i
done

copy_python
test_install
