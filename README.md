<center>
  <img alt="Bookmarks: A simple file and asset manager for animation and CG productions." src="./bookmarks/rsc/icon.png" alt="Bookmarks" height="112">
  <br>
  <span style="font-size:28pt;margin:0px;">Bookmarks</span>

  <p style="font-size:16pt;margin:0px;">A simple file and asset manager for animation and CG productions.</p>

  <br>

  <p>
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


## Features

* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/folder.png" height=20>Create jobs and assets using custom folder templates
* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/todo.png" height=20>Annotate items using thumbnails, TODOs, tags and descriptions
* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/archived.png" height=20>Archive superflous items without touching the underlying files
* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/active.png" height=20>Preview easily most image formats and Alembic archives
* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/folder.png" height=20>Reveal files in Finder / Explorer
* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/folder.png" height=20>Drag & Drop capable file-browser
* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/rv.png" height=20>Push footage to **Shotgun RV** from within Bookmarks
* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/slack_color.png" height=20>Send file paths and messages directly with **Slack**
* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/maya.png" height=20>Maya plugin


<center>

  <p style="width:89%;text-align:justify;">Bookmarks gives an overview of your shots, the files inside them and any
  custom notes, thumbnails and descriptions you or your team added. You
  can use Bookmarks to create new jobs, add assets to them, or browse existing
  content.</p>

  <p style="width:89%">

  To can make your job pretty by adding thumbnails...

  </p>
  <img alt="Bookmark Tabs" src="./bookmarks/rsc/docs/adding_thumbnails_gif_8fps.gif" width="89%">

  <br>
  <p style="width:89%">

  ...and a short descriptions.

  </p>
  <img alt="Bookmark Tabs" src="./bookmarks/rsc/docs/adding_thumbnails_and_descriptions_8fps.gif" width="89%">

  <p style="width:89%">

  Content is organised into three main tabs, like so:

  </p>

  <table style="width:89%">
    <tr>
      <th style="text-align:justify;font-weight:100;font-size:10pt;" width="10%">
        Bookmarks
      </th>
      <th style="text-align:justify;font-weight:100;font-size:10pt;" width="90%">

  Arbitary folders inside your job folder and the main container of
  CG content.

  They have their own _**framerate**_, _**resolution**_, _**default frame range**_,
  and _**Slack Tokens**_ that DCCs can use to set up new scenes.
      </th>
    </tr>
    <tr>
      <th style="text-align:justify;font-weight:100;font-size:10pt;" width="10%">
        Assets
      </th>
      <th style="text-align:justify;font-weight:100;font-size:10pt;" width="90%">
  A container of **task folders**,
  eg. a folder with _scene_, _render_, _export_ folders. Think of them as
  Maya or Houdini like workspaces.

  You can use your own templates as the templates are plain zip archives containing folder/files.
  Any folder can be an asset, and any folder containing an "asset
  identifier" file (eg. `workspace.mel`, but this can be customised to be any file)
  will be recognised as such automatically.
      </th>
    </tr>
    <tr>
      <th style="text-align:justify;font-weight:100;font-size:10pt;" width="10%">
        Files
      </th>
      <th style="text-align:justify;font-weight:100;font-size:10pt;" width="90%">
Files are stored inside "task folders". These are the _scene_, _render_,
_export_ folders placed in the root of an asset.
When browsing, Bookmarks reads all files inside a selected task folder, including files in subdirectories.
You can use the search filters and flags to find and save footage or scenes files
you need to be working with.

``` python
  # Parsing the whole task folder does come with a performance tradeoff as all
  # files have to be loaded in advance. Up to a few hundred thousand files this
  # should not take too long, but a lot depends on network access, hard-drive
  # speeds, etc.
```
</th>
    </tr>
    <tr>
      <th colspan=2>
        <img alt="Bookmark Tabs" src="./bookmarks/rsc/docs/graph.jpg">
      </th>
    </tr>
  </table>
</center>


***


### Setup

`Right-Click` anywhere on the main window and select <img style="margin:4px 4px 4px 4px;"
src="./bookmarks/rsc/bookmark.png" height=20>`Manage bookmarks`.<br>
Here you can configure servers, create new jobs and bookmark folders.

To add a server, click the <img style="margin:4px 4px 4px 4px;"
src="./bookmarks/rsc/CopyAction.png" height=20>icon by "Servers".<br>

<center>
  <img alt="Bookmark Tabs" src="./bookmarks/rsc/docs/managing_bookmarks_6fps.gif" width="89%">
</center>


```
The server is usually a location on a central network
location but can be any folder accessible to your computer, eg.
\\MY-SERVER\JOBS or C:\JOBS /volumes/server/jobs can all be valid.
```



Click <img style="margin:4px 4px 4px 4px;"
src="./bookmarks/rsc/CopyAction.png" height=20> next to _Jobs_ to add new jobs.
Templates are simple zip files. To add your own just drag and drop them where
the templates are listed, or `right-click -> Add template...`

If the job template already has bookmark folders they will be listed below.
You click the name to add or remove if from Bookmarks. Otherwise, click <img style="margin:4px 4px 4px 4px;"
src="./bookmarks/rsc/CopyAction.png" height=20> next to _Bookmarks_ to mark
a folder as a bookmark.


* * *

# Maya plugin

The Maya plugin replaces Maya's **_Set Project_** and uses Bookmarks' own assets
to set the current Workspace.



<!-- <p align="center">
 <img src="./bookmarks/rsc/draganddrop.gif" alt="Maya"/>
</p> -->

### Credits and Acknowledgments

(c) Gergely Wootsch, 2020.<br>
[Email Me](mailto:hello@gergely-wootsch.com)<br>
[gergely-wootsch.com](http://gergely-wootsch.com)
