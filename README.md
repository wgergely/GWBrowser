<center>
  <img src="./bookmarks/rsc/icon.png" alt="Bookmarks" height=128/>
  <h1>Bookmarks</h1>
  <h4>A simple file and asset manager for CG productions</h4><br>

  <p align="center">
    <a href="http://gergely-wootsch.com">
        <img src="https://img.shields.io/badge/Python-lightgrey.svg" alt="Python version">
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

<img src="./bookmarks/rsc/todo.png" height=20> Annotate files with thumbnails, To-dos, tags and descriptions<br>
<img src="./bookmarks/rsc/archived.png" height=20> Archive superflous items non-destructively<br>
<img src="./bookmarks/rsc/active.png" height=20> Preview images of common media formats using `OpenImageIO`<br>
<img src="./bookmarks/rsc/folder.png" height=20> Reveal files in Finder / Explorer easily<br>
<img src="./bookmarks/rsc/rv.png" height=20> Push footage to `Shotgun RV` directly from Bookmarks<br>
<img src="./bookmarks/rsc/slack_color.png" height=20> Send messages with `Slack`<br>
<img src="./bookmarks/rsc/maya.png" height=20> Maya integration<br>
<img src="./bookmarks/rsc/icon_bw.png" height=14> Windows and Mac OS X compatible<br>
<img src="./bookmarks/rsc/icon_bw.png" height=14> Written in `Qt for Python`
</h6>

* * *

<h3>Files</h3>

Most file managers need you to click-through subfolders to find a file. Bookmarks traverses subfolders to give you an overview of the contents.

This is sometimes useful, for instance, when the _exact_ location of a footage is unknown, or when we want to compare footage versions and files residing at different places. This does however come with a performance tradeoff as files have to be loaded beforehand.

To make things manageble, Bookmarks separates jobs into **Bookmarks**. These are arbitary folders inside a job, eg. the _shots_, _assets_ or _edit_ folder where CG content is normally kept. Each bookmark has its own framerate, resolution and Slack integration.

The Bookmark folders contain a series of **Assets**. An Asset is simply a pre-defined folder structure with a series of **Task Folders** inside, eg. _scenes_, _renders_,or _comps_. To put simply, Bookmarks expects to find a folder hierarchy not dissimilar to a standard Maya project.

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
