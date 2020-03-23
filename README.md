<center>
  <img src="./bookmarks/rsc/icon.png" alt="Bookmarks" height=128/>
  <h1>Bookmarks</h1>
  <h4>A simple file and asset manager for animation and CG productions.</h4><br>

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
<center>

<h2>Features</h2>
<img src="./bookmarks/rsc/todo.png" height=20> Annotate files with thumbnails, To-dos, tags and descriptions<br>
<img src="./bookmarks/rsc/archived.png" height=20> Archive superflous items non-destructively<br>
<img src="./bookmarks/rsc/active.png" height=20> Preview images (using `OpenImageIO`)<br>
<img src="./bookmarks/rsc/folder.png" height=20> Reveal files in Finder / Explorer easily<br>
<img src="./bookmarks/rsc/rv.png" height=20> Push footage to Shotgun RV<br>
<img src="./bookmarks/rsc/slack_color.png" height=20> Send messages with `Slack`<br>
<img src="./bookmarks/rsc/maya.png" height=20> Maya integration<br>
<img src="./bookmarks/rsc/icon_bw.png" height=14> Run on Windows or Mac OS X<br>

</center>

* * *

# Introduction

Bookmarks provides a simple visual overview of your job's shots and assets, and the files contained within them.

Most file managers show files hierarchically paired often with cascading clicking to find files tucked away. Bookmarks instead looks inside subfolders and provides filters to locate and save items. This is sometimes useful, for instance, when the _exact_ location of a file is unknown, or when you want to compare footage versions residing at different places.

This does however come with a performance tradeoff as files have to be loaded beforehand. Up to a few hundred thousand files this should not take _too_ long, but a lot depends on network access, hard-drive speeds, etc.


### Bookmarks

To make a project a bit more modular, Bookmarks separates jobs into, well, **Bookmarks**. These are arbitary folders inside a job, eg. the _shots_, _assets_ or _edit_, where CG content is normally kept. Bookmarks have their own _**framerate**_, _**resolution**_, _**default frame range**_, and _**Slack Tokens**_ that DCCs can use to set up new projects.

The Bookmark folders contain a series of **Assets**. An Asset is simply a pre-defined folder structure of a series of **Task Folders**, eg. _scenes_, _renders_, _exports_, _comps_. To put simply, Bookmarks expects to find a folder hierarchy not dissimilar to a standard Maya or Houdini project.

* * *


The Maya plugin replaces Maya's **_Set Project_** and uses Bookmarks' own assets
to set the current Workspace.



<!-- <p align="center">
 <img src="./bookmarks/rsc/draganddrop.gif" alt="Maya"/>
</p> -->

### Credits and Acknowledgments

(c) Gergely Wootsch, 2020.<br>
[Email Me](mailto:hello@gergely-wootsch.com)<br>
[gergely-wootsch.com](http://gergely-wootsch.com)
