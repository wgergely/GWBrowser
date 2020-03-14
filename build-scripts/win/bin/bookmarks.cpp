/*
Application Launcher.
*/

#include <stdio.h>
#include <tchar.h>
#include <Windows.h>
#include <shlwapi.h>
#include <string>
#include <sys/types.h>
#include <sys/stat.h>
#include <Python.h>
#include <vector>
#include <sstream>

using std::wstring;
struct _stat64i32 info;

std::string WstrToUtf8Str(const std::wstring& wstr)
//https://stackoverflow.com/questions/21456926/how-do-i-convert-a-string-in-utf-16-to-utf-8-in-c
{
	std::string retStr;
	if (!wstr.empty())
	{
		int sizeRequired = WideCharToMultiByte(CP_UTF8, 0, wstr.c_str(), -1, NULL, 0, NULL, NULL);

		if (sizeRequired > 0)
		{
			std::vector<char> utf8String(sizeRequired);
			int bytesConverted = WideCharToMultiByte(CP_UTF8, 0, wstr.c_str(),
				-1, &utf8String[0], utf8String.size(), NULL,
				NULL);
			if (bytesConverted != 0)
			{
				retStr = &utf8String[0];
			}
			else
			{
				std::stringstream err;
				err << __FUNCTION__
					<< " std::string WstrToUtf8Str failed to convert wstring '"
					<< wstr.c_str() << L"'";
				throw std::runtime_error(err.str());
			}
		}
	}
	return retStr;
}




int main(int argc, char** argv)
{
	/* The DLLs are stored in "./bin/".
	Prior to calling python we'll add bin to the PATH env */
	wchar_t path[MAX_PATH + 1];
	if (!GetModuleFileNameW(NULL, path, MAX_PATH)) {
		MessageBox(NULL,
			_T("Could not start the application:\nGetModuleFileNameW returned a bogus value."),
			_T("Error"),
			MB_OK
		);
		exit(1);
	};

	if (!PathRemoveFileSpecW(path)) {
		MessageBox(NULL,
			_T("Could not start the application:\nPathRemoveFileSpecW returned a bogus value."),
			_T("Error"),
			MB_OK
		);
		exit(1);
	}

	// Let's check if the app's bin directory exists
	std::wstring bin_dir = wstring(path) + wstring(L"\\bin");

	if (_wstat(bin_dir.c_str(), &info) != 0)
	{
		MessageBox(NULL,
			_T("Could not start the application:\nThe 'bin' directory seems to be missing."),
			_T("Error"),
			MB_ICONERROR | MB_OK
		);
		exit(1);
	}

	if (!(info.st_mode & S_IFDIR))
	{
		MessageBox(NULL,
			_T("Could not start the application:\nThe 'bin' is not a valid directory."),
			_T("Error"),
			MB_ICONERROR | MB_OK
		);
		exit(1);
	}

	wchar_t* pathvar;
	size_t envsize = 0;
	_wgetenv_s(&envsize, NULL, 0, _T("PATH"));

	if (envsize == 0)
	{
		MessageBox(NULL,
			_T("Could not start the application.\nCould not get the PATH environment."),
			_T("Error"),
			MB_OK
		);
		exit(1);
	}

	// Allocating memory
	pathvar = (wchar_t*)malloc(envsize * sizeof(wchar_t));
	if (!pathvar)
	{
		MessageBox(NULL,
			_T("Could not start the application.\nCould not allocate memory."),
			_T("Error"),
			MB_OK
		);
		exit(1);
	}
	// Get the value of the PATH environment variable.
	_wgetenv_s(&envsize, pathvar, envsize, _T("PATH"));
	std::wstring modified_path = bin_dir + wstring(L";") + wstring(pathvar);
	_wputenv_s(modified_path.c_str(), L"PATH");


	// Let's check if the the python dll exists
	std::wstring pydll = wstring(path) + wstring(L"\\python27.dll");
	if (_wstat(pydll.c_str(), &info) != 0)
	{
		MessageBox(NULL,
			_T("Could not start the application:\nThe 'python27.dll' seems to be missing."),
			_T("Error"),
			MB_ICONERROR | MB_OK
		);
		exit(1);
	}

	std::wstring pythonpath = wstring(path) + wstring(L"\\shared");
	_wputenv_s(pythonpath.c_str(), L"PYTHONPATH");


	Py_SetProgramName(argv[0]);
	PyEval_InitThreads();
	Py_Initialize();
	PySys_SetArgv(argc, argv);

	std::wstring wcmd = L"\
import os;\
import sys;\
os.environ['PATH'] = r'" + modified_path + L"';\
sys.path.insert(0, r'" + wstring(path) + wstring(L"\\shared") + L"');\
import bookmarks; bookmarks.exec_();";

	std::string cmd = WstrToUtf8Str(wcmd);
	int res = PyRun_SimpleString(cmd.c_str());
	if (res == -1) {
		Py_Finalize();
		MessageBox(NULL,
			_T("Could not start the application.\nAn internal Python error occured."),
			_T("Error"),
			MB_OK
		);
		exit(1);
	}
	else
	{
		Py_Finalize();
		exit(0);
	}
}
