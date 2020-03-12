@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall.bat" x64

set ROOT=I:\dev
cd /d %~dp0

SET DISTUTILS_USE_SDK=1
SET MSSdk=1

C:\python27\python.exe setup.py build_ext^
 --inplace^
 --compiler=msvc^
 -L"%ROOT%\vcpkg\installed\x64-windows\bin"^
 -I"%ROOT%\vcpkg\installed\x64-windows\include"

copy /Y "%~dp0\_scandir.pyd" "C:\Python27\Lib\site-packages\_scandir.pyd"
