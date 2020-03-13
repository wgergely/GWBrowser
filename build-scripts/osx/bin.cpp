#include <stdio.h>
#include <iostream>
#include <Python.h>
#include <string.h>
#include <cstdlib>
#include <CoreFoundation/CoreFoundation.h>

using std::string;

int main(int argc, char** argv) {
  std::string cmd = "import bookmarks; bookmarks.exec_(); exit(0);";
  Py_SetProgramName(argv[0]);
  PyEval_InitThreads();
  Py_Initialize();
  PySys_SetArgv(argc, argv);
  int res = PyRun_SimpleString(cmd.c_str());
  if (res == -1) {
		Py_Finalize();

    CFOptionFlags nRet;
    SInt32 nRes = CFUserNotificationDisplayAlert(
      0,
      kCFUserNotificationStopAlertLevel,
      NULL, NULL, NULL,
      CFSTR("Error"),
      CFSTR("Could not start the application.\nAn internal Python error occured."),
      CFSTR("OK"), NULL, NULL, &nRet
    );
		exit(1);
	}
	Py_Finalize();
	exit(0);
}
