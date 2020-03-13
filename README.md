<p align="center">

</p>

<center>
  <img src="./bookmarks/rsc/icon.png" alt="Bookmarks" height=128/>
  <h1>Bookmarks</h1>
  <h4>A simple shot manager for CG productions</h4><br>

  <p align="center">
    <a href="http://gergely-wootsch.com">
        <img src="https://img.shields.io/badge/Python-2.7-lightgrey.svg" alt="Python version">
    </a>
    <a href="http://gergely-wootsch.com">
        <img src="https://img.shields.io/badge/Qt-5.6%2B-lightgrey.svg" alt="PySide2 / Qt5">
    </a>
    <a href="http://gergely-wootsch.com">
        <img src="https://img.shields.io/badge/platform-windows%20%7C%20osx-lightgray.svg" alt="PySide2 / Qt5">
    </a>
  </p>
</center>

* * *

<!-- straighforward uncomplicated clear smooth manageble -->

<h6>

-   <img src="./bookmarks/rsc/icon.png" height=24> Run on Mac OS X or Windows 7
-   <img src="./bookmarks/rsc/todo.png" height=24> Annotate with ToDos, tags and descriptions
-   <img src="./bookmarks/rsc/archived.png" height=24> Archive superflous assets and files non-destructively
-   <img src="./bookmarks/rsc/active.png" height=24> Preview images of most media formats (using OpenImageIO)
-   <img src="./bookmarks/rsc/folder.png" height=24> Quick access to the file-system and file paths
-   <img src="./bookmarks/rsc/rv.png" height=24> Push footage to `Shotgun RV` directly from Bookmarks
-   <img src="./bookmarks/rsc/slack_color.png" height=24> Send messegases to `Slack`
-   <img src="./bookmarks/rsc/maya.png" height=24> Maya plugin (see below)
-   <img src="./bookmarks/rsc/icon.png" height=24> Bookmarks is written in Python, hence can be integrated with most _Qt for Python_ capable DCCs
-   <img src="./bookmarks/rsc/icon_bw.png" height=24> and more...!

</h6>

* * *

<h3>Introduction</h3>

Bookmarks can associate files with thumbnails and descriptions. It also provides the
filters needed to find and mark important items. It is however, a file manager at heart.

Most file managers require traversing through subfolder-upon-subfolders to locate an item. Bookmarks implements an alternative (although more resource intense) approach: it lists all files from every subfolder when a selection is made. This is sometimes very useful, eg. when we don't know _exactly_
the location of a footage, or when we want to compare footage versions.

To make things manageble, Bookmarks separates jobs into, well, _**Bookmarks**_. These are distinct parts of any job, eg. the shots, assets or edit folders, where normally CGI content resides. Each bookmark can have their own framerate and resolution settings, as well as their
own Slack workspace.

Each _**Bookmark**_ contains _**Assets**_, eg. the main shot folders, which in turn contain
_**Task Folders**_, eg. scenes, renders, references and comps subfolders.
To put simply, Bookmarks kind-of expects folder hierarchies similar to the standard Maya project structure to work as intended.


* * *

### <img src="./bookmarks/rsc/maya.png" height=32> mBookmarks

The Maya plugin replaces Maya's **_Set Project_** and uses Bookmarks' own assets
to set the current project.

<p align="center">
 <img src="./bookmarks/rsc/maya_preview.png" alt="Maya"/>
</p>

* * *

### [Download the latest binary release](https://github.com/wgergely/Bookmarks/releases)

### [Documentation](https://wgergely.github.io/Bookmarks) (Docs are work in progress!)

* * *

<!-- <p align="center">
 <img src="./bookmarks/rsc/draganddrop.gif" alt="Maya"/>
</p> -->

### Credits and acknowledgments

(c) Gergely Wootsch, 2020.
[Email](hello@gergely-wootsch.com)
[gergely-wootsch.com](http://gergely-wootsch.com)
