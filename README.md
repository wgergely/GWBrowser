<center>

![alt text][logo]

## Bookmarks<br>_A simple asset manager for VFX and animation jobs._

<br>

![alt text](https://img.shields.io/badge/Python-2.7-lightgrey.svg "Python 2.7") ![alt text](https://img.shields.io/badge/Qt-5.6%2B-lightgrey.svg "Qt 5.6+") ![alt text](https://img.shields.io/badge/platform-windows%20%7C%20osx-lightgray.svg "Windows & Mac OS X")

### [Get the latest release.](https://github.com/wgergely/bookmarks/releases)

</center>
<br>

Bookmarks provides a basic overview of your project's assets and files. Use it
to create new jobs, shots, or browse existing content. Share paths and notes
with your Slack-mates and preview renders with OpenImageIO and Shotgun RV, or
add versioned template files to manage file naming.

<center>
<img width="500px" alt="Bookmarks Asset Manager" src="./bookmarks/rsc/docs/tabs.gif">
</center>



# Introduction

<img align="right"  alt="Adding bookmarks and jobs" src="./bookmarks/rsc/docs/files1.jpg">

The project started life as a Maya script to change workspaces but since has
grown into a standalone, multi-threaded asset manager.

For Maya artists Bookmarks has tools to load and save scenes and caches (**hello
incremental save!**), preview/import images. Non-maya artists, and even small
and medium sized studios, could find themselves in need of a simple asset
manager where Shotgun (and the likes) are not required.

<img width="280px" alt="Adding bookmarks and jobs" src="./bookmarks/rsc/docs/maya_files.jpg"><br>

I use it to manage my own freelance projects because it lets me quickly
set up the folders needed to turn a small job around. It is also place where I
keep notes, feedback, google sheet urls. I tend to keep adding descriptions to
scenes as I increment versions know what was changed in each version.

## Let's Go!


To get started specify your servers and create a job if you don't have any.
Right-click anywhere inside the window and select `Manage bookmarks`.


<img align="right" width="360" alt="Adding bookmarks and jobs" src="./bookmarks/rsc/docs/managing_bookmarks_6fps.gif">

Use the ![alt text][add] icons to add a new server, job or bookmark. The job templates are simple zip files and you can add your own by dragging a zip to where the templates are listed. If the job template has bookmark folders they will be listed below automatically, otherwise, add a new one by hand.

## Bookmark, Asset and File Tabs

_Bookmarks_ are folders in your job folder and the main container for CG
content. Bookmarks have frame rate, resolution, default frame range, and a Slack
tokens. Each job can contain multiple bookmarks - eg. `shots`, `assets`, etc.

_Assets_ are Maya/Houdini workspace-like folder structures. Each contains a
series of task folders (eg. a _scene_, _render_, _cache_ folder). Any folder can
be an asset, and any folder containing an asset identifier file (eg.
workspace.mel) will be recognized as such automatically.

_Files_ are stored inside task folders. When browsing, Bookmarks reads all files
inside a selected _task folder_, including files in subdirectories. You can use
the provided search and filter tools to locate and save items. <a
href="./bookmarks/rsc/docs/bookmark_graph.jpg" target="_blank">See this folder
diagram for details</a>.


## Controling What You See

### Search filters

_**Search filters**_ can be used to include or exclude items based on their
description and file name. They are persistent and will stay on unless you
remove them. Click <img height="24px" alt="Search Filter button"
src="./bookmarks/rsc/filter.png"> or press `Ctrl+F` to edit. To show all chef
images type `chef` and press enter. To _exclude_ all chef images type `--chef`
(two dashes followed by a name).

<img alt="Search filter" src="./bookmarks/rsc/docs/search_filter.jpg"><br>


You can also click subfolder labels. To **isolate** elements
`Shift+Click`, to **hide** elements `Alt-Click` on the label.
To reset the search filter `Alt-Click` on the <img height="24px" alt="Search
Filter button" src="./bookmarks/rsc/filter.png"> search filter icon.

### Flags and thumbnails

Save items as a favourite - these items will be added to `My Files`.
You can also archive superflous items.

Use thumbnails to visually scout items. Bookmarks will generate a thumbnail for image files. Press `space` on your keyboard to preview the image (this also works for alembic archives!).


<img alt="Search filter" src="./bookmarks/rsc/docs/image_preview.jpg"><br>



## Maya


The maya plugin replaces the internal project manager and uses assets to set the
current workspace.


`Shift+RightClick` shows Maya specific actions.
`Ctrl+Shift+Alt+S` shows the file-saver.<br>
`Ctrls+Shift+Alt+B` will show/hide Bookmarks.

After installing bookmarks enable `mBookmarks.py` in Maya's plugin manager.

## ![alt text][slack] Slack

To send messages using Slack, you must configure a bookmark with a valid Slack OAuth token.  The tokens are generated automatically when you install a new app to your Slack Workspace. [See guides on Slack](https://api.slack.com/apps) on how to add a new app and make sure to enable the following scopes:


| OAuth Scopes |`channels:read`<br>`chat:write`<br> `chat:write.public`<br>`groups:read`<br>`users:read` |
|--|--|



## Running Bookmarks

Bookmarks has not yet been ported to Python 3 and currently requires Python 2.
Make sure all python dependencies are installed:

| Dependencies | `SlackClient`<br>`OpenImageIO`<br>`Alembic`<br>`PySide2`<br>`Numpy`<br>`psutil`|
| -- | -- |


Starts Bookmarks as a standalone PySide2 application:

``` python

  import bookmarks
  bookmarks.exec_()

```

Or inside Maya initialize the widget like this:

``` python

  import bookmarks.maya.widget as widget
  widget.show()

  # NOTE: Bookmarks is meant to be used as a singleton,
  # and running multiple instances is not allowed.

```


## Credits and Acknowledgments

(c) Gergely Wootsch, 2020.
<br>
[Email](mailto:hello@gergely-wootsch.com
)
<br>
[gergely-wootsch.com](http://gergely-wootsch.com)


[logo]: ./bookmarks/rsc/logo_s.png "Bookmarks: A simple file and asset manager for animation and CG productions"
[add]: ./bookmarks/rsc/add_button_s.png "Add button"
[maya]: ./bookmarks/rsc/maya.png "Maya button"
[slack]: ./bookmarks/rsc/slack_color_sm.png "Slack button"
[filter]: ./bookmarks/rsc/filter.png "Filter button"
