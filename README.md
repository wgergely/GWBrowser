# Bookmarks
![alt text][logo]

![alt text](https://img.shields.io/badge/Python-2.7-lightgrey.svg "Python 2.7") ![alt text](https://img.shields.io/badge/Qt-5.6%2B-lightgrey.svg "Qt 5.6+") ![alt text](https://img.shields.io/badge/platform-windows%20%7C%20osx-lightgray.svg "Windows & Mac OS X")

***

### A file and asset manager for animation and CG productions.

### Use Bookmarks to see an overview of shots, files, custom notes and thumbnails. Use it to [create jobs](#first-run), assets or [browse existing content](#content-structure). Share paths with Slack and preview footage with Shotgun RV.

***



[link text itself]: http://www.reddit.com

### [Get the latest release.](https://github.com/wgergely/bookmarks/releases)

***

![alt text](./bookmarks/rsc/docs/tabs.gif "Content is categorised into Bookmarks, assets and files")

## Features

<img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/folder.png" height=20>Create jobs and assets using custom folder templates
<br>
<img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/todo.png" height=20>Annotate items using thumbnails, TODOs, tags and descriptions
<br>
<img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/archived.png" height=20>Archive superflous items without touching underlying files
<br>
<img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/active.png" height=20>Preview easily most image formats and Alembic archives
<br>
<img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/folder.png" height=20>Reveal files in Finder / Explorer
<br>
<img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/rv.png" height=20>Push footage to **Shotgun RV** from within Bookmarks
<br>
<img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/slack_color.png" height=20>[Send file paths and messages directly with **Slack**](#slack)
<br>
<img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/maya.png" height=20>[Dedicated Maya plugin](#bookmarks-maya-plugin)

![alt text](./bookmarks/rsc/docs/adding_thumbnails_and_descriptions_8fps.gif "Adding thumbnails and descriptions is easy...")

***




# ![alt text][maya] Maya Plugin

![alt text](./bookmarks/rsc/docs/maya_saver.jpg "And so is adding descriptions")

Bookmarks replaces Maya's Set Project and uses assets to set the current
workspace. Use Bookmarks to import/export scenes and to apply frame rate, range
and resolution settings. Use the custom file saver to save named scenes based on
the current bookmark, asset and mode selections.


***

## Content Structure


Content is organised into three separate sections: `Bookmarks`, `Assets` & `Files`.


| Overview  | ![alt text](./bookmarks/rsc/docs/bookmark_graph.jpg "Content structure")  |
|---|---|
| Bookmarks | Bookmarks are folders in your job folder and the main container for CG content. Each bookmark has frame rate, resolution, default frame-range, and a Slack token.|
| Assets  | Assets are Maya/Houdini workspace-like folder-structures. Each contains a series of task folders (scene, render, folders). Any folder can be an asset, and any folder containing an asset identifier file (eg. workspace.mel) will be recognized as an asset automatically. |
| Files  | Files are stored inside task folders. When browsing, Bookmarks reads all files inside a selected task folder, including files in subdirectories. You can use the provided search and filter tools to locate and save items.  |

> Parsing the whole task folder does come with a performance trade-off as files must be loaded upfront. Up to a few hundred thousand files this should not take too long, but a much depends on network access and hard-drive speeds.

***

## ![alt text][slack] Slack

To send messages using Slack, you must configure a bookmark with a valid Slack OAuth token.  The tokens are generated automatically when you install a new app to your Slack Workspace. [See guides on Slack](https://api.slack.com/apps) on how to add a new app and make sure to enable the following scopes:

> | OAuth Scopes |`channels:read`<br>`chat:write`<br> `chat:write.public`<br>`groups:read`<br>`users:read` |
|--|--|


***


## First Run

o start browsing, right-click anywhere on the main window and select Manage bookmarks. Here you can configure your servers, create new jobs and add bookmark folders.

![alt text](./bookmarks/rsc/docs/managing_bookmarks_6fps.gif "Managing bookmarks")

Use the ![alt text][add] icons to add a new server, job or bookmark. The job templates are simple zip files and you can add your own by dragging a zip file where the templates are listed. If the job template has bookmark folders they will be listed here automatically, otherwise, add one manually.

***

# Running the Python module


| Make sure first all python dependencies are installed: | `SlackClient`<br>`OpenImageIO`<br>`Alembic`<br>`PySide2 (Qt5.6+)`|
| -- | -- |

``` python

  # Starts Bookmarks as a standalone PySide2 app
  import bookmarks
  bookmarks.exec_()

```


``` python

  #  Show the Maya widget
  import bookmarks.maya.widget as widget
  widget.show()

  # NOTE: Bookmarks is meant to be used as a singleton,
  # and running multiple instances is a call for trouble.

```

> Bookmarks was written in Python 2 and built against the latest version of OpenImageIO and Qt5. There will be a Python 3 port in the future but as the latest version of Maya is still uses Python 2 there was no point of migrating just yet.


## Credits and Acknowledgments

(c) Gergely Wootsch, 2020.
<br>
[Email](mailto:hello@gergely-wootsch.com
)
<br>
[gergely-wootsch.com](http://gergely-wootsch.com)


[logo]: ./bookmarks/rsc/logo_s.png "Bookmarks: A simple file and asset manager for animation and CG productions"
[add]: ./bookmarks/rsc/add_button_s.png "Add button"
[maya]: ./bookmarks/rsc/maya.png "Add button"
[slack]: ./bookmarks/rsc/slack_color_sm.png "Add button"
