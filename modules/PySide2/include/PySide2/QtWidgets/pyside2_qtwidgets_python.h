/****************************************************************************
**
** Copyright (C) 2016 The Qt Company Ltd.
** Contact: https://www.qt.io/licensing/
**
** This file is part of PySide2.
**
** $QT_BEGIN_LICENSE:LGPL$
** Commercial License Usage
** Licensees holding valid commercial Qt licenses may use this file in
** accordance with the commercial license agreement provided with the
** Software or, alternatively, in accordance with the terms contained in
** a written agreement between you and The Qt Company. For licensing terms
** and conditions see https://www.qt.io/terms-conditions. For further
** information use the contact form at https://www.qt.io/contact-us.
**
** GNU Lesser General Public License Usage
** Alternatively, this file may be used under the terms of the GNU Lesser
** General Public License version 3 as published by the Free Software
** Foundation and appearing in the file LICENSE.LGPL3 included in the
** packaging of this file. Please review the following information to
** ensure the GNU Lesser General Public License version 3 requirements
** will be met: https://www.gnu.org/licenses/lgpl-3.0.html.
**
** GNU General Public License Usage
** Alternatively, this file may be used under the terms of the GNU
** General Public License version 2.0 or (at your option) the GNU General
** Public license version 3 or any later version approved by the KDE Free
** Qt Foundation. The licenses are as published by the Free Software
** Foundation and appearing in the file LICENSE.GPL2 and LICENSE.GPL3
** included in the packaging of this file. Please review the following
** information to ensure the GNU General Public License requirements will
** be met: https://www.gnu.org/licenses/gpl-2.0.html and
** https://www.gnu.org/licenses/gpl-3.0.html.
**
** $QT_END_LICENSE$
**
****************************************************************************/


#ifndef SBK_QTWIDGETS_PYTHON_H
#define SBK_QTWIDGETS_PYTHON_H

#include <sbkpython.h>
#include <sbkconverter.h>
#include <sbkenum.h>
#include <basewrapper.h>
#include <bindingmanager.h>
#include <memory>

#include <pysidesignal.h>
// Module Includes
#include <pyside2_qtgui_python.h>
#include <pyside2_qtcore_python.h>

// Binded library includes
#include <qtreewidget.h>
#include <qlayoutitem.h>
#include <qgraphicseffect.h>
#include <qlistwidget.h>
#include <qtableview.h>
#include <qdockwidget.h>
#include <qtoolbar.h>
#include <qformlayout.h>
#include <qfontdialog.h>
#include <qcompleter.h>
#include <qgesture.h>
#include <qdialogbuttonbox.h>
#include <qsplashscreen.h>
#include <qmessagebox.h>
#include <qgraphicslayoutitem.h>
#include <qundoview.h>
#include <qstylepainter.h>
#include <qwizard.h>
#include <qaction.h>
#include <qcommandlinkbutton.h>
#include <qgesturerecognizer.h>
#include <qdatawidgetmapper.h>
#include <qmenubar.h>
#include <qmdiarea.h>
#include <qstyle.h>
#include <qheaderview.h>
#include <qfileiconprovider.h>
#include <qabstractscrollarea.h>
#include <qundostack.h>
#include <qspinbox.h>
#include <qtablewidget.h>
#include <qtoolbutton.h>
#include <qsizegrip.h>
#include <qtabwidget.h>
#include <qstackedwidget.h>
#include <qscrollbar.h>
#include <qmouseeventtransition.h>
#include <qgroupbox.h>
#include <qbuttongroup.h>
#include <qfontcombobox.h>
#include <qscrollarea.h>
#include <qlayout.h>
#include <qstylefactory.h>
#include <qcalendarwidget.h>
#include <qabstractitemdelegate.h>
#include <qabstractbutton.h>
#include <qgraphicstransform.h>
#include <qpushbutton.h>
#include <qtreeview.h>
#include <qgraphicslinearlayout.h>
#include <qabstractitemview.h>
#include <qgraphicsitem.h>
#include <qgraphicswidget.h>
#include <qdrawutil.h>
#include <qslider.h>
#include <qfiledialog.h>
#include <qactiongroup.h>
#include <qgridlayout.h>
#include <qdialog.h>
#include <qshortcut.h>
#include <qfocusframe.h>
#include <qcolumnview.h>
#include <qframe.h>
#include <qsplitter.h>
#include <qinputdialog.h>
#include <qcombobox.h>
#include <qapplication.h>
#include <qstyleoption.h>
#include <qitemdelegate.h>
#include <qradiobutton.h>
#include <qkeysequenceedit.h>
#include <qabstractslider.h>
#include <qtextbrowser.h>
#include <qgraphicssceneevent.h>
#include <qgraphicsview.h>
#include <qdirmodel.h>
#include <qlcdnumber.h>
#include <qmenu.h>
#include <qcommonstyle.h>
#include <qerrormessage.h>
#include <qtoolbox.h>
#include <qdatetimeedit.h>
#include <qfilesystemmodel.h>
#include <QTextEdit>
#include <qtextedit.h>
#include <qkeyeventtransition.h>
#include <qwidgetaction.h>
#include <qwidget.h>
#include <qdial.h>
#include <qmdisubwindow.h>
#include <qgraphicsitemanimation.h>
#include <qabstractspinbox.h>
#include <qtabbar.h>
#include <qgraphicslayout.h>
#include <qwhatsthis.h>
#include <qprogressbar.h>
#include <qstatusbar.h>
#include <qplaintextedit.h>
#include <qsizepolicy.h>
#include <qlabel.h>
#include <qdesktopwidget.h>
#include <qtreewidgetitemiterator.h>
#include <qcheckbox.h>
#include <qundogroup.h>
#include <qgraphicsgridlayout.h>
#include <qstackedlayout.h>
#include <qsystemtrayicon.h>
#include <qstyleditemdelegate.h>
#include <qgraphicsproxywidget.h>
#include <qitemeditorfactory.h>
#include <qprogressdialog.h>
#include <qlistview.h>
#include <qboxlayout.h>
#include <qtooltip.h>
#include <qcolordialog.h>
#include <qopenglwidget.h>
#include <qgraphicsanchorlayout.h>
#include <qmainwindow.h>
#include <qlineedit.h>
#include <qgraphicsscene.h>
#include <qrubberband.h>
// Conversion Includes - Primitive Types
#include <signalmanager.h>
#include <qabstractitemmodel.h>
#include <QStringList>
#include <QString>
#include <wtypes.h>

// Conversion Includes - Container Types
#include <pysideqflags.h>
#include <QMultiMap>
#include <QSet>
#include <QMap>
#include <QVector>
#include <QPair>
#include <QList>
#include <QStack>
#include <QQueue>
#include <QLinkedList>

