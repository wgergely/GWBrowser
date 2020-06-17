@echo off

call "C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall.bat" x64

REM Builds bookmarks.exe
REM Requires Visual Studio 2015 and Python 2.7

set PRODUCT=bookmarks
set PYTHON_INCLUDE="C:\Python27\Include"
set PYTHON_LIB="C:\Python27\libs\python27.lib"

REM Compile the cpp
cl /c /EHsc /nologo /GS /GL /W3 /Gy /Zc:wchar_t ^
/I%PYTHON_INCLUDE% ^
/Zi /Gm- /O2 /sdl ^
/Fd"%BUILD_DIR%\vc140.pdb" /Zc:inline /fp:precise ^
/D "NDEBUG" /D "_CONSOLE" /D "_UNICODE" /D "UNICODE" ^
/errorReport:prompt /WX- /Zc:forScope /Gd /Oi /MD ^
%PRODUCT%.cpp

REM Compile the resource file for showing the icon
rc bookmarks.rc
IF %ERRORLEVEL% NEQ 0 (
  EXIT 1
)

REM Build the Debug Exe
link ^
/OUT:"%PRODUCT%_d.exe" ^
/MANIFEST /LTCG:incremental /NXCOMPAT ^
/DYNAMICBASE "%PYTHON_LIB%" "Shlwapi.lib" "kernel32.lib" "user32.lib" "gdi32.lib" "winspool.lib" "comdlg32.lib" "advapi32.lib" "shell32.lib" "ole32.lib" "oleaut32.lib" "uuid.lib" "odbc32.lib" "odbccp32.lib" ^
/DEBUG /MACHINE:X64 /OPT:REF /INCREMENTAL:NO ^
/SUBSYSTEM:CONSOLE /MANIFESTUAC:"level='asInvoker' uiAccess='false'" ^
/OPT:ICF /ERRORREPORT:PROMPT /NOLOGO /TLBID:1 ^
%PRODUCT%.obj %PRODUCT%.res

IF %ERRORLEVEL% NEQ 0 (
  EXIT 1
)

REM Build the Release Exe
link ^
/OUT:"%PRODUCT%.exe" ^
/MANIFEST /LTCG:incremental /NXCOMPAT ^
/DYNAMICBASE "%PYTHON_LIB%" "Shlwapi.lib" "kernel32.lib" "user32.lib" "gdi32.lib" "winspool.lib" "comdlg32.lib" "advapi32.lib" "shell32.lib" "ole32.lib" "oleaut32.lib" "uuid.lib" "odbc32.lib" "odbccp32.lib" ^
/DEBUG /MACHINE:X64 /OPT:REF /INCREMENTAL:NO ^
/SUBSYSTEM:CONSOLE /MANIFESTUAC:"level='asInvoker' uiAccess='false'" ^
/OPT:ICF /ERRORREPORT:PROMPT /NOLOGO /TLBID:1 ^
/SUBSYSTEM:windows /ENTRY:mainCRTStartup ^
%PRODUCT%.obj %PRODUCT%.res

IF %ERRORLEVEL% NEQ 0 (
  EXIT 1
)

del /q /f *.manifest
del /q /f *.iobj
del /q /f *.obj
del /q /f *.ipdb
del /q /f *.pdb
del /q /f *.res
EXIT 0
