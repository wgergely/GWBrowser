Setup
=====

The ``Maya Browser`` plug-in is used to set the working project and importing, opening, referencing, and annotating projects and scenes with notes and thumbnails.
Once installed and loaded, the browser window can be found in Maya's 'File' menu.

The application-wide shortcut to show the panel is ``Ctrl + Shift + O``.

---------------------
Installing the plugin
---------------------

Place ``mayaBrowserPlugin.py`` into one of the Maya plug-in directories. The list of plug-in directories can be retrieved by running the following in the Maya Script Editor:

.. code-block:: python
    :linenos:

    import os
    for path in os.environ['MAYA_PLUG_IN_PATH'].split(';'):
        print path


The default (windows) user plug-in folders are:

``C:/Users/[user name]/Documents/maya/[version]/plug-ins`` and ``C:/Users/[user name]/Documents/maya/plug-ins``

These directories might not exists by default so make sure to create them if needed.

-----------------------------
Installing the browser module
-----------------------------

Before loading the plug-in, make sure the Browser module folder is placed into one of the python script directories. You can list these by running in the Maya script editor the following code:

.. code-block:: python
    :linenos:

    import sys
    for path in sys.path:
        print path

...The default user script paths are:

``C:/Users/[user name]/Documents/maya/[version]/scripts`` and ``C:/Users/[user name]/Documents/maya/scripts``

To test your installation, try importing Browser in the Maya Script Editor. After running code, and if all went well, you shouldn't get any error messages.

.. code-block:: python
    :linenos:

    import browser

Finally, you have to load the plug-in via the `Plug-in Manager`, where the plug-in should be listed as `mayaBrowserPlugin.py`.
Check ``load`` and ``auto-load``.