// Type indices
#define SBK_QUNDOCOMMAND_IDX                                         425
#define SBK_QSTYLEFACTORY_IDX                                        282
#define SBK_QTILERULES_IDX                                           411
#define SBK_QWHATSTHIS_IDX                                           430
#define SBK_QTOOLTIP_IDX                                             417
#define SBK_QGESTURERECOGNIZER_IDX                                   131
#define SBK_QGESTURERECOGNIZER_RESULTFLAG_IDX                        132
#define SBK_QFLAGS_QGESTURERECOGNIZER_RESULTFLAG__IDX                89
#define SBK_QLAYOUTITEM_IDX                                          208
#define SBK_QWIDGETITEM_IDX                                          434
#define SBK_QTREEWIDGETITEM_IDX                                      420
#define SBK_QTREEWIDGETITEM_ITEMTYPE_IDX                             422
#define SBK_QTREEWIDGETITEM_CHILDINDICATORPOLICY_IDX                 421
#define SBK_QTREEWIDGETITEMITERATOR_IDX                              423
#define SBK_QTREEWIDGETITEMITERATOR_ITERATORFLAG_IDX                 424
#define SBK_QFLAGS_QTREEWIDGETITEMITERATOR_ITERATORFLAG__IDX         112
#define SBK_QTABLEWIDGETITEM_IDX                                     401
#define SBK_QTABLEWIDGETITEM_ITEMTYPE_IDX                            402
#define SBK_QTABLEWIDGETSELECTIONRANGE_IDX                           403
#define SBK_QLISTWIDGETITEM_IDX                                      219
#define SBK_QLISTWIDGETITEM_ITEMTYPE_IDX                             220
#define SBK_QITEMEDITORFACTORY_IDX                                   199
#define SBK_QITEMEDITORCREATORBASE_IDX                               198
#define SBK_QFILEICONPROVIDER_IDX                                    74
#define SBK_QFILEICONPROVIDER_ICONTYPE_IDX                           75
#define SBK_QFILEICONPROVIDER_OPTION_IDX                             76
#define SBK_QFLAGS_QFILEICONPROVIDER_OPTION__IDX                     86
#define SBK_QSTYLEOPTION_IDX                                         293
#define SBK_QSTYLEOPTION_OPTIONTYPE_IDX                              294
#define SBK_QSTYLEOPTION_STYLEOPTIONTYPE_IDX                         295
#define SBK_QSTYLEOPTION_STYLEOPTIONVERSION_IDX                      296
#define SBK_QSTYLEOPTIONTABWIDGETFRAME_IDX                           359
#define SBK_QSTYLEOPTIONTABWIDGETFRAME_STYLEOPTIONTYPE_IDX           360
#define SBK_QSTYLEOPTIONTABWIDGETFRAME_STYLEOPTIONVERSION_IDX        361
#define SBK_QSTYLEOPTIONFRAME_IDX                                    313
#define SBK_QSTYLEOPTIONFRAME_STYLEOPTIONTYPE_IDX                    315
#define SBK_QSTYLEOPTIONFRAME_STYLEOPTIONVERSION_IDX                 316
#define SBK_QSTYLEOPTIONFRAME_FRAMEFEATURE_IDX                       314
#define SBK_QFLAGS_QSTYLEOPTIONFRAME_FRAMEFEATURE__IDX               105
#define SBK_QSTYLEOPTIONHEADER_IDX                                   323
#define SBK_QSTYLEOPTIONHEADER_STYLEOPTIONTYPE_IDX                   327
#define SBK_QSTYLEOPTIONHEADER_STYLEOPTIONVERSION_IDX                328
#define SBK_QSTYLEOPTIONHEADER_SECTIONPOSITION_IDX                   324
#define SBK_QSTYLEOPTIONHEADER_SELECTEDPOSITION_IDX                  325
#define SBK_QSTYLEOPTIONHEADER_SORTINDICATOR_IDX                     326
#define SBK_QSTYLEOPTIONGRAPHICSITEM_IDX                             317
#define SBK_QSTYLEOPTIONGRAPHICSITEM_STYLEOPTIONTYPE_IDX             318
#define SBK_QSTYLEOPTIONGRAPHICSITEM_STYLEOPTIONVERSION_IDX          319
#define SBK_QSTYLEOPTIONTABBARBASE_IDX                               356
#define SBK_QSTYLEOPTIONTABBARBASE_STYLEOPTIONTYPE_IDX               357
#define SBK_QSTYLEOPTIONTABBARBASE_STYLEOPTIONVERSION_IDX            358
#define SBK_QSTYLEOPTIONTAB_IDX                                      349
#define SBK_QSTYLEOPTIONTAB_STYLEOPTIONTYPE_IDX                      352
#define SBK_QSTYLEOPTIONTAB_STYLEOPTIONVERSION_IDX                   353
#define SBK_QSTYLEOPTIONTAB_TABPOSITION_IDX                          355
#define SBK_QSTYLEOPTIONTAB_SELECTEDPOSITION_IDX                     351
#define SBK_QSTYLEOPTIONTAB_CORNERWIDGET_IDX                         350
#define SBK_QFLAGS_QSTYLEOPTIONTAB_CORNERWIDGET__IDX                 106
#define SBK_QSTYLEOPTIONTAB_TABFEATURE_IDX                           354
#define SBK_QFLAGS_QSTYLEOPTIONTAB_TABFEATURE__IDX                   107
#define SBK_QSTYLEOPTIONBUTTON_IDX                                   297
#define SBK_QSTYLEOPTIONBUTTON_STYLEOPTIONTYPE_IDX                   299
#define SBK_QSTYLEOPTIONBUTTON_STYLEOPTIONVERSION_IDX                300
#define SBK_QSTYLEOPTIONBUTTON_BUTTONFEATURE_IDX                     298
#define SBK_QFLAGS_QSTYLEOPTIONBUTTON_BUTTONFEATURE__IDX             104
#define SBK_QSTYLEHINTRETURN_IDX                                     283
#define SBK_QSTYLEHINTRETURN_HINTRETURNTYPE_IDX                      284
#define SBK_QSTYLEHINTRETURN_STYLEOPTIONTYPE_IDX                     285
#define SBK_QSTYLEHINTRETURN_STYLEOPTIONVERSION_IDX                  286
#define SBK_QSTYLEHINTRETURNMASK_IDX                                 287
#define SBK_QSTYLEHINTRETURNMASK_STYLEOPTIONTYPE_IDX                 288
#define SBK_QSTYLEHINTRETURNMASK_STYLEOPTIONVERSION_IDX              289
#define SBK_QSTYLEHINTRETURNVARIANT_IDX                              290
#define SBK_QSTYLEHINTRETURNVARIANT_STYLEOPTIONTYPE_IDX              291
#define SBK_QSTYLEHINTRETURNVARIANT_STYLEOPTIONVERSION_IDX           292
#define SBK_QSTYLEOPTIONPROGRESSBAR_IDX                              334
#define SBK_QSTYLEOPTIONPROGRESSBAR_STYLEOPTIONTYPE_IDX              335
#define SBK_QSTYLEOPTIONPROGRESSBAR_STYLEOPTIONVERSION_IDX           336
#define SBK_QSTYLEOPTIONTOOLBAR_IDX                                  365
#define SBK_QSTYLEOPTIONTOOLBAR_STYLEOPTIONTYPE_IDX                  366
#define SBK_QSTYLEOPTIONTOOLBAR_STYLEOPTIONVERSION_IDX               367
#define SBK_QSTYLEOPTIONTOOLBAR_TOOLBARPOSITION_IDX                  369
#define SBK_QSTYLEOPTIONTOOLBAR_TOOLBARFEATURE_IDX                   368
#define SBK_QFLAGS_QSTYLEOPTIONTOOLBAR_TOOLBARFEATURE__IDX           108
#define SBK_QSTYLEOPTIONDOCKWIDGET_IDX                               307
#define SBK_QSTYLEOPTIONDOCKWIDGET_STYLEOPTIONTYPE_IDX               308
#define SBK_QSTYLEOPTIONDOCKWIDGET_STYLEOPTIONVERSION_IDX            309
#define SBK_QSTYLEOPTIONMENUITEM_IDX                                 329
#define SBK_QSTYLEOPTIONMENUITEM_STYLEOPTIONTYPE_IDX                 332
#define SBK_QSTYLEOPTIONMENUITEM_STYLEOPTIONVERSION_IDX              333
#define SBK_QSTYLEOPTIONMENUITEM_MENUITEMTYPE_IDX                    331
#define SBK_QSTYLEOPTIONMENUITEM_CHECKTYPE_IDX                       330
#define SBK_QSTYLEOPTIONTOOLBOX_IDX                                  370
#define SBK_QSTYLEOPTIONTOOLBOX_STYLEOPTIONTYPE_IDX                  372
#define SBK_QSTYLEOPTIONTOOLBOX_STYLEOPTIONVERSION_IDX               373
#define SBK_QSTYLEOPTIONTOOLBOX_TABPOSITION_IDX                      374
#define SBK_QSTYLEOPTIONTOOLBOX_SELECTEDPOSITION_IDX                 371
#define SBK_QSTYLEOPTIONVIEWITEM_IDX                                 379
#define SBK_QSTYLEOPTIONVIEWITEM_STYLEOPTIONTYPE_IDX                 381
#define SBK_QSTYLEOPTIONVIEWITEM_STYLEOPTIONVERSION_IDX              382
#define SBK_QSTYLEOPTIONVIEWITEM_POSITION_IDX                        380
#define SBK_QSTYLEOPTIONVIEWITEM_VIEWITEMFEATURE_IDX                 383
#define SBK_QFLAGS_QSTYLEOPTIONVIEWITEM_VIEWITEMFEATURE__IDX         110
#define SBK_QSTYLEOPTIONVIEWITEM_VIEWITEMPOSITION_IDX                384
#define SBK_QSTYLEOPTIONCOMPLEX_IDX                                  304
#define SBK_QSTYLEOPTIONCOMPLEX_STYLEOPTIONTYPE_IDX                  305
#define SBK_QSTYLEOPTIONCOMPLEX_STYLEOPTIONVERSION_IDX               306
#define SBK_QSTYLEOPTIONCOMBOBOX_IDX                                 301
#define SBK_QSTYLEOPTIONCOMBOBOX_STYLEOPTIONTYPE_IDX                 302
#define SBK_QSTYLEOPTIONCOMBOBOX_STYLEOPTIONVERSION_IDX              303
#define SBK_QSTYLEOPTIONTOOLBUTTON_IDX                               375
#define SBK_QSTYLEOPTIONTOOLBUTTON_STYLEOPTIONTYPE_IDX               376
#define SBK_QSTYLEOPTIONTOOLBUTTON_STYLEOPTIONVERSION_IDX            377
#define SBK_QSTYLEOPTIONTOOLBUTTON_TOOLBUTTONFEATURE_IDX             378
#define SBK_QFLAGS_QSTYLEOPTIONTOOLBUTTON_TOOLBUTTONFEATURE__IDX     109
#define SBK_QSTYLEOPTIONGROUPBOX_IDX                                 320
#define SBK_QSTYLEOPTIONGROUPBOX_STYLEOPTIONTYPE_IDX                 321
#define SBK_QSTYLEOPTIONGROUPBOX_STYLEOPTIONVERSION_IDX              322
#define SBK_QSTYLEOPTIONTITLEBAR_IDX                                 362
#define SBK_QSTYLEOPTIONTITLEBAR_STYLEOPTIONTYPE_IDX                 363
#define SBK_QSTYLEOPTIONTITLEBAR_STYLEOPTIONVERSION_IDX              364
#define SBK_QSTYLEOPTIONSIZEGRIP_IDX                                 340
#define SBK_QSTYLEOPTIONSIZEGRIP_STYLEOPTIONTYPE_IDX                 341
#define SBK_QSTYLEOPTIONSIZEGRIP_STYLEOPTIONVERSION_IDX              342
#define SBK_QSTYLEOPTIONSPINBOX_IDX                                  346
#define SBK_QSTYLEOPTIONSPINBOX_STYLEOPTIONTYPE_IDX                  347
#define SBK_QSTYLEOPTIONSPINBOX_STYLEOPTIONVERSION_IDX               348
#define SBK_QSTYLEOPTIONSLIDER_IDX                                   343
#define SBK_QSTYLEOPTIONSLIDER_STYLEOPTIONTYPE_IDX                   344
#define SBK_QSTYLEOPTIONSLIDER_STYLEOPTIONVERSION_IDX                345
#define SBK_QSTYLEOPTIONRUBBERBAND_IDX                               337
#define SBK_QSTYLEOPTIONRUBBERBAND_STYLEOPTIONTYPE_IDX               338
#define SBK_QSTYLEOPTIONRUBBERBAND_STYLEOPTIONVERSION_IDX            339
#define SBK_QSTYLEOPTIONFOCUSRECT_IDX                                310
#define SBK_QSTYLEOPTIONFOCUSRECT_STYLEOPTIONTYPE_IDX                311
#define SBK_QSTYLEOPTIONFOCUSRECT_STYLEOPTIONVERSION_IDX             312
#define SBK_QSIZEPOLICY_IDX                                          255
#define SBK_QSIZEPOLICY_POLICYFLAG_IDX                               258
#define SBK_QSIZEPOLICY_POLICY_IDX                                   257
#define SBK_QSIZEPOLICY_CONTROLTYPE_IDX                              256
#define SBK_QFLAGS_QSIZEPOLICY_CONTROLTYPE__IDX                      101
#define SBK_QSPACERITEM_IDX                                          261
#define SBK_QGRAPHICSLAYOUTITEM_IDX                                  153
#define SBK_QGRAPHICSLAYOUT_IDX                                      152
#define SBK_QGRAPHICSANCHORLAYOUT_IDX                                134
#define SBK_QGRAPHICSGRIDLAYOUT_IDX                                  143
#define SBK_QGRAPHICSLINEARLAYOUT_IDX                                155
#define SBK_QGRAPHICSITEM_IDX                                        144
#define SBK_QGRAPHICSITEM_GRAPHICSITEMFLAG_IDX                       148
#define SBK_QFLAGS_QGRAPHICSITEM_GRAPHICSITEMFLAG__IDX               92
#define SBK_QGRAPHICSITEM_GRAPHICSITEMCHANGE_IDX                     147
#define SBK_QGRAPHICSITEM_CACHEMODE_IDX                              145
#define SBK_QGRAPHICSITEM_PANELMODALITY_IDX                          149
#define SBK_QGRAPHICSITEM_EXTENSION_IDX                              146
#define SBK_QABSTRACTGRAPHICSSHAPEITEM_IDX                           1
#define SBK_QGRAPHICSSIMPLETEXTITEM_IDX                              179
#define SBK_QGRAPHICSPATHITEM_IDX                                    158
#define SBK_QGRAPHICSELLIPSEITEM_IDX                                 142
#define SBK_QGRAPHICSRECTITEM_IDX                                    163
#define SBK_QGRAPHICSPOLYGONITEM_IDX                                 161
#define SBK_QGRAPHICSLINEITEM_IDX                                    154
#define SBK_QGRAPHICSPIXMAPITEM_IDX                                  159
#define SBK_QGRAPHICSPIXMAPITEM_SHAPEMODE_IDX                        160
#define SBK_QGRAPHICSITEMGROUP_IDX                                   151
#define SBK_QSTYLEPAINTER_IDX                                        385
#define SBK_QGESTUREEVENT_IDX                                        130
#define SBK_QGRAPHICSSCENEEVENT_IDX                                  172
#define SBK_QGRAPHICSSCENERESIZEEVENT_IDX                            177
#define SBK_QGRAPHICSSCENEDRAGDROPEVENT_IDX                          171
#define SBK_QGRAPHICSSCENEMOVEEVENT_IDX                              176
#define SBK_QGRAPHICSSCENEMOUSEEVENT_IDX                             175
#define SBK_QGRAPHICSSCENECONTEXTMENUEVENT_IDX                       169
#define SBK_QGRAPHICSSCENECONTEXTMENUEVENT_REASON_IDX                170
#define SBK_QGRAPHICSSCENEWHEELEVENT_IDX                             178
#define SBK_QGRAPHICSSCENEHELPEVENT_IDX                              173
#define SBK_QGRAPHICSSCENEHOVEREVENT_IDX                             174
#define SBK_QGRAPHICSANCHOR_IDX                                      133
#define SBK_QGRAPHICSITEMANIMATION_IDX                               150
#define SBK_QACTION_IDX                                              23
#define SBK_QACTION_MENUROLE_IDX                                     25
#define SBK_QACTION_PRIORITY_IDX                                     26
#define SBK_QACTION_ACTIONEVENT_IDX                                  24
#define SBK_QWIDGETACTION_IDX                                        433
#define SBK_QGRAPHICSSCENE_IDX                                       166
#define SBK_QGRAPHICSSCENE_ITEMINDEXMETHOD_IDX                       167
#define SBK_QGRAPHICSSCENE_SCENELAYER_IDX                            168
#define SBK_QFLAGS_QGRAPHICSSCENE_SCENELAYER__IDX                    93
#define SBK_QPLAINTEXTDOCUMENTLAYOUT_IDX                             241
#define SBK_QACTIONGROUP_IDX                                         27
#define SBK_QLAYOUT_IDX                                              206
#define SBK_QLAYOUT_SIZECONSTRAINT_IDX                               207
#define SBK_QFORMLAYOUT_IDX                                          120
#define SBK_QFORMLAYOUT_FIELDGROWTHPOLICY_IDX                        121
#define SBK_QFORMLAYOUT_ROWWRAPPOLICY_IDX                            123
#define SBK_QFORMLAYOUT_ITEMROLE_IDX                                 122
#define SBK_QSTACKEDLAYOUT_IDX                                       266
#define SBK_QSTACKEDLAYOUT_STACKINGMODE_IDX                          267
#define SBK_QBOXLAYOUT_IDX                                           30
#define SBK_QBOXLAYOUT_DIRECTION_IDX                                 31
#define SBK_QVBOXLAYOUT_IDX                                          429
#define SBK_QHBOXLAYOUT_IDX                                          191
#define SBK_QGRIDLAYOUT_IDX                                          189
#define SBK_QGRAPHICSTRANSFORM_IDX                                   181
#define SBK_QGRAPHICSROTATION_IDX                                    164
#define SBK_QGRAPHICSSCALE_IDX                                       165
#define SBK_QAPPLICATION_IDX                                         28
#define SBK_QAPPLICATION_COLORSPEC_IDX                               29
#define SBK_QGESTURE_IDX                                             128
#define SBK_QGESTURE_GESTURECANCELPOLICY_IDX                         129
#define SBK_QPANGESTURE_IDX                                          238
#define SBK_QSWIPEGESTURE_IDX                                        387
#define SBK_QSWIPEGESTURE_SWIPEDIRECTION_IDX                         388
#define SBK_QPINCHGESTURE_IDX                                        239
#define SBK_QPINCHGESTURE_CHANGEFLAG_IDX                             240
#define SBK_QFLAGS_QPINCHGESTURE_CHANGEFLAG__IDX                     100
#define SBK_QTAPANDHOLDGESTURE_IDX                                   404
#define SBK_QTAPGESTURE_IDX                                          405
#define SBK_QSHORTCUT_IDX                                            253
#define SBK_QSTYLE_IDX                                               270
#define SBK_QSTYLE_STATEFLAG_IDX                                     278
#define SBK_QFLAGS_QSTYLE_STATEFLAG__IDX                             102
#define SBK_QSTYLE_PRIMITIVEELEMENT_IDX                              275
#define SBK_QSTYLE_CONTROLELEMENT_IDX                                273
#define SBK_QSTYLE_SUBELEMENT_IDX                                    281
#define SBK_QSTYLE_COMPLEXCONTROL_IDX                                271
#define SBK_QSTYLE_SUBCONTROL_IDX                                    280
#define SBK_QFLAGS_QSTYLE_SUBCONTROL__IDX                            103
#define SBK_QSTYLE_PIXELMETRIC_IDX                                   274
#define SBK_QSTYLE_CONTENTSTYPE_IDX                                  272
#define SBK_QSTYLE_REQUESTSOFTWAREINPUTPANEL_IDX                     276
#define SBK_QSTYLE_STYLEHINT_IDX                                     279
#define SBK_QSTYLE_STANDARDPIXMAP_IDX                                277
#define SBK_QCOMMONSTYLE_IDX                                         45
#define SBK_QWIDGET_IDX                                              431
#define SBK_QWIDGET_RENDERFLAG_IDX                                   432
#define SBK_QFLAGS_QWIDGET_RENDERFLAG__IDX                           113
#define SBK_QDESKTOPWIDGET_IDX                                       54
#define SBK_QDIALOG_IDX                                              56
#define SBK_QDIALOG_DIALOGCODE_IDX                                   57
#define SBK_QCOLORDIALOG_IDX                                         38
#define SBK_QCOLORDIALOG_COLORDIALOGOPTION_IDX                       39
#define SBK_QFLAGS_QCOLORDIALOG_COLORDIALOGOPTION__IDX               81
#define SBK_QOPENGLWIDGET_IDX                                        236
#define SBK_QOPENGLWIDGET_UPDATEBEHAVIOR_IDX                         237
#define SBK_QERRORMESSAGE_IDX                                        67
#define SBK_QFONTDIALOG_IDX                                          118
#define SBK_QFONTDIALOG_FONTDIALOGOPTION_IDX                         119
#define SBK_QFLAGS_QFONTDIALOG_FONTDIALOGOPTION__IDX                 88
#define SBK_QLINEEDIT_IDX                                            209
#define SBK_QLINEEDIT_ACTIONPOSITION_IDX                             210
#define SBK_QLINEEDIT_ECHOMODE_IDX                                   211
#define SBK_QFRAME_IDX                                               124
#define SBK_QFRAME_SHAPE_IDX                                         126
#define SBK_QFRAME_SHADOW_IDX                                        125
#define SBK_QFRAME_STYLEMASK_IDX                                     127
#define SBK_QMESSAGEBOX_IDX                                          231
#define SBK_QMESSAGEBOX_ICON_IDX                                     233
#define SBK_QMESSAGEBOX_BUTTONROLE_IDX                               232
#define SBK_QMESSAGEBOX_STANDARDBUTTON_IDX                           234
#define SBK_QFLAGS_QMESSAGEBOX_STANDARDBUTTON__IDX                   99
#define SBK_QINPUTDIALOG_IDX                                         194
#define SBK_QINPUTDIALOG_INPUTDIALOGOPTION_IDX                       195
#define SBK_QINPUTDIALOG_INPUTMODE_IDX                               196
#define SBK_QWIZARD_IDX                                              435
#define SBK_QWIZARD_WIZARDBUTTON_IDX                                 436
#define SBK_QWIZARD_WIZARDPIXMAP_IDX                                 438
#define SBK_QWIZARD_WIZARDSTYLE_IDX                                  439
#define SBK_QWIZARD_WIZARDOPTION_IDX                                 437
#define SBK_QFLAGS_QWIZARD_WIZARDOPTION__IDX                         114
#define SBK_QPROGRESSDIALOG_IDX                                      246
#define SBK_QWIZARDPAGE_IDX                                          440
#define SBK_QABSTRACTBUTTON_IDX                                      0
#define SBK_QCHECKBOX_IDX                                            37
#define SBK_QCALENDARWIDGET_IDX                                      33
#define SBK_QCALENDARWIDGET_HORIZONTALHEADERFORMAT_IDX               34
#define SBK_QCALENDARWIDGET_VERTICALHEADERFORMAT_IDX                 36
#define SBK_QCALENDARWIDGET_SELECTIONMODE_IDX                        35
#define SBK_QPUSHBUTTON_IDX                                          247
#define SBK_QCOMBOBOX_IDX                                            41
#define SBK_QCOMBOBOX_INSERTPOLICY_IDX                               42
#define SBK_QCOMBOBOX_SIZEADJUSTPOLICY_IDX                           43
#define SBK_QCOMMANDLINKBUTTON_IDX                                   44
#define SBK_QDIALOGBUTTONBOX_IDX                                     58
#define SBK_QDIALOGBUTTONBOX_BUTTONROLE_IDX                          60
#define SBK_QDIALOGBUTTONBOX_STANDARDBUTTON_IDX                      61
#define SBK_QFLAGS_QDIALOGBUTTONBOX_STANDARDBUTTON__IDX              83
#define SBK_QDIALOGBUTTONBOX_BUTTONLAYOUT_IDX                        59
#define SBK_QFOCUSFRAME_IDX                                          115
#define SBK_QDOCKWIDGET_IDX                                          64
#define SBK_QDOCKWIDGET_DOCKWIDGETFEATURE_IDX                        65
#define SBK_QFLAGS_QDOCKWIDGET_DOCKWIDGETFEATURE__IDX                84
#define SBK_QGROUPBOX_IDX                                            190
#define SBK_QFONTCOMBOBOX_IDX                                        116
#define SBK_QFONTCOMBOBOX_FONTFILTER_IDX                             117
#define SBK_QFLAGS_QFONTCOMBOBOX_FONTFILTER__IDX                     87
#define SBK_QLABEL_IDX                                               205
#define SBK_QKEYSEQUENCEEDIT_IDX                                     201
#define SBK_QMAINWINDOW_IDX                                          221
#define SBK_QMAINWINDOW_DOCKOPTION_IDX                               222
#define SBK_QFLAGS_QMAINWINDOW_DOCKOPTION__IDX                       96
#define SBK_QLCDNUMBER_IDX                                           202
#define SBK_QLCDNUMBER_MODE_IDX                                      203
#define SBK_QLCDNUMBER_SEGMENTSTYLE_IDX                              204
#define SBK_QMDISUBWINDOW_IDX                                        227
#define SBK_QMDISUBWINDOW_SUBWINDOWOPTION_IDX                        228
#define SBK_QFLAGS_QMDISUBWINDOW_SUBWINDOWOPTION__IDX                98
#define SBK_QMENUBAR_IDX                                             230
#define SBK_QMENU_IDX                                                229
#define SBK_QRADIOBUTTON_IDX                                         248
#define SBK_QPROGRESSBAR_IDX                                         244
#define SBK_QPROGRESSBAR_DIRECTION_IDX                               245
#define SBK_QSIZEGRIP_IDX                                            254
#define SBK_QSPLITTER_IDX                                            264
#define SBK_QABSTRACTSCROLLAREA_IDX                                  14
#define SBK_QABSTRACTSCROLLAREA_SIZEADJUSTPOLICY_IDX                 15
#define SBK_QMDIAREA_IDX                                             223
#define SBK_QMDIAREA_AREAOPTION_IDX                                  224
#define SBK_QFLAGS_QMDIAREA_AREAOPTION__IDX                          97
#define SBK_QMDIAREA_WINDOWORDER_IDX                                 226
#define SBK_QMDIAREA_VIEWMODE_IDX                                    225
#define SBK_QSCROLLAREA_IDX                                          251
#define SBK_QGRAPHICSVIEW_IDX                                        182
#define SBK_QGRAPHICSVIEW_VIEWPORTANCHOR_IDX                         186
#define SBK_QGRAPHICSVIEW_CACHEMODEFLAG_IDX                          183
#define SBK_QFLAGS_QGRAPHICSVIEW_CACHEMODEFLAG__IDX                  94
#define SBK_QGRAPHICSVIEW_DRAGMODE_IDX                               184
#define SBK_QGRAPHICSVIEW_VIEWPORTUPDATEMODE_IDX                     187
#define SBK_QGRAPHICSVIEW_OPTIMIZATIONFLAG_IDX                       185
#define SBK_QFLAGS_QGRAPHICSVIEW_OPTIMIZATIONFLAG__IDX               95
#define SBK_QABSTRACTITEMVIEW_IDX                                    4
#define SBK_QABSTRACTITEMVIEW_SELECTIONMODE_IDX                      12
#define SBK_QABSTRACTITEMVIEW_SELECTIONBEHAVIOR_IDX                  11
#define SBK_QABSTRACTITEMVIEW_SCROLLHINT_IDX                         9
#define SBK_QABSTRACTITEMVIEW_EDITTRIGGER_IDX                        8
#define SBK_QFLAGS_QABSTRACTITEMVIEW_EDITTRIGGER__IDX                79
#define SBK_QABSTRACTITEMVIEW_SCROLLMODE_IDX                         10
#define SBK_QABSTRACTITEMVIEW_DRAGDROPMODE_IDX                       6
#define SBK_QABSTRACTITEMVIEW_CURSORACTION_IDX                       5
#define SBK_QABSTRACTITEMVIEW_STATE_IDX                              13
#define SBK_QABSTRACTITEMVIEW_DROPINDICATORPOSITION_IDX              7
#define SBK_QTREEVIEW_IDX                                            418
#define SBK_QTREEWIDGET_IDX                                          419
#define SBK_QHEADERVIEW_IDX                                          192
#define SBK_QHEADERVIEW_RESIZEMODE_IDX                               193
#define SBK_QLISTVIEW_IDX                                            212
#define SBK_QLISTVIEW_MOVEMENT_IDX                                   215
#define SBK_QLISTVIEW_FLOW_IDX                                       213
#define SBK_QLISTVIEW_RESIZEMODE_IDX                                 216
#define SBK_QLISTVIEW_LAYOUTMODE_IDX                                 214
#define SBK_QLISTVIEW_VIEWMODE_IDX                                   217
#define SBK_QUNDOVIEW_IDX                                            428
#define SBK_QLISTWIDGET_IDX                                          218
#define SBK_QCOLUMNVIEW_IDX                                          40
#define SBK_QTABLEVIEW_IDX                                           399
#define SBK_QTABLEWIDGET_IDX                                         400
#define SBK_QSPLASHSCREEN_IDX                                        263
#define SBK_QABSTRACTSPINBOX_IDX                                     19
#define SBK_QABSTRACTSPINBOX_STEPENABLEDFLAG_IDX                     22
#define SBK_QFLAGS_QABSTRACTSPINBOX_STEPENABLEDFLAG__IDX             80
#define SBK_QABSTRACTSPINBOX_BUTTONSYMBOLS_IDX                       20
#define SBK_QABSTRACTSPINBOX_CORRECTIONMODE_IDX                      21
#define SBK_QDOUBLESPINBOX_IDX                                       66
#define SBK_QSPINBOX_IDX                                             262
#define SBK_QDATETIMEEDIT_IDX                                        52
#define SBK_QDATETIMEEDIT_SECTION_IDX                                53
#define SBK_QFLAGS_QDATETIMEEDIT_SECTION__IDX                        82
#define SBK_QDATEEDIT_IDX                                            51
#define SBK_QTIMEEDIT_IDX                                            412
#define SBK_QSTACKEDWIDGET_IDX                                       268
#define SBK_QSPLITTERHANDLE_IDX                                      265
#define SBK_QABSTRACTSLIDER_IDX                                      16
#define SBK_QABSTRACTSLIDER_SLIDERACTION_IDX                         17
#define SBK_QABSTRACTSLIDER_SLIDERCHANGE_IDX                         18
#define SBK_QSLIDER_IDX                                              259
#define SBK_QSLIDER_TICKPOSITION_IDX                                 260
#define SBK_QDIAL_IDX                                                55
#define SBK_QSCROLLBAR_IDX                                           252
#define SBK_QSTATUSBAR_IDX                                           269
#define SBK_QTABBAR_IDX                                              392
#define SBK_QTABBAR_SHAPE_IDX                                        395
#define SBK_QTABBAR_BUTTONPOSITION_IDX                               393
#define SBK_QTABBAR_SELECTIONBEHAVIOR_IDX                            394
#define SBK_QTOOLBOX_IDX                                             414
#define SBK_QTOOLBAR_IDX                                             413
#define SBK_QRUBBERBAND_IDX                                          249
#define SBK_QRUBBERBAND_SHAPE_IDX                                    250
#define SBK_QTABWIDGET_IDX                                           396
#define SBK_QTABWIDGET_TABPOSITION_IDX                               397
#define SBK_QTABWIDGET_TABSHAPE_IDX                                  398
#define SBK_QTOOLBUTTON_IDX                                          415
#define SBK_QTOOLBUTTON_TOOLBUTTONPOPUPMODE_IDX                      416
#define SBK_QKEYEVENTTRANSITION_IDX                                  200
#define SBK_QMOUSEEVENTTRANSITION_IDX                                235
#define SBK_QSYSTEMTRAYICON_IDX                                      389
#define SBK_QSYSTEMTRAYICON_ACTIVATIONREASON_IDX                     390
#define SBK_QSYSTEMTRAYICON_MESSAGEICON_IDX                          391
#define SBK_QCOMPLETER_IDX                                           46
#define SBK_QCOMPLETER_COMPLETIONMODE_IDX                            47
#define SBK_QCOMPLETER_MODELSORTING_IDX                              48
#define SBK_QGRAPHICSEFFECT_IDX                                      139
#define SBK_QGRAPHICSEFFECT_CHANGEFLAG_IDX                           140
#define SBK_QFLAGS_QGRAPHICSEFFECT_CHANGEFLAG__IDX                   91
#define SBK_QGRAPHICSEFFECT_PIXMAPPADMODE_IDX                        141
#define SBK_QGRAPHICSBLUREFFECT_IDX                                  135
#define SBK_QGRAPHICSBLUREFFECT_BLURHINT_IDX                         136
#define SBK_QFLAGS_QGRAPHICSBLUREFFECT_BLURHINT__IDX                 90
#define SBK_QGRAPHICSCOLORIZEEFFECT_IDX                              137
#define SBK_QGRAPHICSOPACITYEFFECT_IDX                               157
#define SBK_QGRAPHICSDROPSHADOWEFFECT_IDX                            138
#define SBK_QUNDOGROUP_IDX                                           426
#define SBK_QUNDOSTACK_IDX                                           427
#define SBK_QBUTTONGROUP_IDX                                         32
#define SBK_QGRAPHICSOBJECT_IDX                                      156
#define SBK_QGRAPHICSTEXTITEM_IDX                                    180
#define SBK_QGRAPHICSWIDGET_IDX                                      188
#define SBK_QGRAPHICSPROXYWIDGET_IDX                                 162
#define SBK_QDATAWIDGETMAPPER_IDX                                    49
#define SBK_QDATAWIDGETMAPPER_SUBMITPOLICY_IDX                       50
#define SBK_QABSTRACTITEMDELEGATE_IDX                                2
#define SBK_QABSTRACTITEMDELEGATE_ENDEDITHINT_IDX                    3
#define SBK_QITEMDELEGATE_IDX                                        197
#define SBK_QSTYLEDITEMDELEGATE_IDX                                  386
#define SBK_QFILESYSTEMMODEL_IDX                                     77
#define SBK_QFILESYSTEMMODEL_ROLES_IDX                               78
#define SBK_QDIRMODEL_IDX                                            62
#define SBK_QDIRMODEL_ROLES_IDX                                      63
#define SBK_QTEXTEDIT_IDX                                            407
#define SBK_QTEXTEDIT_LINEWRAPMODE_IDX                               410
#define SBK_QTEXTEDIT_AUTOFORMATTINGFLAG_IDX                         408
#define SBK_QFLAGS_QTEXTEDIT_AUTOFORMATTINGFLAG__IDX                 111
#define SBK_QTEXTBROWSER_IDX                                         406
#define SBK_QTEXTEDIT_EXTRASELECTION_IDX                             409
#define SBK_QPLAINTEXTEDIT_IDX                                       242
#define SBK_QPLAINTEXTEDIT_LINEWRAPMODE_IDX                          243
#define SBK_QFILEDIALOG_IDX                                          68
#define SBK_QFILEDIALOG_VIEWMODE_IDX                                 73
#define SBK_QFILEDIALOG_FILEMODE_IDX                                 71
#define SBK_QFILEDIALOG_ACCEPTMODE_IDX                               69
#define SBK_QFILEDIALOG_DIALOGLABEL_IDX                              70
#define SBK_QFILEDIALOG_OPTION_IDX                                   72
#define SBK_QFLAGS_QFILEDIALOG_OPTION__IDX                           85
#define SBK_QtWidgets_IDX_COUNT                                      441

