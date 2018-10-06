# Browser: Maya Plug-In

This plug-in is a Maya front-end to Browser, a custom PyQt pipeline package.
Please note, this is a development release, and I can take no warranty for any of the functionality.

## Description
The plug-in is responsible for setting Maya projects and importing, opening, referencing,
and annotating projects and scenes.  
Once installed and loaded, the browser window can be found in Maya's 'File'
menu.  
The application-wide shortcut to show the panel is 'Ctrl + Shift + O'.

##  Plug-in Installation

Place `mayaBrowserPlugin.py` into one of the Maya plug-in directories.
The list of plug-in directories can be retrieved by running the following in
the Maya Script Editor:

```python
import os
for path in os.environ['MAYA_PLUG_IN_PATH'].split(';'):
    print path
```

By default, on windows, the default user plug-in paths are `C:/Users/[user name]/Documents/maya/[version]/plug-ins` and  `C:/Users/[user name]/Documents/maya/plug-ins`

Sometimes, these directories don't exists so make sure you create them if so.
Finally, you have to load the plug-in via the *Plug-in Manager*, it should be listed as `mayaBrowserPlugin.py`.

## Python package installation
Before loading the plug-in make sure the main 'Browser' module location is either added to the python path or placed in one of the python script directories. You can get them by running:

```python
import sys
for path in sys.path:
    print path
```

By default, on windows, the default user script paths are `C:/Users/[user name]/Documents/maya/[version]/scripts` and  `C:/Users/[user name]/Documents/maya/scripts`

After copying, you can test by your setup by trying to import `browser`
to Maya. Run this in the Maya Script Editor:

```python
import browser
```

If you get any error messages something went south, no message is good.

## Credits
Gergely Wootsch, 2018.  
hello@gergely-wootsch.com  
http://gergely-wootsch.com
