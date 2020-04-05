

# ![alt text][logo] Bookmarks

### A simple file and asset manager for animation and CG productions.

![alt text](https://img.shields.io/badge/Python-2.7-lightgrey.svg "Python 2.7") ![alt text](https://img.shields.io/badge/Qt-5.6%2B-lightgrey.svg "Qt 5.6+") ![alt text](https://img.shields.io/badge/platform-windows%20%7C%20osx-lightgray.svg "Windows & Mac OS X")



## Features

* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/folder.png" height=20>Create jobs and assets using custom folder templates
* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/todo.png" height=20>Annotate items using thumbnails, TODOs, tags and descriptions
* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/archived.png" height=20>Archive superflous items without touching underlying files
* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/active.png" height=20>Preview easily most image formats and Alembic archives
* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/folder.png" height=20>Reveal files in Finder / Explorer
* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/folder.png" height=20>Drag & Drop capable file-browser
* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/rv.png" height=20>Push footage to **Shotgun RV** from within Bookmarks
* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/slack_color.png" height=20>Send file paths and messages directly with **Slack**
* <img style="margin:4px 10px 4px 0px;" src="./bookmarks/rsc/maya.png" height=20>Dedicated Maya plugin



Bookmarks provides an overview of your shots, the files inside them and any custom notes, thumbnails and descriptions you or your team added. You can use Bookmarks to create new jobs, add assets to them, or browse existing content.


#####  Adding thumbnails and descriptions is easy

![alt text](./bookmarks/rsc/docs/adding_thumbnails_gif_8fps.gif "Adding thumbnails is easy") ![alt text](./bookmarks/rsc/docs/adding_thumbnails_and_descriptions_8fps.gif "And so is adding descriptions")


## Content Structure


Content is organised into three separate sections: `Bookmarks`, `Assets` & `Files`.


| Overview  | ![alt text](./bookmarks/rsc/docs/bookmark_graph.jpg "Content structure")  |
|---|---|
| Bookmarks | A folders inside your job and the main container for CG content. Each bookmark have their own _framerate_, _resolution_, _default frame-range_, and _Slack Tokens_.|
| Assets  | Maya or Houdini workspace-like folder structures. Each contains a series of **task folders** (eg. _scene_, _render_, etc. folders). Any folder can be an asset, and any folder containing an "asset identifier" file (eg. `workspace.mel`) will be recognised as an asset automatically. |
| Files  | Files are stored inside task folders. When browsing, Bookmarks reads all files inside a selected task folder, including files in subdirectories. You can use the provided search and filter tools to locate and save items.  |

``` python
  # Parsing the whole task folder does come with a performance tradeoff as all
  # files have to be loaded in advance. Up to a few hundred thousand files this
  # should not take too long, but a lot depends on network access, hard-drive
  # speeds, etc.
```




## Getting started

<p style="width:89%;text-align:justify;"> Right-click anywhere on the main window and select <img style="margin:4px 4px 4px 4px;"
src="./bookmarks/rsc/bookmark.png" height=20>Manage bookmarks. Use the window to configure servers, create new jobs and add bookmark folders.

To add a server, click the <img style="margin:4px 4px 4px 4px;"
src="./bookmarks/rsc/CopyAction.png" height=20>icon next to "Servers".<br>
</p>

  <img alt="Bookmark Tabs" src="./bookmarks/rsc/docs/managing_bookmarks_6fps.gif" width="89%">


```
The server is usually a location on a central network
location but can be any folder accessible to your computer, eg.
\\MY-SERVER\JOBS or C:\JOBS /volumes/server/jobs can all be valid.
```


<p style="width:89%;text-align:justify;">
Click <img style="margin:4px 4px 4px 4px;"
src="./bookmarks/rsc/CopyAction.png" height=20> next to _Jobs_ to add new jobs.
As templates are simple zip files you can add your own by draggin any zip file where
the templates are listed, or `right-click -> Add template...`</p>

<p style="width:89%;text-align:justify;">
If the job template already has bookmark folders they will be listed below.
You click the name to add or remove if from Bookmarks. Otherwise, click <img style="margin:4px 4px 4px 4px;"
src="./bookmarks/rsc/CopyAction.png" height=20> next to _Bookmarks_ to mark
a folder as a bookmark.</p>


* * *

# Maya plugin

The Maya plugin replaces Maya's **_Set Project_** and uses Bookmarks' own assets
to set the current Workspace.



### Credits and Acknowledgments

(c) Gergely Wootsch, 2020.<br>
[Email Me](mailto:hello@gergely-wootsch.com)<br>
[gergely-wootsch.com](http://gergely-wootsch.com)


[logo]: ./bookmarks/rsc/logo_s.png "Bookmarks: A simple file and asset manager for animation and CG productions"