// This variable stores all Python types exported by this module.
extern PyTypeObject** SbkPySide2_QtWidgetsTypes;

// This variable stores all type converters exported by this module.
extern SbkConverter** SbkPySide2_QtWidgetsTypeConverters;

// Converter indices
#define SBK_QTWIDGETS_QLIST_QTREEWIDGETITEMPTR_IDX                   0 // const QList<QTreeWidgetItem * > &
#define SBK_QTWIDGETS_QLIST_QGRAPHICSITEMPTR_IDX                     1 // QList<QGraphicsItem * >
#define SBK_QTWIDGETS_QLIST_QGRAPHICSTRANSFORMPTR_IDX                2 // const QList<QGraphicsTransform * > &
#define SBK_QTWIDGETS_QVECTOR_QLINE_IDX                              3 // const QVector<QLine > &
#define SBK_QTWIDGETS_QVECTOR_QLINEF_IDX                             4 // const QVector<QLineF > &
#define SBK_QTWIDGETS_QVECTOR_QPOINT_IDX                             5 // const QVector<QPoint > &
#define SBK_QTWIDGETS_QVECTOR_QPOINTF_IDX                            6 // const QVector<QPointF > &
#define SBK_QTWIDGETS_QVECTOR_QRECT_IDX                              7 // const QVector<QRect > &
#define SBK_QTWIDGETS_QVECTOR_QRECTF_IDX                             8 // const QVector<QRectF > &
#define SBK_QTWIDGETS_QLIST_QGESTUREPTR_IDX                          9 // const QList<QGesture * > &
#define SBK_QTWIDGETS_QLIST_QOBJECTPTR_IDX                           10 // const QList<QObject * > &
#define SBK_QTWIDGETS_QLIST_QBYTEARRAY_IDX                           11 // QList<QByteArray >
#define SBK_QTWIDGETS_QPAIR_QREAL_QPOINTF_IDX                        12 // QPair<qreal, QPointF >
#define SBK_QTWIDGETS_QLIST_QPAIR_QREAL_QPOINTF_IDX                  13 // QList<QPair<qreal, QPointF > >
#define SBK_QTWIDGETS_QPAIR_QREAL_QREAL_IDX                          14 // QPair<qreal, qreal >
#define SBK_QTWIDGETS_QLIST_QPAIR_QREAL_QREAL_IDX                    15 // QList<QPair<qreal, qreal > >
#define SBK_QTWIDGETS_QLIST_QGRAPHICSWIDGETPTR_IDX                   16 // QList<QGraphicsWidget * >
#define SBK_QTWIDGETS_QLIST_QWIDGETPTR_IDX                           17 // QList<QWidget * >
#define SBK_QTWIDGETS_QLIST_QKEYSEQUENCE_IDX                         18 // const QList<QKeySequence > &
#define SBK_QTWIDGETS_QLIST_QRECTF_IDX                               19 // const QList<QRectF > &
#define SBK_QTWIDGETS_QLIST_QGRAPHICSVIEWPTR_IDX                     20 // QList<QGraphicsView * >
#define SBK_QTWIDGETS_QLIST_QACTIONPTR_IDX                           21 // QList<QAction * >
#define SBK_QTWIDGETS_QLIST_QWINDOWPTR_IDX                           22 // QList<QWindow * >
#define SBK_QTWIDGETS_QLIST_QSCREENPTR_IDX                           23 // QList<QScreen * >
#define SBK_QTWIDGETS_QLIST_QABSTRACTBUTTONPTR_IDX                   24 // QList<QAbstractButton * >
#define SBK_QTWIDGETS_QLIST_INT_IDX                                  25 // QList<int >
#define SBK_QTWIDGETS_QLIST_QWIZARD_WIZARDBUTTON_IDX                 26 // const QList<QWizard::WizardButton > &
#define SBK_QTWIDGETS_QMAP_QDATE_QTEXTCHARFORMAT_IDX                 27 // QMap<QDate, QTextCharFormat >
#define SBK_QTWIDGETS_QLIST_QDOCKWIDGETPTR_IDX                       28 // const QList<QDockWidget * > &
#define SBK_QTWIDGETS_QLIST_QMDISUBWINDOWPTR_IDX                     29 // QList<QMdiSubWindow * >
#define SBK_QTWIDGETS_QVECTOR_INT_IDX                                30 // const QVector<int > &
#define SBK_QTWIDGETS_QLIST_QLISTWIDGETITEMPTR_IDX                   31 // QList<QListWidgetItem * >
#define SBK_QTWIDGETS_QLIST_QTABLEWIDGETITEMPTR_IDX                  32 // QList<QTableWidgetItem * >
#define SBK_QTWIDGETS_QLIST_QTABLEWIDGETSELECTIONRANGE_IDX           33 // QList<QTableWidgetSelectionRange >
#define SBK_QTWIDGETS_QLIST_QABSTRACTANIMATIONPTR_IDX                34 // QList<QAbstractAnimation * >
#define SBK_QTWIDGETS_QLIST_QABSTRACTSTATEPTR_IDX                    35 // const QList<QAbstractState * > &
#define SBK_QTWIDGETS_QLIST_QUNDOSTACKPTR_IDX                        36 // QList<QUndoStack * >
#define SBK_QTWIDGETS_QHASH_INT_QBYTEARRAY_IDX                       37 // const QHash<int, QByteArray > &
#define SBK_QTWIDGETS_QMAP_INT_QVARIANT_IDX                          38 // QMap<int, QVariant >
#define SBK_QTWIDGETS_QLIST_QPERSISTENTMODELINDEX_IDX                39 // const QList<QPersistentModelIndex > &
#define SBK_QTWIDGETS_QLIST_QTEXTEDIT_EXTRASELECTION_IDX             40 // QList<QTextEdit::ExtraSelection >
#define SBK_QTWIDGETS_QLIST_QURL_IDX                                 41 // QList<QUrl >
#define SBK_QTWIDGETS_QLIST_QVARIANT_IDX                             42 // QList<QVariant >
#define SBK_QTWIDGETS_QLIST_QSTRING_IDX                              43 // QList<QString >
#define SBK_QTWIDGETS_QMAP_QSTRING_QVARIANT_IDX                      44 // QMap<QString, QVariant >
#define SBK_QtWidgets_CONVERTERS_IDX_COUNT                           45

// Macros for type check

// Protected enum surrogates
enum PySide2_QtWidgets_QGraphicsItem_Extension_Surrogate {};
enum PySide2_QtWidgets_QAbstractItemView_CursorAction_Surrogate {};
enum PySide2_QtWidgets_QAbstractItemView_State_Surrogate {};
enum PySide2_QtWidgets_QAbstractItemView_DropIndicatorPosition_Surrogate {};
enum PySide2_QtWidgets_QAbstractSlider_SliderChange_Surrogate {};

namespace Shiboken
{

// PyType functions, to get the PyObjectType for a type T
template<> inline PyTypeObject* SbkType< ::QUndoCommand >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QUNDOCOMMAND_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleFactory >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEFACTORY_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTileRules >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTILERULES_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWhatsThis >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QWHATSTHIS_IDX]); }
template<> inline PyTypeObject* SbkType< ::QToolTip >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTOOLTIP_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGestureRecognizer::ResultFlag >() { return SbkPySide2_QtWidgetsTypes[SBK_QGESTURERECOGNIZER_RESULTFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QGestureRecognizer::ResultFlag> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QGESTURERECOGNIZER_RESULTFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QGestureRecognizer >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGESTURERECOGNIZER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QLayoutItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QLAYOUTITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWidgetItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QWIDGETITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTreeWidgetItem::ItemType >() { return SbkPySide2_QtWidgetsTypes[SBK_QTREEWIDGETITEM_ITEMTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTreeWidgetItem::ChildIndicatorPolicy >() { return SbkPySide2_QtWidgetsTypes[SBK_QTREEWIDGETITEM_CHILDINDICATORPOLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTreeWidgetItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTREEWIDGETITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTreeWidgetItemIterator::IteratorFlag >() { return SbkPySide2_QtWidgetsTypes[SBK_QTREEWIDGETITEMITERATOR_ITERATORFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QTreeWidgetItemIterator::IteratorFlag> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QTREEWIDGETITEMITERATOR_ITERATORFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QTreeWidgetItemIterator >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTREEWIDGETITEMITERATOR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTableWidgetItem::ItemType >() { return SbkPySide2_QtWidgetsTypes[SBK_QTABLEWIDGETITEM_ITEMTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTableWidgetItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTABLEWIDGETITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTableWidgetSelectionRange >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTABLEWIDGETSELECTIONRANGE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QListWidgetItem::ItemType >() { return SbkPySide2_QtWidgetsTypes[SBK_QLISTWIDGETITEM_ITEMTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QListWidgetItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QLISTWIDGETITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QItemEditorFactory >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QITEMEDITORFACTORY_IDX]); }
template<> inline PyTypeObject* SbkType< ::QItemEditorCreatorBase >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QITEMEDITORCREATORBASE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QFileIconProvider::IconType >() { return SbkPySide2_QtWidgetsTypes[SBK_QFILEICONPROVIDER_ICONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFileIconProvider::Option >() { return SbkPySide2_QtWidgetsTypes[SBK_QFILEICONPROVIDER_OPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QFileIconProvider::Option> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QFILEICONPROVIDER_OPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QFileIconProvider >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QFILEICONPROVIDER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOption::OptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTION_OPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOption::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTION_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOption::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTION_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOption >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionTabWidgetFrame::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTABWIDGETFRAME_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionTabWidgetFrame::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTABWIDGETFRAME_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionTabWidgetFrame >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTABWIDGETFRAME_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionFrame::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONFRAME_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionFrame::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONFRAME_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionFrame::FrameFeature >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONFRAME_FRAMEFEATURE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QStyleOptionFrame::FrameFeature> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QSTYLEOPTIONFRAME_FRAMEFEATURE__IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionFrame >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONFRAME_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionHeader::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONHEADER_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionHeader::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONHEADER_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionHeader::SectionPosition >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONHEADER_SECTIONPOSITION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionHeader::SelectedPosition >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONHEADER_SELECTEDPOSITION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionHeader::SortIndicator >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONHEADER_SORTINDICATOR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionHeader >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONHEADER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionGraphicsItem::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONGRAPHICSITEM_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionGraphicsItem::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONGRAPHICSITEM_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionGraphicsItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONGRAPHICSITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionTabBarBase::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTABBARBASE_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionTabBarBase::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTABBARBASE_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionTabBarBase >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTABBARBASE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionTab::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTAB_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionTab::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTAB_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionTab::TabPosition >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTAB_TABPOSITION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionTab::SelectedPosition >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTAB_SELECTEDPOSITION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionTab::CornerWidget >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTAB_CORNERWIDGET_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QStyleOptionTab::CornerWidget> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QSTYLEOPTIONTAB_CORNERWIDGET__IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionTab::TabFeature >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTAB_TABFEATURE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QStyleOptionTab::TabFeature> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QSTYLEOPTIONTAB_TABFEATURE__IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionTab >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTAB_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionButton::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONBUTTON_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionButton::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONBUTTON_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionButton::ButtonFeature >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONBUTTON_BUTTONFEATURE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QStyleOptionButton::ButtonFeature> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QSTYLEOPTIONBUTTON_BUTTONFEATURE__IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionButton >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONBUTTON_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleHintReturn::HintReturnType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEHINTRETURN_HINTRETURNTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleHintReturn::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEHINTRETURN_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleHintReturn::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEHINTRETURN_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleHintReturn >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEHINTRETURN_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleHintReturnMask::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEHINTRETURNMASK_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleHintReturnMask::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEHINTRETURNMASK_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleHintReturnMask >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEHINTRETURNMASK_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleHintReturnVariant::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEHINTRETURNVARIANT_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleHintReturnVariant::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEHINTRETURNVARIANT_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleHintReturnVariant >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEHINTRETURNVARIANT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionProgressBar::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONPROGRESSBAR_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionProgressBar::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONPROGRESSBAR_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionProgressBar >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONPROGRESSBAR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionToolBar::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTOOLBAR_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionToolBar::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTOOLBAR_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionToolBar::ToolBarPosition >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTOOLBAR_TOOLBARPOSITION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionToolBar::ToolBarFeature >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTOOLBAR_TOOLBARFEATURE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QStyleOptionToolBar::ToolBarFeature> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QSTYLEOPTIONTOOLBAR_TOOLBARFEATURE__IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionToolBar >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTOOLBAR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionDockWidget::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONDOCKWIDGET_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionDockWidget::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONDOCKWIDGET_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionDockWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONDOCKWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionMenuItem::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONMENUITEM_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionMenuItem::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONMENUITEM_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionMenuItem::MenuItemType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONMENUITEM_MENUITEMTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionMenuItem::CheckType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONMENUITEM_CHECKTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionMenuItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONMENUITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionToolBox::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTOOLBOX_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionToolBox::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTOOLBOX_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionToolBox::TabPosition >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTOOLBOX_TABPOSITION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionToolBox::SelectedPosition >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTOOLBOX_SELECTEDPOSITION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionToolBox >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTOOLBOX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionViewItem::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONVIEWITEM_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionViewItem::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONVIEWITEM_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionViewItem::Position >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONVIEWITEM_POSITION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionViewItem::ViewItemFeature >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONVIEWITEM_VIEWITEMFEATURE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QStyleOptionViewItem::ViewItemFeature> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QSTYLEOPTIONVIEWITEM_VIEWITEMFEATURE__IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionViewItem::ViewItemPosition >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONVIEWITEM_VIEWITEMPOSITION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionViewItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONVIEWITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionComplex::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONCOMPLEX_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionComplex::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONCOMPLEX_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionComplex >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONCOMPLEX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionComboBox::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONCOMBOBOX_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionComboBox::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONCOMBOBOX_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionComboBox >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONCOMBOBOX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionToolButton::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTOOLBUTTON_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionToolButton::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTOOLBUTTON_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionToolButton::ToolButtonFeature >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTOOLBUTTON_TOOLBUTTONFEATURE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QStyleOptionToolButton::ToolButtonFeature> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QSTYLEOPTIONTOOLBUTTON_TOOLBUTTONFEATURE__IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionToolButton >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTOOLBUTTON_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionGroupBox::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONGROUPBOX_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionGroupBox::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONGROUPBOX_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionGroupBox >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONGROUPBOX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionTitleBar::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTITLEBAR_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionTitleBar::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTITLEBAR_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionTitleBar >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONTITLEBAR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionSizeGrip::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONSIZEGRIP_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionSizeGrip::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONSIZEGRIP_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionSizeGrip >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONSIZEGRIP_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionSpinBox::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONSPINBOX_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionSpinBox::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONSPINBOX_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionSpinBox >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONSPINBOX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionSlider::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONSLIDER_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionSlider::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONSLIDER_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionSlider >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONSLIDER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionRubberBand::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONRUBBERBAND_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionRubberBand::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONRUBBERBAND_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionRubberBand >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONRUBBERBAND_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyleOptionFocusRect::StyleOptionType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONFOCUSRECT_STYLEOPTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionFocusRect::StyleOptionVersion >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONFOCUSRECT_STYLEOPTIONVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyleOptionFocusRect >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEOPTIONFOCUSRECT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSizePolicy::PolicyFlag >() { return SbkPySide2_QtWidgetsTypes[SBK_QSIZEPOLICY_POLICYFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSizePolicy::Policy >() { return SbkPySide2_QtWidgetsTypes[SBK_QSIZEPOLICY_POLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSizePolicy::ControlType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSIZEPOLICY_CONTROLTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QSizePolicy::ControlType> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QSIZEPOLICY_CONTROLTYPE__IDX]; }
template<> inline PyTypeObject* SbkType< ::QSizePolicy >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSIZEPOLICY_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSpacerItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSPACERITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsLayoutItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSLAYOUTITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsLayout >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSLAYOUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsAnchorLayout >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSANCHORLAYOUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsGridLayout >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSGRIDLAYOUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsLinearLayout >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSLINEARLAYOUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsItem::GraphicsItemFlag >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSITEM_GRAPHICSITEMFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QGraphicsItem::GraphicsItemFlag> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QGRAPHICSITEM_GRAPHICSITEMFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QGraphicsItem::GraphicsItemChange >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSITEM_GRAPHICSITEMCHANGE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QGraphicsItem::CacheMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSITEM_CACHEMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QGraphicsItem::PanelModality >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSITEM_PANELMODALITY_IDX]; }
template<> inline PyTypeObject* SbkType< ::PySide2_QtWidgets_QGraphicsItem_Extension_Surrogate >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSITEM_EXTENSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QGraphicsItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractGraphicsShapeItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTGRAPHICSSHAPEITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsSimpleTextItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSSIMPLETEXTITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsPathItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSPATHITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsEllipseItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSELLIPSEITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsRectItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSRECTITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsPolygonItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSPOLYGONITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsLineItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSLINEITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsPixmapItem::ShapeMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSPIXMAPITEM_SHAPEMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QGraphicsPixmapItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSPIXMAPITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsItemGroup >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSITEMGROUP_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStylePainter >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEPAINTER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGestureEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGESTUREEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsSceneEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSSCENEEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsSceneResizeEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSSCENERESIZEEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsSceneDragDropEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSSCENEDRAGDROPEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsSceneMoveEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSSCENEMOVEEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsSceneMouseEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSSCENEMOUSEEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsSceneContextMenuEvent::Reason >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSSCENECONTEXTMENUEVENT_REASON_IDX]; }
template<> inline PyTypeObject* SbkType< ::QGraphicsSceneContextMenuEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSSCENECONTEXTMENUEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsSceneWheelEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSSCENEWHEELEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsSceneHelpEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSSCENEHELPEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsSceneHoverEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSSCENEHOVEREVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsAnchor >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSANCHOR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsItemAnimation >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSITEMANIMATION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAction::MenuRole >() { return SbkPySide2_QtWidgetsTypes[SBK_QACTION_MENUROLE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAction::Priority >() { return SbkPySide2_QtWidgetsTypes[SBK_QACTION_PRIORITY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAction::ActionEvent >() { return SbkPySide2_QtWidgetsTypes[SBK_QACTION_ACTIONEVENT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAction >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QACTION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWidgetAction >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QWIDGETACTION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsScene::ItemIndexMethod >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSSCENE_ITEMINDEXMETHOD_IDX]; }
template<> inline PyTypeObject* SbkType< ::QGraphicsScene::SceneLayer >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSSCENE_SCENELAYER_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QGraphicsScene::SceneLayer> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QGRAPHICSSCENE_SCENELAYER__IDX]; }
template<> inline PyTypeObject* SbkType< ::QGraphicsScene >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSSCENE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QPlainTextDocumentLayout >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QPLAINTEXTDOCUMENTLAYOUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QActionGroup >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QACTIONGROUP_IDX]); }
template<> inline PyTypeObject* SbkType< ::QLayout::SizeConstraint >() { return SbkPySide2_QtWidgetsTypes[SBK_QLAYOUT_SIZECONSTRAINT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QLayout >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QLAYOUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QFormLayout::FieldGrowthPolicy >() { return SbkPySide2_QtWidgetsTypes[SBK_QFORMLAYOUT_FIELDGROWTHPOLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFormLayout::RowWrapPolicy >() { return SbkPySide2_QtWidgetsTypes[SBK_QFORMLAYOUT_ROWWRAPPOLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFormLayout::ItemRole >() { return SbkPySide2_QtWidgetsTypes[SBK_QFORMLAYOUT_ITEMROLE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFormLayout >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QFORMLAYOUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStackedLayout::StackingMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTACKEDLAYOUT_STACKINGMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStackedLayout >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTACKEDLAYOUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QBoxLayout::Direction >() { return SbkPySide2_QtWidgetsTypes[SBK_QBOXLAYOUT_DIRECTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QBoxLayout >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QBOXLAYOUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QVBoxLayout >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QVBOXLAYOUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QHBoxLayout >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QHBOXLAYOUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGridLayout >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRIDLAYOUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsTransform >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSTRANSFORM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsRotation >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSROTATION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsScale >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSSCALE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QApplication::ColorSpec >() { return SbkPySide2_QtWidgetsTypes[SBK_QAPPLICATION_COLORSPEC_IDX]; }
template<> inline PyTypeObject* SbkType< ::QApplication >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QAPPLICATION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGesture::GestureCancelPolicy >() { return SbkPySide2_QtWidgetsTypes[SBK_QGESTURE_GESTURECANCELPOLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QGesture >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGESTURE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QPanGesture >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QPANGESTURE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSwipeGesture::SwipeDirection >() { return SbkPySide2_QtWidgetsTypes[SBK_QSWIPEGESTURE_SWIPEDIRECTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSwipeGesture >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSWIPEGESTURE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QPinchGesture::ChangeFlag >() { return SbkPySide2_QtWidgetsTypes[SBK_QPINCHGESTURE_CHANGEFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QPinchGesture::ChangeFlag> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QPINCHGESTURE_CHANGEFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QPinchGesture >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QPINCHGESTURE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTapAndHoldGesture >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTAPANDHOLDGESTURE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTapGesture >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTAPGESTURE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QShortcut >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSHORTCUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyle::StateFlag >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLE_STATEFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QStyle::StateFlag> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QSTYLE_STATEFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyle::PrimitiveElement >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLE_PRIMITIVEELEMENT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyle::ControlElement >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLE_CONTROLELEMENT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyle::SubElement >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLE_SUBELEMENT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyle::ComplexControl >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLE_COMPLEXCONTROL_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyle::SubControl >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLE_SUBCONTROL_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QStyle::SubControl> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QSTYLE_SUBCONTROL__IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyle::PixelMetric >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLE_PIXELMETRIC_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyle::ContentsType >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLE_CONTENTSTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyle::RequestSoftwareInputPanel >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLE_REQUESTSOFTWAREINPUTPANEL_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyle::StyleHint >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLE_STYLEHINT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyle::StandardPixmap >() { return SbkPySide2_QtWidgetsTypes[SBK_QSTYLE_STANDARDPIXMAP_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStyle >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCommonStyle >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QCOMMONSTYLE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWidget::RenderFlag >() { return SbkPySide2_QtWidgetsTypes[SBK_QWIDGET_RENDERFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QWidget::RenderFlag> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QWIDGET_RENDERFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QDesktopWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QDESKTOPWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QDialog::DialogCode >() { return SbkPySide2_QtWidgetsTypes[SBK_QDIALOG_DIALOGCODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QDialog >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QDIALOG_IDX]); }
template<> inline PyTypeObject* SbkType< ::QColorDialog::ColorDialogOption >() { return SbkPySide2_QtWidgetsTypes[SBK_QCOLORDIALOG_COLORDIALOGOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QColorDialog::ColorDialogOption> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QCOLORDIALOG_COLORDIALOGOPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QColorDialog >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QCOLORDIALOG_IDX]); }
template<> inline PyTypeObject* SbkType< ::QOpenGLWidget::UpdateBehavior >() { return SbkPySide2_QtWidgetsTypes[SBK_QOPENGLWIDGET_UPDATEBEHAVIOR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QOpenGLWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QOPENGLWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QErrorMessage >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QERRORMESSAGE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QFontDialog::FontDialogOption >() { return SbkPySide2_QtWidgetsTypes[SBK_QFONTDIALOG_FONTDIALOGOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QFontDialog::FontDialogOption> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QFONTDIALOG_FONTDIALOGOPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QFontDialog >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QFONTDIALOG_IDX]); }
template<> inline PyTypeObject* SbkType< ::QLineEdit::ActionPosition >() { return SbkPySide2_QtWidgetsTypes[SBK_QLINEEDIT_ACTIONPOSITION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QLineEdit::EchoMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QLINEEDIT_ECHOMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QLineEdit >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QLINEEDIT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QFrame::Shape >() { return SbkPySide2_QtWidgetsTypes[SBK_QFRAME_SHAPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFrame::Shadow >() { return SbkPySide2_QtWidgetsTypes[SBK_QFRAME_SHADOW_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFrame::StyleMask >() { return SbkPySide2_QtWidgetsTypes[SBK_QFRAME_STYLEMASK_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFrame >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QFRAME_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMessageBox::Icon >() { return SbkPySide2_QtWidgetsTypes[SBK_QMESSAGEBOX_ICON_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMessageBox::ButtonRole >() { return SbkPySide2_QtWidgetsTypes[SBK_QMESSAGEBOX_BUTTONROLE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMessageBox::StandardButton >() { return SbkPySide2_QtWidgetsTypes[SBK_QMESSAGEBOX_STANDARDBUTTON_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QMessageBox::StandardButton> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QMESSAGEBOX_STANDARDBUTTON__IDX]; }
template<> inline PyTypeObject* SbkType< ::QMessageBox >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QMESSAGEBOX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QInputDialog::InputDialogOption >() { return SbkPySide2_QtWidgetsTypes[SBK_QINPUTDIALOG_INPUTDIALOGOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QInputDialog::InputMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QINPUTDIALOG_INPUTMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QInputDialog >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QINPUTDIALOG_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWizard::WizardButton >() { return SbkPySide2_QtWidgetsTypes[SBK_QWIZARD_WIZARDBUTTON_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWizard::WizardPixmap >() { return SbkPySide2_QtWidgetsTypes[SBK_QWIZARD_WIZARDPIXMAP_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWizard::WizardStyle >() { return SbkPySide2_QtWidgetsTypes[SBK_QWIZARD_WIZARDSTYLE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWizard::WizardOption >() { return SbkPySide2_QtWidgetsTypes[SBK_QWIZARD_WIZARDOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QWizard::WizardOption> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QWIZARD_WIZARDOPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QWizard >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QWIZARD_IDX]); }
template<> inline PyTypeObject* SbkType< ::QProgressDialog >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QPROGRESSDIALOG_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWizardPage >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QWIZARDPAGE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractButton >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTBUTTON_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCheckBox >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QCHECKBOX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCalendarWidget::HorizontalHeaderFormat >() { return SbkPySide2_QtWidgetsTypes[SBK_QCALENDARWIDGET_HORIZONTALHEADERFORMAT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCalendarWidget::VerticalHeaderFormat >() { return SbkPySide2_QtWidgetsTypes[SBK_QCALENDARWIDGET_VERTICALHEADERFORMAT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCalendarWidget::SelectionMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QCALENDARWIDGET_SELECTIONMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCalendarWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QCALENDARWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QPushButton >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QPUSHBUTTON_IDX]); }
template<> inline PyTypeObject* SbkType< ::QComboBox::InsertPolicy >() { return SbkPySide2_QtWidgetsTypes[SBK_QCOMBOBOX_INSERTPOLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QComboBox::SizeAdjustPolicy >() { return SbkPySide2_QtWidgetsTypes[SBK_QCOMBOBOX_SIZEADJUSTPOLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QComboBox >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QCOMBOBOX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCommandLinkButton >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QCOMMANDLINKBUTTON_IDX]); }
template<> inline PyTypeObject* SbkType< ::QDialogButtonBox::ButtonRole >() { return SbkPySide2_QtWidgetsTypes[SBK_QDIALOGBUTTONBOX_BUTTONROLE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QDialogButtonBox::StandardButton >() { return SbkPySide2_QtWidgetsTypes[SBK_QDIALOGBUTTONBOX_STANDARDBUTTON_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QDialogButtonBox::StandardButton> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QDIALOGBUTTONBOX_STANDARDBUTTON__IDX]; }
template<> inline PyTypeObject* SbkType< ::QDialogButtonBox::ButtonLayout >() { return SbkPySide2_QtWidgetsTypes[SBK_QDIALOGBUTTONBOX_BUTTONLAYOUT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QDialogButtonBox >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QDIALOGBUTTONBOX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QFocusFrame >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QFOCUSFRAME_IDX]); }
template<> inline PyTypeObject* SbkType< ::QDockWidget::DockWidgetFeature >() { return SbkPySide2_QtWidgetsTypes[SBK_QDOCKWIDGET_DOCKWIDGETFEATURE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QDockWidget::DockWidgetFeature> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QDOCKWIDGET_DOCKWIDGETFEATURE__IDX]; }
template<> inline PyTypeObject* SbkType< ::QDockWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QDOCKWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGroupBox >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGROUPBOX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QFontComboBox::FontFilter >() { return SbkPySide2_QtWidgetsTypes[SBK_QFONTCOMBOBOX_FONTFILTER_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QFontComboBox::FontFilter> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QFONTCOMBOBOX_FONTFILTER__IDX]; }
template<> inline PyTypeObject* SbkType< ::QFontComboBox >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QFONTCOMBOBOX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QLabel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QLABEL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QKeySequenceEdit >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QKEYSEQUENCEEDIT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMainWindow::DockOption >() { return SbkPySide2_QtWidgetsTypes[SBK_QMAINWINDOW_DOCKOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QMainWindow::DockOption> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QMAINWINDOW_DOCKOPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QMainWindow >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QMAINWINDOW_IDX]); }
template<> inline PyTypeObject* SbkType< ::QLCDNumber::Mode >() { return SbkPySide2_QtWidgetsTypes[SBK_QLCDNUMBER_MODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QLCDNumber::SegmentStyle >() { return SbkPySide2_QtWidgetsTypes[SBK_QLCDNUMBER_SEGMENTSTYLE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QLCDNumber >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QLCDNUMBER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMdiSubWindow::SubWindowOption >() { return SbkPySide2_QtWidgetsTypes[SBK_QMDISUBWINDOW_SUBWINDOWOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QMdiSubWindow::SubWindowOption> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QMDISUBWINDOW_SUBWINDOWOPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QMdiSubWindow >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QMDISUBWINDOW_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMenuBar >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QMENUBAR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMenu >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QMENU_IDX]); }
template<> inline PyTypeObject* SbkType< ::QRadioButton >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QRADIOBUTTON_IDX]); }
template<> inline PyTypeObject* SbkType< ::QProgressBar::Direction >() { return SbkPySide2_QtWidgetsTypes[SBK_QPROGRESSBAR_DIRECTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QProgressBar >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QPROGRESSBAR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSizeGrip >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSIZEGRIP_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSplitter >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSPLITTER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractScrollArea::SizeAdjustPolicy >() { return SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTSCROLLAREA_SIZEADJUSTPOLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractScrollArea >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTSCROLLAREA_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMdiArea::AreaOption >() { return SbkPySide2_QtWidgetsTypes[SBK_QMDIAREA_AREAOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QMdiArea::AreaOption> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QMDIAREA_AREAOPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QMdiArea::WindowOrder >() { return SbkPySide2_QtWidgetsTypes[SBK_QMDIAREA_WINDOWORDER_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMdiArea::ViewMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QMDIAREA_VIEWMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMdiArea >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QMDIAREA_IDX]); }
template<> inline PyTypeObject* SbkType< ::QScrollArea >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSCROLLAREA_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsView::ViewportAnchor >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSVIEW_VIEWPORTANCHOR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QGraphicsView::CacheModeFlag >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSVIEW_CACHEMODEFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QGraphicsView::CacheModeFlag> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QGRAPHICSVIEW_CACHEMODEFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QGraphicsView::DragMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSVIEW_DRAGMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QGraphicsView::ViewportUpdateMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSVIEW_VIEWPORTUPDATEMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QGraphicsView::OptimizationFlag >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSVIEW_OPTIMIZATIONFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QGraphicsView::OptimizationFlag> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QGRAPHICSVIEW_OPTIMIZATIONFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QGraphicsView >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSVIEW_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractItemView::SelectionMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTITEMVIEW_SELECTIONMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractItemView::SelectionBehavior >() { return SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTITEMVIEW_SELECTIONBEHAVIOR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractItemView::ScrollHint >() { return SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTITEMVIEW_SCROLLHINT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractItemView::EditTrigger >() { return SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTITEMVIEW_EDITTRIGGER_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QAbstractItemView::EditTrigger> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QABSTRACTITEMVIEW_EDITTRIGGER__IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractItemView::ScrollMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTITEMVIEW_SCROLLMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractItemView::DragDropMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTITEMVIEW_DRAGDROPMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::PySide2_QtWidgets_QAbstractItemView_CursorAction_Surrogate >() { return SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTITEMVIEW_CURSORACTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::PySide2_QtWidgets_QAbstractItemView_State_Surrogate >() { return SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTITEMVIEW_STATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::PySide2_QtWidgets_QAbstractItemView_DropIndicatorPosition_Surrogate >() { return SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTITEMVIEW_DROPINDICATORPOSITION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractItemView >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTITEMVIEW_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTreeView >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTREEVIEW_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTreeWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTREEWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QHeaderView::ResizeMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QHEADERVIEW_RESIZEMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QHeaderView >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QHEADERVIEW_IDX]); }
template<> inline PyTypeObject* SbkType< ::QListView::Movement >() { return SbkPySide2_QtWidgetsTypes[SBK_QLISTVIEW_MOVEMENT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QListView::Flow >() { return SbkPySide2_QtWidgetsTypes[SBK_QLISTVIEW_FLOW_IDX]; }
template<> inline PyTypeObject* SbkType< ::QListView::ResizeMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QLISTVIEW_RESIZEMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QListView::LayoutMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QLISTVIEW_LAYOUTMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QListView::ViewMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QLISTVIEW_VIEWMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QListView >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QLISTVIEW_IDX]); }
template<> inline PyTypeObject* SbkType< ::QUndoView >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QUNDOVIEW_IDX]); }
template<> inline PyTypeObject* SbkType< ::QListWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QLISTWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QColumnView >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QCOLUMNVIEW_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTableView >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTABLEVIEW_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTableWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTABLEWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSplashScreen >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSPLASHSCREEN_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractSpinBox::StepEnabledFlag >() { return SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTSPINBOX_STEPENABLEDFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QAbstractSpinBox::StepEnabledFlag> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QABSTRACTSPINBOX_STEPENABLEDFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractSpinBox::ButtonSymbols >() { return SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTSPINBOX_BUTTONSYMBOLS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractSpinBox::CorrectionMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTSPINBOX_CORRECTIONMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractSpinBox >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTSPINBOX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QDoubleSpinBox >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QDOUBLESPINBOX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSpinBox >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSPINBOX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QDateTimeEdit::Section >() { return SbkPySide2_QtWidgetsTypes[SBK_QDATETIMEEDIT_SECTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QDateTimeEdit::Section> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QDATETIMEEDIT_SECTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QDateTimeEdit >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QDATETIMEEDIT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QDateEdit >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QDATEEDIT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTimeEdit >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTIMEEDIT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStackedWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTACKEDWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSplitterHandle >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSPLITTERHANDLE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractSlider::SliderAction >() { return SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTSLIDER_SLIDERACTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::PySide2_QtWidgets_QAbstractSlider_SliderChange_Surrogate >() { return SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTSLIDER_SLIDERCHANGE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractSlider >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTSLIDER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSlider::TickPosition >() { return SbkPySide2_QtWidgetsTypes[SBK_QSLIDER_TICKPOSITION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSlider >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSLIDER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QDial >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QDIAL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QScrollBar >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSCROLLBAR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStatusBar >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTATUSBAR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTabBar::Shape >() { return SbkPySide2_QtWidgetsTypes[SBK_QTABBAR_SHAPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTabBar::ButtonPosition >() { return SbkPySide2_QtWidgetsTypes[SBK_QTABBAR_BUTTONPOSITION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTabBar::SelectionBehavior >() { return SbkPySide2_QtWidgetsTypes[SBK_QTABBAR_SELECTIONBEHAVIOR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTabBar >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTABBAR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QToolBox >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTOOLBOX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QToolBar >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTOOLBAR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QRubberBand::Shape >() { return SbkPySide2_QtWidgetsTypes[SBK_QRUBBERBAND_SHAPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QRubberBand >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QRUBBERBAND_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTabWidget::TabPosition >() { return SbkPySide2_QtWidgetsTypes[SBK_QTABWIDGET_TABPOSITION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTabWidget::TabShape >() { return SbkPySide2_QtWidgetsTypes[SBK_QTABWIDGET_TABSHAPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTabWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTABWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QToolButton::ToolButtonPopupMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QTOOLBUTTON_TOOLBUTTONPOPUPMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QToolButton >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTOOLBUTTON_IDX]); }
template<> inline PyTypeObject* SbkType< ::QKeyEventTransition >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QKEYEVENTTRANSITION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMouseEventTransition >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QMOUSEEVENTTRANSITION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSystemTrayIcon::ActivationReason >() { return SbkPySide2_QtWidgetsTypes[SBK_QSYSTEMTRAYICON_ACTIVATIONREASON_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSystemTrayIcon::MessageIcon >() { return SbkPySide2_QtWidgetsTypes[SBK_QSYSTEMTRAYICON_MESSAGEICON_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSystemTrayIcon >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSYSTEMTRAYICON_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCompleter::CompletionMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QCOMPLETER_COMPLETIONMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCompleter::ModelSorting >() { return SbkPySide2_QtWidgetsTypes[SBK_QCOMPLETER_MODELSORTING_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCompleter >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QCOMPLETER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsEffect::ChangeFlag >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSEFFECT_CHANGEFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QGraphicsEffect::ChangeFlag> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QGRAPHICSEFFECT_CHANGEFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QGraphicsEffect::PixmapPadMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSEFFECT_PIXMAPPADMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QGraphicsEffect >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSEFFECT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsBlurEffect::BlurHint >() { return SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSBLUREFFECT_BLURHINT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QGraphicsBlurEffect::BlurHint> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QGRAPHICSBLUREFFECT_BLURHINT__IDX]; }
template<> inline PyTypeObject* SbkType< ::QGraphicsBlurEffect >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSBLUREFFECT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsColorizeEffect >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSCOLORIZEEFFECT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsOpacityEffect >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSOPACITYEFFECT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsDropShadowEffect >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSDROPSHADOWEFFECT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QUndoGroup >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QUNDOGROUP_IDX]); }
template<> inline PyTypeObject* SbkType< ::QUndoStack >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QUNDOSTACK_IDX]); }
template<> inline PyTypeObject* SbkType< ::QButtonGroup >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QBUTTONGROUP_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsObject >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSOBJECT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsTextItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSTEXTITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsProxyWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QGRAPHICSPROXYWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QDataWidgetMapper::SubmitPolicy >() { return SbkPySide2_QtWidgetsTypes[SBK_QDATAWIDGETMAPPER_SUBMITPOLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QDataWidgetMapper >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QDATAWIDGETMAPPER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractItemDelegate::EndEditHint >() { return SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTITEMDELEGATE_ENDEDITHINT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractItemDelegate >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QABSTRACTITEMDELEGATE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QItemDelegate >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QITEMDELEGATE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStyledItemDelegate >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QSTYLEDITEMDELEGATE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QFileSystemModel::Roles >() { return SbkPySide2_QtWidgetsTypes[SBK_QFILESYSTEMMODEL_ROLES_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFileSystemModel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QFILESYSTEMMODEL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QDirModel::Roles >() { return SbkPySide2_QtWidgetsTypes[SBK_QDIRMODEL_ROLES_IDX]; }
template<> inline PyTypeObject* SbkType< ::QDirModel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QDIRMODEL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTextEdit::LineWrapMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QTEXTEDIT_LINEWRAPMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTextEdit::AutoFormattingFlag >() { return SbkPySide2_QtWidgetsTypes[SBK_QTEXTEDIT_AUTOFORMATTINGFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QTextEdit::AutoFormattingFlag> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QTEXTEDIT_AUTOFORMATTINGFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QTextEdit >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTEXTEDIT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTextBrowser >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTEXTBROWSER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTextEdit::ExtraSelection >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QTEXTEDIT_EXTRASELECTION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QPlainTextEdit::LineWrapMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QPLAINTEXTEDIT_LINEWRAPMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QPlainTextEdit >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QPLAINTEXTEDIT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QFileDialog::ViewMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QFILEDIALOG_VIEWMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFileDialog::FileMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QFILEDIALOG_FILEMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFileDialog::AcceptMode >() { return SbkPySide2_QtWidgetsTypes[SBK_QFILEDIALOG_ACCEPTMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFileDialog::DialogLabel >() { return SbkPySide2_QtWidgetsTypes[SBK_QFILEDIALOG_DIALOGLABEL_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFileDialog::Option >() { return SbkPySide2_QtWidgetsTypes[SBK_QFILEDIALOG_OPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QFileDialog::Option> >() { return SbkPySide2_QtWidgetsTypes[SBK_QFLAGS_QFILEDIALOG_OPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QFileDialog >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWidgetsTypes[SBK_QFILEDIALOG_IDX]); }

} // namespace Shiboken

#endif // SBK_QTWIDGETS_PYTHON_H

