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


#ifndef SBK_QTCORE_PYTHON_H
#define SBK_QTCORE_PYTHON_H

#include <sbkpython.h>
#include <sbkconverter.h>
#include <sbkenum.h>
#include <basewrapper.h>
#include <bindingmanager.h>
#include <memory>

#include <pysidesignal.h>
// Binded library includes
#include <qjsonarray.h>
#include <qsize.h>
#include <qfactoryinterface.h>
#include <qlocale.h>
#include <qmimedata.h>
#include <qpropertyanimation.h>
#include <qthread.h>
#include <QList>
#include <qsemaphore.h>
#include <qvariantanimation.h>
#include <qcommandlineoption.h>
#include <qtextcodec.h>
#include <qelapsedtimer.h>
#include <qfile.h>
#include <qsystemsemaphore.h>
#include <QTextCodec>
#include <qwineventnotifier.h>
#include <qmimetype.h>
#include <qtimer.h>
#include <qmetaobject.h>
#include <qhistorystate.h>
#include <qbuffer.h>
#include <qfileinfo.h>
#include <qanimationgroup.h>
#include <qiodevice.h>
#include <qnamespace.h>
#include <qsignalmapper.h>
#include <qabstracttransition.h>
#include <qsignaltransition.h>
#include <qtimeline.h>
#include <qobject.h>
#include <qdiriterator.h>
#include <qitemselectionmodel.h>
#include <qresource.h>
#include <qpauseanimation.h>
#include <qdir.h>
#include <qsettings.h>
#include <qline.h>
#include <qcryptographichash.h>
#include <qbasictimer.h>
#include <qregexp.h>
#include <qwaitcondition.h>
#include <qfileselector.h>
#include <qthreadpool.h>
#include <qfilesystemwatcher.h>
#include <qxmlstream.h>
#include <qprocess.h>
#include <qmutex.h>
#include <qstandardpaths.h>
#include <qtextboundaryfinder.h>
#include <qtemporaryfile.h>
#include <qreadwritelock.h>
#include <qfiledevice.h>
#include <qpoint.h>
#include <qlogging.h>
#include <qsysinfo.h>
#include <qobjectdefs.h>
#include <qpluginloader.h>
#include <qstate.h>
#include <qjsondocument.h>
#include <qcoreevent.h>
#include <qcollator.h>
#include <qstatemachine.h>
#include <qtemporarydir.h>
#include <qabstractstate.h>
#include <qtextstream.h>
#include <qmargins.h>
#include <qbitarray.h>
#include <qstringlistmodel.h>
#include <qdatastream.h>
#include <qjsonvalue.h>
#include <qabstractanimation.h>
#include <qsequentialanimationgroup.h>
#include <qbytearray.h>
#include <qurl.h>
#include <qeventloop.h>
#include <qparallelanimationgroup.h>
#include <qabstractproxymodel.h>
#include <qcommandlineparser.h>
#include <qrunnable.h>
#include <qcoreapplication.h>
#include <qbytearraymatcher.h>
#include <qtimezone.h>
#include <qlibraryinfo.h>
#include <qabstractitemmodel.h>
#include <qsavefile.h>
#include <qsocketnotifier.h>
#include <qstorageinfo.h>
#include <qtranslator.h>
#include <qdatetime.h>
#include <qabstracteventdispatcher.h>
#include <qrect.h>
#include <qfinalstate.h>
#include <qsortfilterproxymodel.h>
#include <qmimedatabase.h>
#include <qeventtransition.h>
#include <qeasingcurve.h>
// Conversion Includes - Primitive Types
#include <wtypes.h>
#include <QString>
#include <qabstractitemmodel.h>
#include <signalmanager.h>
#include <QStringList>

// Conversion Includes - Container Types
#include <QVector>
#include <QQueue>
#include <QList>
#include <QMap>
#include <QPair>
#include <QLinkedList>
#include <pysideqflags.h>
#include <QSet>
#include <QStack>
#include <QMultiMap>

// Type indices
#define SBK_QT_IDX                                                   265
#define SBK_QT_GLOBALCOLOR_IDX                                       298
#define SBK_QT_KEYBOARDMODIFIER_IDX                                  308
#define SBK_QFLAGS_QT_KEYBOARDMODIFIER__IDX                          94
#define SBK_QT_MODIFIER_IDX                                          312
#define SBK_QT_MOUSEBUTTON_IDX                                       313
#define SBK_QFLAGS_QT_MOUSEBUTTON__IDX                               96
#define SBK_QT_ORIENTATION_IDX                                       318
#define SBK_QFLAGS_QT_ORIENTATION__IDX                               98
#define SBK_QT_FOCUSPOLICY_IDX                                       293
#define SBK_QT_TABFOCUSBEHAVIOR_IDX                                  329
#define SBK_QT_SORTORDER_IDX                                         328
#define SBK_QT_TILERULE_IDX                                          334
#define SBK_QT_ALIGNMENTFLAG_IDX                                     266
#define SBK_QFLAGS_QT_ALIGNMENTFLAG__IDX                             83
#define SBK_QT_TEXTFLAG_IDX                                          331
#define SBK_QT_TEXTELIDEMODE_IDX                                     330
#define SBK_QT_WHITESPACEMODE_IDX                                    343
#define SBK_QT_HITTESTACCURACY_IDX                                   299
#define SBK_QT_WINDOWTYPE_IDX                                        348
#define SBK_QFLAGS_QT_WINDOWTYPE__IDX                                104
#define SBK_QT_WINDOWSTATE_IDX                                       347
#define SBK_QFLAGS_QT_WINDOWSTATE__IDX                               103
#define SBK_QT_APPLICATIONSTATE_IDX                                  269
#define SBK_QFLAGS_QT_APPLICATIONSTATE__IDX                          84
#define SBK_QT_SCREENORIENTATION_IDX                                 322
#define SBK_QFLAGS_QT_SCREENORIENTATION__IDX                         99
#define SBK_QT_WIDGETATTRIBUTE_IDX                                   344
#define SBK_QT_APPLICATIONATTRIBUTE_IDX                              268
#define SBK_QT_IMAGECONVERSIONFLAG_IDX                               300
#define SBK_QFLAGS_QT_IMAGECONVERSIONFLAG__IDX                       90
#define SBK_QT_BGMODE_IDX                                            273
#define SBK_QT_KEY_IDX                                               307
#define SBK_QT_ARROWTYPE_IDX                                         270
#define SBK_QT_PENSTYLE_IDX                                          321
#define SBK_QT_PENCAPSTYLE_IDX                                       319
#define SBK_QT_PENJOINSTYLE_IDX                                      320
#define SBK_QT_BRUSHSTYLE_IDX                                        274
#define SBK_QT_SIZEMODE_IDX                                          327
#define SBK_QT_UIEFFECT_IDX                                          342
#define SBK_QT_CURSORSHAPE_IDX                                       282
#define SBK_QT_TEXTFORMAT_IDX                                        332
#define SBK_QT_ASPECTRATIOMODE_IDX                                   271
#define SBK_QT_DOCKWIDGETAREA_IDX                                    285
#define SBK_QFLAGS_QT_DOCKWIDGETAREA__IDX                            85
#define SBK_QT_DOCKWIDGETAREASIZES_IDX                               286
#define SBK_QT_TOOLBARAREA_IDX                                       337
#define SBK_QFLAGS_QT_TOOLBARAREA__IDX                               101
#define SBK_QT_TOOLBARAREASIZES_IDX                                  338
#define SBK_QT_DATEFORMAT_IDX                                        283
#define SBK_QT_TIMESPEC_IDX                                          335
#define SBK_QT_DAYOFWEEK_IDX                                         284
#define SBK_QT_SCROLLBARPOLICY_IDX                                   323
#define SBK_QT_CASESENSITIVITY_IDX                                   275
#define SBK_QT_CORNER_IDX                                            281
#define SBK_QT_EDGE_IDX                                              288
#define SBK_QFLAGS_QT_EDGE__IDX                                      87
#define SBK_QT_CONNECTIONTYPE_IDX                                    278
#define SBK_QT_SHORTCUTCONTEXT_IDX                                   325
#define SBK_QT_FILLRULE_IDX                                          291
#define SBK_QT_MASKMODE_IDX                                          310
#define SBK_QT_CLIPOPERATION_IDX                                     277
#define SBK_QT_ITEMSELECTIONMODE_IDX                                 305
#define SBK_QT_ITEMSELECTIONOPERATION_IDX                            306
#define SBK_QT_TRANSFORMATIONMODE_IDX                                341
#define SBK_QT_AXIS_IDX                                              272
#define SBK_QT_FOCUSREASON_IDX                                       294
#define SBK_QT_CONTEXTMENUPOLICY_IDX                                 279
#define SBK_QT_INPUTMETHODQUERY_IDX                                  302
#define SBK_QFLAGS_QT_INPUTMETHODQUERY__IDX                          92
#define SBK_QT_INPUTMETHODHINT_IDX                                   301
#define SBK_QFLAGS_QT_INPUTMETHODHINT__IDX                           91
#define SBK_QT_ENTERKEYTYPE_IDX                                      289
#define SBK_QT_TOOLBUTTONSTYLE_IDX                                   339
#define SBK_QT_LAYOUTDIRECTION_IDX                                   309
#define SBK_QT_ANCHORPOINT_IDX                                       267
#define SBK_QT_FINDCHILDOPTION_IDX                                   292
#define SBK_QFLAGS_QT_FINDCHILDOPTION__IDX                           88
#define SBK_QT_DROPACTION_IDX                                        287
#define SBK_QFLAGS_QT_DROPACTION__IDX                                86
#define SBK_QT_CHECKSTATE_IDX                                        276
#define SBK_QT_ITEMDATAROLE_IDX                                      303
#define SBK_QT_ITEMFLAG_IDX                                          304
#define SBK_QFLAGS_QT_ITEMFLAG__IDX                                  93
#define SBK_QT_MATCHFLAG_IDX                                         311
#define SBK_QFLAGS_QT_MATCHFLAG__IDX                                 95
#define SBK_QT_WINDOWMODALITY_IDX                                    346
#define SBK_QT_TEXTINTERACTIONFLAG_IDX                               333
#define SBK_QFLAGS_QT_TEXTINTERACTIONFLAG__IDX                       100
#define SBK_QT_EVENTPRIORITY_IDX                                     290
#define SBK_QT_SIZEHINT_IDX                                          326
#define SBK_QT_WINDOWFRAMESECTION_IDX                                345
#define SBK_QT_COORDINATESYSTEM_IDX                                  280
#define SBK_QT_TOUCHPOINTSTATE_IDX                                   340
#define SBK_QFLAGS_QT_TOUCHPOINTSTATE__IDX                           102
#define SBK_QT_GESTURESTATE_IDX                                      296
#define SBK_QT_GESTURETYPE_IDX                                       297
#define SBK_QT_GESTUREFLAG_IDX                                       295
#define SBK_QFLAGS_QT_GESTUREFLAG__IDX                               89
#define SBK_QT_NATIVEGESTURETYPE_IDX                                 316
#define SBK_QT_NAVIGATIONMODE_IDX                                    317
#define SBK_QT_CURSORMOVESTYLE_IDX                                   354
#define SBK_QT_TIMERTYPE_IDX                                         336
#define SBK_QT_SCROLLPHASE_IDX                                       324
#define SBK_QT_MOUSEEVENTSOURCE_IDX                                  315
#define SBK_QT_MOUSEEVENTFLAG_IDX                                    314
#define SBK_QFLAGS_QT_MOUSEEVENTFLAG__IDX                            97
#define SBK_QXMLSTREAMWRITER_IDX                                     264
#define SBK_QXMLSTREAMREADER_IDX                                     260
#define SBK_QXMLSTREAMREADER_TOKENTYPE_IDX                           263
#define SBK_QXMLSTREAMREADER_READELEMENTTEXTBEHAVIOUR_IDX            262
#define SBK_QXMLSTREAMREADER_ERROR_IDX                               261
#define SBK_QXMLSTREAMENTITYRESOLVER_IDX                             257
#define SBK_QXMLSTREAMENTITYDECLARATION_IDX                          256
#define SBK_QXMLSTREAMNOTATIONDECLARATION_IDX                        259
#define SBK_QXMLSTREAMNAMESPACEDECLARATION_IDX                       258
#define SBK_QXMLSTREAMATTRIBUTES_IDX                                 255
#define SBK_QVECTOR_QXMLSTREAMATTRIBUTE_IDX                          255
#define SBK_QXMLSTREAMATTRIBUTE_IDX                                  254
#define SBK_QTEXTBOUNDARYFINDER_IDX                                  216
#define SBK_QTEXTBOUNDARYFINDER_BOUNDARYTYPE_IDX                     218
#define SBK_QTEXTBOUNDARYFINDER_BOUNDARYREASON_IDX                   217
#define SBK_QFLAGS_QTEXTBOUNDARYFINDER_BOUNDARYREASON__IDX           77
#define SBK_QRECTF_IDX                                               174
#define SBK_QRECT_IDX                                                173
#define SBK_QSIZEF_IDX                                               190
#define SBK_QSIZE_IDX                                                189
#define SBK_QMARGINSF_IDX                                            135
#define SBK_QMARGINS_IDX                                             134
#define SBK_QLINEF_IDX                                               126
#define SBK_QLINEF_INTERSECTTYPE_IDX                                 127
#define SBK_QLINE_IDX                                                125
#define SBK_QPOINTF_IDX                                              160
#define SBK_QPOINT_IDX                                               159
#define SBK_QELAPSEDTIMER_IDX                                        48
#define SBK_QELAPSEDTIMER_CLOCKTYPE_IDX                              49
#define SBK_QCRYPTOGRAPHICHASH_IDX                                   30
#define SBK_QCRYPTOGRAPHICHASH_ALGORITHM_IDX                         31
#define SBK_QCOMMANDLINEPARSER_IDX                                   26
#define SBK_QCOMMANDLINEPARSER_SINGLEDASHWORDOPTIONMODE_IDX          28
#define SBK_QCOMMANDLINEPARSER_OPTIONSAFTERPOSITIONALARGUMENTSMODE_IDX 27
#define SBK_QCOMMANDLINEOPTION_IDX                                   25
#define SBK_QCOLLATORSORTKEY_IDX                                     24
#define SBK_QBYTEARRAYMATCHER_IDX                                    21
#define SBK_QBITARRAY_IDX                                            17
#define SBK_QWAITCONDITION_IDX                                       251
#define SBK_QSEMAPHORE_IDX                                           181
#define SBK_QWRITELOCKER_IDX                                         253
#define SBK_QREADLOCKER_IDX                                          170
#define SBK_QREADWRITELOCK_IDX                                       171
#define SBK_QREADWRITELOCK_RECURSIONMODE_IDX                         172
#define SBK_QRUNNABLE_IDX                                            179
#define SBK_QFACTORYINTERFACE_IDX                                    55
#define SBK_QMIMEDATABASE_IDX                                        147
#define SBK_QMIMEDATABASE_MATCHMODE_IDX                              148
#define SBK_QMIMETYPE_IDX                                            149
#define SBK_QSYSTEMSEMAPHORE_IDX                                     211
#define SBK_QSYSTEMSEMAPHORE_ACCESSMODE_IDX                          212
#define SBK_QSYSTEMSEMAPHORE_SYSTEMSEMAPHOREERROR_IDX                213
#define SBK_QMETACLASSINFO_IDX                                       137
#define SBK_QMETAPROPERTY_IDX                                        145
#define SBK_QMETAENUM_IDX                                            138
#define SBK_QEVENT_IDX                                               50
#define SBK_QEVENT_TYPE_IDX                                          51
#define SBK_QCHILDEVENT_IDX                                          22
#define SBK_QTIMEREVENT_IDX                                          243
#define SBK_QDYNAMICPROPERTYCHANGEEVENT_IDX                          45
#define SBK_QBASICTIMER_IDX                                          16
#define SBK_QJSONDOCUMENT_IDX                                        116
#define SBK_QJSONDOCUMENT_DATAVALIDATION_IDX                         117
#define SBK_QJSONDOCUMENT_JSONFORMAT_IDX                             118
#define SBK_QJSONPARSEERROR_IDX                                      119
#define SBK_QJSONPARSEERROR_PARSEERROR_IDX                           120
#define SBK_QJSONARRAY_IDX                                           115
#define SBK_QJSONVALUE_IDX                                           121
#define SBK_QJSONVALUE_TYPE_IDX                                      122
#define SBK_QITEMSELECTION_IDX                                       111
#define SBK_QLIST_QITEMSELECTIONRANGE_IDX                            111
#define SBK_QITEMSELECTIONRANGE_IDX                                  114
#define SBK_QPERSISTENTMODELINDEX_IDX                                157
#define SBK_QMODELINDEX_IDX                                          150
#define SBK_QTEMPORARYDIR_IDX                                        214
#define SBK_QSTORAGEINFO_IDX                                         205
#define SBK_QSTANDARDPATHS_IDX                                       194
#define SBK_QSTANDARDPATHS_STANDARDLOCATION_IDX                      196
#define SBK_QSTANDARDPATHS_LOCATEOPTION_IDX                          195
#define SBK_QFLAGS_QSTANDARDPATHS_LOCATEOPTION__IDX                  76
#define SBK_QPROCESSENVIRONMENT_IDX                                  168
#define SBK_QDIR_IDX                                                 40
#define SBK_QDIR_FILTER_IDX                                          41
#define SBK_QFLAGS_QDIR_FILTER__IDX                                  67
#define SBK_QDIR_SORTFLAG_IDX                                        42
#define SBK_QFLAGS_QDIR_SORTFLAG__IDX                                68
#define SBK_QDIRITERATOR_IDX                                         43
#define SBK_QDIRITERATOR_ITERATORFLAG_IDX                            44
#define SBK_QFLAGS_QDIRITERATOR_ITERATORFLAG__IDX                    69
#define SBK_QFILEINFO_IDX                                            62
#define SBK_QTEXTSTREAMMANIPULATOR_IDX                               229
#define SBK_QLOCALE_IDX                                              128
#define SBK_QLOCALE_LANGUAGE_IDX                                     131
#define SBK_QLOCALE_SCRIPT_IDX                                       353
#define SBK_QLOCALE_COUNTRY_IDX                                      129
#define SBK_QLOCALE_MEASUREMENTSYSTEM_IDX                            132
#define SBK_QLOCALE_FORMATTYPE_IDX                                   130
#define SBK_QLOCALE_NUMBEROPTION_IDX                                 133
#define SBK_QFLAGS_QLOCALE_NUMBEROPTION__IDX                         75
#define SBK_QLOCALE_CURRENCYSYMBOLFORMAT_IDX                         351
#define SBK_QLOCALE_QUOTATIONSTYLE_IDX                               352
#define SBK_QRESOURCE_IDX                                            178
#define SBK_QTIMEZONE_IDX                                            238
#define SBK_QTIMEZONE_TIMETYPE_IDX                                   241
#define SBK_QTIMEZONE_NAMETYPE_IDX                                   239
#define SBK_QTIMEZONE_OFFSETDATA_IDX                                 240
#define SBK_QCOLLATOR_IDX                                            23
#define SBK_QDATASTREAM_IDX                                          32
#define SBK_QDATASTREAM_VERSION_IDX                                  36
#define SBK_QDATASTREAM_BYTEORDER_IDX                                33
#define SBK_QDATASTREAM_STATUS_IDX                                   35
#define SBK_QDATASTREAM_FLOATINGPOINTPRECISION_IDX                   34
#define SBK_QLIBRARYINFO_IDX                                         123
#define SBK_QLIBRARYINFO_LIBRARYLOCATION_IDX                         124
#define SBK_QDATETIME_IDX                                            39
#define SBK_QTIME_IDX                                                233
#define SBK_QDATE_IDX                                                37
#define SBK_QDATE_MONTHNAMETYPE_IDX                                  38
#define SBK_QTEXTDECODER_IDX                                         222
#define SBK_QTEXTENCODER_IDX                                         223
#define SBK_QTEXTCODEC_IDX                                           219
#define SBK_QTEXTCODEC_CONVERSIONFLAG_IDX                            220
#define SBK_QFLAGS_QTEXTCODEC_CONVERSIONFLAG__IDX                    78
#define SBK_QTEXTCODEC_CONVERTERSTATE_IDX                            221
#define SBK_QEASINGCURVE_IDX                                         46
#define SBK_QEASINGCURVE_TYPE_IDX                                    47
#define SBK_QOBJECT_IDX                                              154
#define SBK_QFILESELECTOR_IDX                                        63
#define SBK_QTHREADPOOL_IDX                                          232
#define SBK_QTHREAD_IDX                                              230
#define SBK_QTHREAD_PRIORITY_IDX                                     231
#define SBK_QABSTRACTANIMATION_IDX                                   0
#define SBK_QABSTRACTANIMATION_DIRECTION_IDX                         2
#define SBK_QABSTRACTANIMATION_STATE_IDX                             3
#define SBK_QABSTRACTANIMATION_DELETIONPOLICY_IDX                    1
#define SBK_QVARIANTANIMATION_IDX                                    250
#define SBK_QPROPERTYANIMATION_IDX                                   169
#define SBK_QPAUSEANIMATION_IDX                                      156
#define SBK_QANIMATIONGROUP_IDX                                      14
#define SBK_QSEQUENTIALANIMATIONGROUP_IDX                            182
#define SBK_QPARALLELANIMATIONGROUP_IDX                              155
#define SBK_QWINEVENTNOTIFIER_IDX                                    252
#define SBK_QTRANSLATOR_IDX                                          244
#define SBK_QSETTINGS_IDX                                            183
#define SBK_QSETTINGS_STATUS_IDX                                     186
#define SBK_QSETTINGS_FORMAT_IDX                                     184
#define SBK_QSETTINGS_SCOPE_IDX                                      185
#define SBK_QTIMER_IDX                                               242
#define SBK_QSOCKETNOTIFIER_IDX                                      191
#define SBK_QSOCKETNOTIFIER_TYPE_IDX                                 192
#define SBK_QSIGNALMAPPER_IDX                                        187
#define SBK_QFILESYSTEMWATCHER_IDX                                   64
#define SBK_QABSTRACTTRANSITION_IDX                                  12
#define SBK_QABSTRACTTRANSITION_TRANSITIONTYPE_IDX                   13
#define SBK_QSIGNALTRANSITION_IDX                                    188
#define SBK_QEVENTTRANSITION_IDX                                     54
#define SBK_QTIMELINE_IDX                                            234
#define SBK_QTIMELINE_STATE_IDX                                      237
#define SBK_QTIMELINE_DIRECTION_IDX                                  236
#define SBK_QTIMELINE_CURVESHAPE_IDX                                 235
#define SBK_QABSTRACTSTATE_IDX                                       10
#define SBK_QSTATE_IDX                                               197
#define SBK_QSTATE_CHILDMODE_IDX                                     198
#define SBK_QSTATE_RESTOREPOLICY_IDX                                 199
#define SBK_QSTATEMACHINE_IDX                                        200
#define SBK_QSTATEMACHINE_EVENTPRIORITY_IDX                          202
#define SBK_QSTATEMACHINE_ERROR_IDX                                  201
#define SBK_QSTATEMACHINE_WRAPPEDEVENT_IDX                           204
#define SBK_QSTATEMACHINE_SIGNALEVENT_IDX                            203
#define SBK_QHISTORYSTATE_IDX                                        107
#define SBK_QHISTORYSTATE_HISTORYTYPE_IDX                            108
#define SBK_QFINALSTATE_IDX                                          65
#define SBK_QPLUGINLOADER_IDX                                        158
#define SBK_QABSTRACTITEMMODEL_IDX                                   6
#define SBK_QABSTRACTITEMMODEL_LAYOUTCHANGEHINT_IDX                  7
#define SBK_QABSTRACTPROXYMODEL_IDX                                  9
#define SBK_QSORTFILTERPROXYMODEL_IDX                                193
#define SBK_QABSTRACTLISTMODEL_IDX                                   8
#define SBK_QSTRINGLISTMODEL_IDX                                     206
#define SBK_QABSTRACTTABLEMODEL_IDX                                  11
#define SBK_QABSTRACTEVENTDISPATCHER_IDX                             4
#define SBK_QABSTRACTEVENTDISPATCHER_TIMERINFO_IDX                   5
#define SBK_QIODEVICE_IDX                                            109
#define SBK_QIODEVICE_OPENMODEFLAG_IDX                               110
#define SBK_QFLAGS_QIODEVICE_OPENMODEFLAG__IDX                       73
#define SBK_QBUFFER_IDX                                              18
#define SBK_QPROCESS_IDX                                             161
#define SBK_QPROCESS_PROCESSERROR_IDX                                166
#define SBK_QPROCESS_PROCESSSTATE_IDX                                167
#define SBK_QPROCESS_PROCESSCHANNEL_IDX                              164
#define SBK_QPROCESS_PROCESSCHANNELMODE_IDX                          165
#define SBK_QPROCESS_INPUTCHANNELMODE_IDX                            163
#define SBK_QPROCESS_EXITSTATUS_IDX                                  162
#define SBK_QFILEDEVICE_IDX                                          57
#define SBK_QFILEDEVICE_FILEERROR_IDX                                58
#define SBK_QFILEDEVICE_PERMISSION_IDX                               61
#define SBK_QFLAGS_QFILEDEVICE_PERMISSION__IDX                       72
#define SBK_QFILEDEVICE_FILEHANDLEFLAG_IDX                           59
#define SBK_QFLAGS_QFILEDEVICE_FILEHANDLEFLAG__IDX                   71
#define SBK_QFILEDEVICE_MEMORYMAPFLAGS_IDX                           60
#define SBK_QSAVEFILE_IDX                                            180
#define SBK_QFILE_IDX                                                56
#define SBK_QTEMPORARYFILE_IDX                                       215
#define SBK_QTEXTSTREAM_IDX                                          224
#define SBK_QTEXTSTREAM_REALNUMBERNOTATION_IDX                       227
#define SBK_QTEXTSTREAM_FIELDALIGNMENT_IDX                           225
#define SBK_QTEXTSTREAM_STATUS_IDX                                   228
#define SBK_QTEXTSTREAM_NUMBERFLAG_IDX                               226
#define SBK_QFLAGS_QTEXTSTREAM_NUMBERFLAG__IDX                       79
#define SBK_QEVENTLOOP_IDX                                           52
#define SBK_QEVENTLOOP_PROCESSEVENTSFLAG_IDX                         53
#define SBK_QFLAGS_QEVENTLOOP_PROCESSEVENTSFLAG__IDX                 70
#define SBK_QMIMEDATA_IDX                                            146
#define SBK_QITEMSELECTIONMODEL_IDX                                  112
#define SBK_QITEMSELECTIONMODEL_SELECTIONFLAG_IDX                    113
#define SBK_QFLAGS_QITEMSELECTIONMODEL_SELECTIONFLAG__IDX            74
#define SBK_QCOREAPPLICATION_IDX                                     29
#define SBK_QCOREAPPLICATION_APPLICATIONFLAGS_IDX                    350
#define SBK_QREGEXP_IDX                                              175
#define SBK_QREGEXP_PATTERNSYNTAX_IDX                                177
#define SBK_QREGEXP_CARETMODE_IDX                                    176
#define SBK_QBYTEARRAY_IDX                                           19
#define SBK_QBYTEARRAY_BASE64OPTION_IDX                              20
#define SBK_QFLAGS_QBYTEARRAY_BASE64OPTION__IDX                      66
#define SBK_QURL_IDX                                                 245
#define SBK_QURL_PARSINGMODE_IDX                                     247
#define SBK_QURL_URLFORMATTINGOPTION_IDX                             248
#define SBK_QURL_COMPONENTFORMATTINGOPTION_IDX                       246
#define SBK_QFLAGS_QURL_COMPONENTFORMATTINGOPTION__IDX               80
#define SBK_QURL_USERINPUTRESOLUTIONOPTION_IDX                       249
#define SBK_QFLAGS_QURL_USERINPUTRESOLUTIONOPTION__IDX               82
#define SBK_QMETAOBJECT_CONNECTION_IDX                               144
#define SBK_QGENERICARGUMENT_IDX                                     105
#define SBK_QMETAOBJECT_IDX                                          142
#define SBK_QMETAOBJECT_CALL_IDX                                     143
#define SBK_QGENERICRETURNARGUMENT_IDX                               106
#define SBK_QMETAMETHOD_IDX                                          139
#define SBK_QMETAMETHOD_ACCESS_IDX                                   140
#define SBK_QMETAMETHOD_METHODTYPE_IDX                               141
#define SBK_QMUTEXLOCKER_IDX                                         153
#define SBK_QBASICMUTEX_IDX                                          15
#define SBK_QMUTEX_IDX                                               151
#define SBK_QMUTEX_RECURSIONMODE_IDX                                 152
#define SBK_QMESSAGELOGCONTEXT_IDX                                   136
#define SBK_QSYSINFO_IDX                                             207
#define SBK_QSYSINFO_SIZES_IDX                                       209
#define SBK_QSYSINFO_ENDIAN_IDX                                      208
#define SBK_QSYSINFO_WINVERSION_IDX                                  210
#define SBK_QTMSGTYPE_IDX                                            349
#define SBK_QtCore_IDX_COUNT                                         355

// This variable stores all Python types exported by this module.
extern PyTypeObject** SbkPySide2_QtCoreTypes;

// This variable stores all type converters exported by this module.
extern SbkConverter** SbkPySide2_QtCoreTypeConverters;

// Converter indices
#define SBK_HWND_IDX                                                 0
#define SBK_QSTRINGREF_IDX                                           1
#define SBK_QINTPTR_IDX                                              2
#define SBK_QSTRING_IDX                                              3
#define SBK_QCHAR_IDX                                                4
#define SBK_QMODELINDEXLIST_IDX                                      5
#define SBK_BOOL_IDX                                                 6
#define SBK_QVARIANT_TYPE_IDX                                        7
#define SBK_QJSONOBJECT_IDX                                          8
#define SBK_QUINTPTR_IDX                                             9
#define SBK_QVARIANT_IDX                                             10
#define SBK_QSTRINGLIST_IDX                                          11
#define SBK_QPTRDIFF_IDX                                             12
#define SBK_QTCORE_QVECTOR_QXMLSTREAMNAMESPACEDECLARATION_IDX        13 // const QVector<QXmlStreamNamespaceDeclaration > &
#define SBK_QTCORE_QVECTOR_QXMLSTREAMENTITYDECLARATION_IDX           14 // QVector<QXmlStreamEntityDeclaration >
#define SBK_QTCORE_QVECTOR_QXMLSTREAMNOTATIONDECLARATION_IDX         15 // QVector<QXmlStreamNotationDeclaration >
#define SBK_QTCORE_QVECTOR_QXMLSTREAMATTRIBUTE_IDX                   16 // QVector<QXmlStreamAttribute > &
#define SBK_QTCORE_QLIST_QXMLSTREAMATTRIBUTE_IDX                     17 // const QList<QXmlStreamAttribute > &
#define SBK_QTCORE_QLIST_QCOMMANDLINEOPTION_IDX                      18 // const QList<QCommandLineOption > &
#define SBK_QTCORE_QLIST_QMIMETYPE_IDX                               19 // QList<QMimeType >
#define SBK_QTCORE_QLIST_QVARIANT_IDX                                20 // const QList<QVariant > &
#define SBK_QTCORE_QLIST_QITEMSELECTIONRANGE_IDX                     21 // const QList<QItemSelectionRange > &
#define SBK_QTCORE_QSET_QITEMSELECTIONRANGE_IDX                      22 // const QSet<QItemSelectionRange > &
#define SBK_QTCORE_QVECTOR_QITEMSELECTIONRANGE_IDX                   23 // const QVector<QItemSelectionRange > &
#define SBK_QTCORE_QLIST_QSTORAGEINFO_IDX                            24 // QList<QStorageInfo >
#define SBK_QTCORE_QLIST_QFILEINFO_IDX                               25 // QList<QFileInfo >
#define SBK_QTCORE_QLIST_QLOCALE_COUNTRY_IDX                         26 // QList<QLocale::Country >
#define SBK_QTCORE_QLIST_QLOCALE_IDX                                 27 // QList<QLocale >
#define SBK_QTCORE_QLIST_QT_DAYOFWEEK_IDX                            28 // QList<Qt::DayOfWeek >
#define SBK_QTCORE_QLIST_QBYTEARRAY_IDX                              29 // QList<QByteArray >
#define SBK_QTCORE_QVECTOR_QTIMEZONE_OFFSETDATA_IDX                  30 // QVector<QTimeZone::OffsetData >
#define SBK_QTCORE_QLIST_INT_IDX                                     31 // QList<int >
#define SBK_QTCORE_QVECTOR_QPOINTF_IDX                               32 // QVector<QPointF >
#define SBK_QTCORE_QLIST_QOBJECTPTR_IDX                              33 // const QList<QObject * > &
#define SBK_QTCORE_QPAIR_QREAL_QVARIANT_IDX                          34 // QPair<qreal, QVariant >
#define SBK_QTCORE_QVECTOR_QPAIR_QREAL_QVARIANT_IDX                  35 // QVector<QPair<qreal, QVariant > >
#define SBK_QTCORE_QLIST_QABSTRACTANIMATIONPTR_IDX                   36 // QList<QAbstractAnimation * >
#define SBK_QTCORE_QLIST_QABSTRACTSTATEPTR_IDX                       37 // const QList<QAbstractState * > &
#define SBK_QTCORE_QLIST_QABSTRACTTRANSITIONPTR_IDX                  38 // QList<QAbstractTransition * >
#define SBK_QTCORE_QSET_QABSTRACTSTATEPTR_IDX                        39 // QSet<QAbstractState * >
#define SBK_QTCORE_QVECTOR_INT_IDX                                   40 // const QVector<int > &
#define SBK_QTCORE_QHASH_INT_QBYTEARRAY_IDX                          41 // const QHash<int, QByteArray > &
#define SBK_QTCORE_QMAP_INT_QVARIANT_IDX                             42 // QMap<int, QVariant >
#define SBK_QTCORE_QLIST_QPERSISTENTMODELINDEX_IDX                   43 // const QList<QPersistentModelIndex > &
#define SBK_QTCORE_QLIST_QABSTRACTEVENTDISPATCHER_TIMERINFO_IDX      44 // QList<QAbstractEventDispatcher::TimerInfo >
#define SBK_QTCORE_QLIST_QURL_IDX                                    45 // const QList<QUrl > &
#define SBK_QTCORE_QLIST_QSTRING_IDX                                 46 // QList<QString >
#define SBK_QTCORE_QMAP_QSTRING_QVARIANT_IDX                         47 // QMap<QString, QVariant >
#define SBK_QtCore_CONVERTERS_IDX_COUNT                              48

// Macros for type check

namespace Shiboken
{

// PyType functions, to get the PyObjectType for a type T
template<> inline PyTypeObject* SbkType< ::QtMsgType >() { return SbkPySide2_QtCoreTypes[SBK_QTMSGTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::GlobalColor >() { return SbkPySide2_QtCoreTypes[SBK_QT_GLOBALCOLOR_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::KeyboardModifier >() { return SbkPySide2_QtCoreTypes[SBK_QT_KEYBOARDMODIFIER_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::KeyboardModifier> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_KEYBOARDMODIFIER__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::Modifier >() { return SbkPySide2_QtCoreTypes[SBK_QT_MODIFIER_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::MouseButton >() { return SbkPySide2_QtCoreTypes[SBK_QT_MOUSEBUTTON_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::MouseButton> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_MOUSEBUTTON__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::Orientation >() { return SbkPySide2_QtCoreTypes[SBK_QT_ORIENTATION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::Orientation> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_ORIENTATION__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::FocusPolicy >() { return SbkPySide2_QtCoreTypes[SBK_QT_FOCUSPOLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::TabFocusBehavior >() { return SbkPySide2_QtCoreTypes[SBK_QT_TABFOCUSBEHAVIOR_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::SortOrder >() { return SbkPySide2_QtCoreTypes[SBK_QT_SORTORDER_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::TileRule >() { return SbkPySide2_QtCoreTypes[SBK_QT_TILERULE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::AlignmentFlag >() { return SbkPySide2_QtCoreTypes[SBK_QT_ALIGNMENTFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::AlignmentFlag> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_ALIGNMENTFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::TextFlag >() { return SbkPySide2_QtCoreTypes[SBK_QT_TEXTFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::TextElideMode >() { return SbkPySide2_QtCoreTypes[SBK_QT_TEXTELIDEMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::WhiteSpaceMode >() { return SbkPySide2_QtCoreTypes[SBK_QT_WHITESPACEMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::HitTestAccuracy >() { return SbkPySide2_QtCoreTypes[SBK_QT_HITTESTACCURACY_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::WindowType >() { return SbkPySide2_QtCoreTypes[SBK_QT_WINDOWTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::WindowType> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_WINDOWTYPE__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::WindowState >() { return SbkPySide2_QtCoreTypes[SBK_QT_WINDOWSTATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::WindowState> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_WINDOWSTATE__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ApplicationState >() { return SbkPySide2_QtCoreTypes[SBK_QT_APPLICATIONSTATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::ApplicationState> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_APPLICATIONSTATE__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ScreenOrientation >() { return SbkPySide2_QtCoreTypes[SBK_QT_SCREENORIENTATION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::ScreenOrientation> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_SCREENORIENTATION__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::WidgetAttribute >() { return SbkPySide2_QtCoreTypes[SBK_QT_WIDGETATTRIBUTE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ApplicationAttribute >() { return SbkPySide2_QtCoreTypes[SBK_QT_APPLICATIONATTRIBUTE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ImageConversionFlag >() { return SbkPySide2_QtCoreTypes[SBK_QT_IMAGECONVERSIONFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::ImageConversionFlag> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_IMAGECONVERSIONFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::BGMode >() { return SbkPySide2_QtCoreTypes[SBK_QT_BGMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::Key >() { return SbkPySide2_QtCoreTypes[SBK_QT_KEY_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ArrowType >() { return SbkPySide2_QtCoreTypes[SBK_QT_ARROWTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::PenStyle >() { return SbkPySide2_QtCoreTypes[SBK_QT_PENSTYLE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::PenCapStyle >() { return SbkPySide2_QtCoreTypes[SBK_QT_PENCAPSTYLE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::PenJoinStyle >() { return SbkPySide2_QtCoreTypes[SBK_QT_PENJOINSTYLE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::BrushStyle >() { return SbkPySide2_QtCoreTypes[SBK_QT_BRUSHSTYLE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::SizeMode >() { return SbkPySide2_QtCoreTypes[SBK_QT_SIZEMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::UIEffect >() { return SbkPySide2_QtCoreTypes[SBK_QT_UIEFFECT_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::CursorShape >() { return SbkPySide2_QtCoreTypes[SBK_QT_CURSORSHAPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::TextFormat >() { return SbkPySide2_QtCoreTypes[SBK_QT_TEXTFORMAT_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::AspectRatioMode >() { return SbkPySide2_QtCoreTypes[SBK_QT_ASPECTRATIOMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::DockWidgetArea >() { return SbkPySide2_QtCoreTypes[SBK_QT_DOCKWIDGETAREA_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::DockWidgetArea> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_DOCKWIDGETAREA__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::DockWidgetAreaSizes >() { return SbkPySide2_QtCoreTypes[SBK_QT_DOCKWIDGETAREASIZES_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ToolBarArea >() { return SbkPySide2_QtCoreTypes[SBK_QT_TOOLBARAREA_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::ToolBarArea> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_TOOLBARAREA__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ToolBarAreaSizes >() { return SbkPySide2_QtCoreTypes[SBK_QT_TOOLBARAREASIZES_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::DateFormat >() { return SbkPySide2_QtCoreTypes[SBK_QT_DATEFORMAT_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::TimeSpec >() { return SbkPySide2_QtCoreTypes[SBK_QT_TIMESPEC_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::DayOfWeek >() { return SbkPySide2_QtCoreTypes[SBK_QT_DAYOFWEEK_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ScrollBarPolicy >() { return SbkPySide2_QtCoreTypes[SBK_QT_SCROLLBARPOLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::CaseSensitivity >() { return SbkPySide2_QtCoreTypes[SBK_QT_CASESENSITIVITY_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::Corner >() { return SbkPySide2_QtCoreTypes[SBK_QT_CORNER_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::Edge >() { return SbkPySide2_QtCoreTypes[SBK_QT_EDGE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::Edge> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_EDGE__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ConnectionType >() { return SbkPySide2_QtCoreTypes[SBK_QT_CONNECTIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ShortcutContext >() { return SbkPySide2_QtCoreTypes[SBK_QT_SHORTCUTCONTEXT_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::FillRule >() { return SbkPySide2_QtCoreTypes[SBK_QT_FILLRULE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::MaskMode >() { return SbkPySide2_QtCoreTypes[SBK_QT_MASKMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ClipOperation >() { return SbkPySide2_QtCoreTypes[SBK_QT_CLIPOPERATION_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ItemSelectionMode >() { return SbkPySide2_QtCoreTypes[SBK_QT_ITEMSELECTIONMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ItemSelectionOperation >() { return SbkPySide2_QtCoreTypes[SBK_QT_ITEMSELECTIONOPERATION_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::TransformationMode >() { return SbkPySide2_QtCoreTypes[SBK_QT_TRANSFORMATIONMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::Axis >() { return SbkPySide2_QtCoreTypes[SBK_QT_AXIS_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::FocusReason >() { return SbkPySide2_QtCoreTypes[SBK_QT_FOCUSREASON_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ContextMenuPolicy >() { return SbkPySide2_QtCoreTypes[SBK_QT_CONTEXTMENUPOLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::InputMethodQuery >() { return SbkPySide2_QtCoreTypes[SBK_QT_INPUTMETHODQUERY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::InputMethodQuery> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_INPUTMETHODQUERY__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::InputMethodHint >() { return SbkPySide2_QtCoreTypes[SBK_QT_INPUTMETHODHINT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::InputMethodHint> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_INPUTMETHODHINT__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::EnterKeyType >() { return SbkPySide2_QtCoreTypes[SBK_QT_ENTERKEYTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ToolButtonStyle >() { return SbkPySide2_QtCoreTypes[SBK_QT_TOOLBUTTONSTYLE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::LayoutDirection >() { return SbkPySide2_QtCoreTypes[SBK_QT_LAYOUTDIRECTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::AnchorPoint >() { return SbkPySide2_QtCoreTypes[SBK_QT_ANCHORPOINT_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::FindChildOption >() { return SbkPySide2_QtCoreTypes[SBK_QT_FINDCHILDOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::FindChildOption> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_FINDCHILDOPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::DropAction >() { return SbkPySide2_QtCoreTypes[SBK_QT_DROPACTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::DropAction> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_DROPACTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::CheckState >() { return SbkPySide2_QtCoreTypes[SBK_QT_CHECKSTATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ItemDataRole >() { return SbkPySide2_QtCoreTypes[SBK_QT_ITEMDATAROLE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ItemFlag >() { return SbkPySide2_QtCoreTypes[SBK_QT_ITEMFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::ItemFlag> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_ITEMFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::MatchFlag >() { return SbkPySide2_QtCoreTypes[SBK_QT_MATCHFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::MatchFlag> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_MATCHFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::WindowModality >() { return SbkPySide2_QtCoreTypes[SBK_QT_WINDOWMODALITY_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::TextInteractionFlag >() { return SbkPySide2_QtCoreTypes[SBK_QT_TEXTINTERACTIONFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::TextInteractionFlag> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_TEXTINTERACTIONFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::EventPriority >() { return SbkPySide2_QtCoreTypes[SBK_QT_EVENTPRIORITY_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::SizeHint >() { return SbkPySide2_QtCoreTypes[SBK_QT_SIZEHINT_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::WindowFrameSection >() { return SbkPySide2_QtCoreTypes[SBK_QT_WINDOWFRAMESECTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::CoordinateSystem >() { return SbkPySide2_QtCoreTypes[SBK_QT_COORDINATESYSTEM_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::TouchPointState >() { return SbkPySide2_QtCoreTypes[SBK_QT_TOUCHPOINTSTATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::TouchPointState> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_TOUCHPOINTSTATE__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::GestureState >() { return SbkPySide2_QtCoreTypes[SBK_QT_GESTURESTATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::GestureType >() { return SbkPySide2_QtCoreTypes[SBK_QT_GESTURETYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::GestureFlag >() { return SbkPySide2_QtCoreTypes[SBK_QT_GESTUREFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::GestureFlag> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_GESTUREFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::NativeGestureType >() { return SbkPySide2_QtCoreTypes[SBK_QT_NATIVEGESTURETYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::NavigationMode >() { return SbkPySide2_QtCoreTypes[SBK_QT_NAVIGATIONMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::CursorMoveStyle >() { return SbkPySide2_QtCoreTypes[SBK_QT_CURSORMOVESTYLE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::TimerType >() { return SbkPySide2_QtCoreTypes[SBK_QT_TIMERTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::ScrollPhase >() { return SbkPySide2_QtCoreTypes[SBK_QT_SCROLLPHASE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::MouseEventSource >() { return SbkPySide2_QtCoreTypes[SBK_QT_MOUSEEVENTSOURCE_IDX]; }
template<> inline PyTypeObject* SbkType< ::Qt::MouseEventFlag >() { return SbkPySide2_QtCoreTypes[SBK_QT_MOUSEEVENTFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<Qt::MouseEventFlag> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QT_MOUSEEVENTFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QXmlStreamWriter >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QXMLSTREAMWRITER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QXmlStreamReader::TokenType >() { return SbkPySide2_QtCoreTypes[SBK_QXMLSTREAMREADER_TOKENTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QXmlStreamReader::ReadElementTextBehaviour >() { return SbkPySide2_QtCoreTypes[SBK_QXMLSTREAMREADER_READELEMENTTEXTBEHAVIOUR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QXmlStreamReader::Error >() { return SbkPySide2_QtCoreTypes[SBK_QXMLSTREAMREADER_ERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QXmlStreamReader >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QXMLSTREAMREADER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QXmlStreamEntityResolver >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QXMLSTREAMENTITYRESOLVER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QXmlStreamEntityDeclaration >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QXMLSTREAMENTITYDECLARATION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QXmlStreamNotationDeclaration >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QXMLSTREAMNOTATIONDECLARATION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QXmlStreamNamespaceDeclaration >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QXMLSTREAMNAMESPACEDECLARATION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QXmlStreamAttributes >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QXMLSTREAMATTRIBUTES_IDX]); }
template<> inline PyTypeObject* SbkType< ::QXmlStreamAttribute >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QXMLSTREAMATTRIBUTE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTextBoundaryFinder::BoundaryType >() { return SbkPySide2_QtCoreTypes[SBK_QTEXTBOUNDARYFINDER_BOUNDARYTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTextBoundaryFinder::BoundaryReason >() { return SbkPySide2_QtCoreTypes[SBK_QTEXTBOUNDARYFINDER_BOUNDARYREASON_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QTextBoundaryFinder::BoundaryReason> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QTEXTBOUNDARYFINDER_BOUNDARYREASON__IDX]; }
template<> inline PyTypeObject* SbkType< ::QTextBoundaryFinder >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTEXTBOUNDARYFINDER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QRectF >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QRECTF_IDX]); }
template<> inline PyTypeObject* SbkType< ::QRect >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QRECT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSizeF >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSIZEF_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSize >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSIZE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMarginsF >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QMARGINSF_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMargins >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QMARGINS_IDX]); }
template<> inline PyTypeObject* SbkType< ::QLineF::IntersectType >() { return SbkPySide2_QtCoreTypes[SBK_QLINEF_INTERSECTTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QLineF >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QLINEF_IDX]); }
template<> inline PyTypeObject* SbkType< ::QLine >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QLINE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QPointF >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QPOINTF_IDX]); }
template<> inline PyTypeObject* SbkType< ::QPoint >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QPOINT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QElapsedTimer::ClockType >() { return SbkPySide2_QtCoreTypes[SBK_QELAPSEDTIMER_CLOCKTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QElapsedTimer >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QELAPSEDTIMER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCryptographicHash::Algorithm >() { return SbkPySide2_QtCoreTypes[SBK_QCRYPTOGRAPHICHASH_ALGORITHM_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCryptographicHash >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QCRYPTOGRAPHICHASH_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCommandLineParser::SingleDashWordOptionMode >() { return SbkPySide2_QtCoreTypes[SBK_QCOMMANDLINEPARSER_SINGLEDASHWORDOPTIONMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCommandLineParser::OptionsAfterPositionalArgumentsMode >() { return SbkPySide2_QtCoreTypes[SBK_QCOMMANDLINEPARSER_OPTIONSAFTERPOSITIONALARGUMENTSMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCommandLineParser >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QCOMMANDLINEPARSER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCommandLineOption >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QCOMMANDLINEOPTION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCollatorSortKey >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QCOLLATORSORTKEY_IDX]); }
template<> inline PyTypeObject* SbkType< ::QByteArrayMatcher >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QBYTEARRAYMATCHER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QBitArray >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QBITARRAY_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWaitCondition >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QWAITCONDITION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSemaphore >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSEMAPHORE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWriteLocker >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QWRITELOCKER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QReadLocker >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QREADLOCKER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QReadWriteLock::RecursionMode >() { return SbkPySide2_QtCoreTypes[SBK_QREADWRITELOCK_RECURSIONMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QReadWriteLock >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QREADWRITELOCK_IDX]); }
template<> inline PyTypeObject* SbkType< ::QRunnable >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QRUNNABLE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QFactoryInterface >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QFACTORYINTERFACE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMimeDatabase::MatchMode >() { return SbkPySide2_QtCoreTypes[SBK_QMIMEDATABASE_MATCHMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMimeDatabase >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QMIMEDATABASE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMimeType >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QMIMETYPE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSystemSemaphore::AccessMode >() { return SbkPySide2_QtCoreTypes[SBK_QSYSTEMSEMAPHORE_ACCESSMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSystemSemaphore::SystemSemaphoreError >() { return SbkPySide2_QtCoreTypes[SBK_QSYSTEMSEMAPHORE_SYSTEMSEMAPHOREERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSystemSemaphore >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSYSTEMSEMAPHORE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMetaClassInfo >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QMETACLASSINFO_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMetaProperty >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QMETAPROPERTY_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMetaEnum >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QMETAENUM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QEvent::Type >() { return SbkPySide2_QtCoreTypes[SBK_QEVENT_TYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QChildEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QCHILDEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTimerEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTIMEREVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QDynamicPropertyChangeEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QDYNAMICPROPERTYCHANGEEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QBasicTimer >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QBASICTIMER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QJsonDocument::DataValidation >() { return SbkPySide2_QtCoreTypes[SBK_QJSONDOCUMENT_DATAVALIDATION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QJsonDocument::JsonFormat >() { return SbkPySide2_QtCoreTypes[SBK_QJSONDOCUMENT_JSONFORMAT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QJsonDocument >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QJSONDOCUMENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QJsonParseError::ParseError >() { return SbkPySide2_QtCoreTypes[SBK_QJSONPARSEERROR_PARSEERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QJsonParseError >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QJSONPARSEERROR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QJsonArray >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QJSONARRAY_IDX]); }
template<> inline PyTypeObject* SbkType< ::QJsonValue::Type >() { return SbkPySide2_QtCoreTypes[SBK_QJSONVALUE_TYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QJsonValue >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QJSONVALUE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QItemSelection >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QITEMSELECTION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QItemSelectionRange >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QITEMSELECTIONRANGE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QPersistentModelIndex >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QPERSISTENTMODELINDEX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QModelIndex >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QMODELINDEX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTemporaryDir >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTEMPORARYDIR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStorageInfo >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSTORAGEINFO_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStandardPaths::StandardLocation >() { return SbkPySide2_QtCoreTypes[SBK_QSTANDARDPATHS_STANDARDLOCATION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStandardPaths::LocateOption >() { return SbkPySide2_QtCoreTypes[SBK_QSTANDARDPATHS_LOCATEOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QStandardPaths::LocateOption> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QSTANDARDPATHS_LOCATEOPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QStandardPaths >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSTANDARDPATHS_IDX]); }
template<> inline PyTypeObject* SbkType< ::QProcessEnvironment >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QPROCESSENVIRONMENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QDir::Filter >() { return SbkPySide2_QtCoreTypes[SBK_QDIR_FILTER_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QDir::Filter> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QDIR_FILTER__IDX]; }
template<> inline PyTypeObject* SbkType< ::QDir::SortFlag >() { return SbkPySide2_QtCoreTypes[SBK_QDIR_SORTFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QDir::SortFlag> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QDIR_SORTFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QDir >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QDIR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QDirIterator::IteratorFlag >() { return SbkPySide2_QtCoreTypes[SBK_QDIRITERATOR_ITERATORFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QDirIterator::IteratorFlag> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QDIRITERATOR_ITERATORFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QDirIterator >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QDIRITERATOR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QFileInfo >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QFILEINFO_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTextStreamManipulator >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTEXTSTREAMMANIPULATOR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QLocale::Language >() { return SbkPySide2_QtCoreTypes[SBK_QLOCALE_LANGUAGE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QLocale::Script >() { return SbkPySide2_QtCoreTypes[SBK_QLOCALE_SCRIPT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QLocale::Country >() { return SbkPySide2_QtCoreTypes[SBK_QLOCALE_COUNTRY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QLocale::MeasurementSystem >() { return SbkPySide2_QtCoreTypes[SBK_QLOCALE_MEASUREMENTSYSTEM_IDX]; }
template<> inline PyTypeObject* SbkType< ::QLocale::FormatType >() { return SbkPySide2_QtCoreTypes[SBK_QLOCALE_FORMATTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QLocale::NumberOption >() { return SbkPySide2_QtCoreTypes[SBK_QLOCALE_NUMBEROPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QLocale::NumberOption> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QLOCALE_NUMBEROPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QLocale::CurrencySymbolFormat >() { return SbkPySide2_QtCoreTypes[SBK_QLOCALE_CURRENCYSYMBOLFORMAT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QLocale::QuotationStyle >() { return SbkPySide2_QtCoreTypes[SBK_QLOCALE_QUOTATIONSTYLE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QLocale >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QLOCALE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QResource >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QRESOURCE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTimeZone::TimeType >() { return SbkPySide2_QtCoreTypes[SBK_QTIMEZONE_TIMETYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTimeZone::NameType >() { return SbkPySide2_QtCoreTypes[SBK_QTIMEZONE_NAMETYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTimeZone >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTIMEZONE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTimeZone::OffsetData >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTIMEZONE_OFFSETDATA_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCollator >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QCOLLATOR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QDataStream::Version >() { return SbkPySide2_QtCoreTypes[SBK_QDATASTREAM_VERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QDataStream::ByteOrder >() { return SbkPySide2_QtCoreTypes[SBK_QDATASTREAM_BYTEORDER_IDX]; }
template<> inline PyTypeObject* SbkType< ::QDataStream::Status >() { return SbkPySide2_QtCoreTypes[SBK_QDATASTREAM_STATUS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QDataStream::FloatingPointPrecision >() { return SbkPySide2_QtCoreTypes[SBK_QDATASTREAM_FLOATINGPOINTPRECISION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QDataStream >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QDATASTREAM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QLibraryInfo::LibraryLocation >() { return SbkPySide2_QtCoreTypes[SBK_QLIBRARYINFO_LIBRARYLOCATION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QLibraryInfo >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QLIBRARYINFO_IDX]); }
template<> inline PyTypeObject* SbkType< ::QDateTime >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QDATETIME_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTime >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTIME_IDX]); }
template<> inline PyTypeObject* SbkType< ::QDate::MonthNameType >() { return SbkPySide2_QtCoreTypes[SBK_QDATE_MONTHNAMETYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QDate >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QDATE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTextDecoder >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTEXTDECODER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTextEncoder >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTEXTENCODER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTextCodec::ConversionFlag >() { return SbkPySide2_QtCoreTypes[SBK_QTEXTCODEC_CONVERSIONFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QTextCodec::ConversionFlag> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QTEXTCODEC_CONVERSIONFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QTextCodec >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTEXTCODEC_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTextCodec::ConverterState >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTEXTCODEC_CONVERTERSTATE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QEasingCurve::Type >() { return SbkPySide2_QtCoreTypes[SBK_QEASINGCURVE_TYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QEasingCurve >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QEASINGCURVE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QObject >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QOBJECT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QFileSelector >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QFILESELECTOR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QThreadPool >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTHREADPOOL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QThread::Priority >() { return SbkPySide2_QtCoreTypes[SBK_QTHREAD_PRIORITY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QThread >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTHREAD_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractAnimation::Direction >() { return SbkPySide2_QtCoreTypes[SBK_QABSTRACTANIMATION_DIRECTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractAnimation::State >() { return SbkPySide2_QtCoreTypes[SBK_QABSTRACTANIMATION_STATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractAnimation::DeletionPolicy >() { return SbkPySide2_QtCoreTypes[SBK_QABSTRACTANIMATION_DELETIONPOLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractAnimation >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QABSTRACTANIMATION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QVariantAnimation >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QVARIANTANIMATION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QPropertyAnimation >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QPROPERTYANIMATION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QPauseAnimation >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QPAUSEANIMATION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAnimationGroup >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QANIMATIONGROUP_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSequentialAnimationGroup >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSEQUENTIALANIMATIONGROUP_IDX]); }
template<> inline PyTypeObject* SbkType< ::QParallelAnimationGroup >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QPARALLELANIMATIONGROUP_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWinEventNotifier >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QWINEVENTNOTIFIER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTranslator >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTRANSLATOR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSettings::Status >() { return SbkPySide2_QtCoreTypes[SBK_QSETTINGS_STATUS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSettings::Format >() { return SbkPySide2_QtCoreTypes[SBK_QSETTINGS_FORMAT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSettings::Scope >() { return SbkPySide2_QtCoreTypes[SBK_QSETTINGS_SCOPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSettings >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSETTINGS_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTimer >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTIMER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSocketNotifier::Type >() { return SbkPySide2_QtCoreTypes[SBK_QSOCKETNOTIFIER_TYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSocketNotifier >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSOCKETNOTIFIER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSignalMapper >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSIGNALMAPPER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QFileSystemWatcher >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QFILESYSTEMWATCHER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractTransition::TransitionType >() { return SbkPySide2_QtCoreTypes[SBK_QABSTRACTTRANSITION_TRANSITIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractTransition >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QABSTRACTTRANSITION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSignalTransition >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSIGNALTRANSITION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QEventTransition >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QEVENTTRANSITION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTimeLine::State >() { return SbkPySide2_QtCoreTypes[SBK_QTIMELINE_STATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTimeLine::Direction >() { return SbkPySide2_QtCoreTypes[SBK_QTIMELINE_DIRECTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTimeLine::CurveShape >() { return SbkPySide2_QtCoreTypes[SBK_QTIMELINE_CURVESHAPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTimeLine >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTIMELINE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractState >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QABSTRACTSTATE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QState::ChildMode >() { return SbkPySide2_QtCoreTypes[SBK_QSTATE_CHILDMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QState::RestorePolicy >() { return SbkPySide2_QtCoreTypes[SBK_QSTATE_RESTOREPOLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QState >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSTATE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStateMachine::EventPriority >() { return SbkPySide2_QtCoreTypes[SBK_QSTATEMACHINE_EVENTPRIORITY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStateMachine::Error >() { return SbkPySide2_QtCoreTypes[SBK_QSTATEMACHINE_ERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QStateMachine >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSTATEMACHINE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStateMachine::WrappedEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSTATEMACHINE_WRAPPEDEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStateMachine::SignalEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSTATEMACHINE_SIGNALEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QHistoryState::HistoryType >() { return SbkPySide2_QtCoreTypes[SBK_QHISTORYSTATE_HISTORYTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QHistoryState >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QHISTORYSTATE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QFinalState >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QFINALSTATE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QPluginLoader >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QPLUGINLOADER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractItemModel::LayoutChangeHint >() { return SbkPySide2_QtCoreTypes[SBK_QABSTRACTITEMMODEL_LAYOUTCHANGEHINT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractItemModel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QABSTRACTITEMMODEL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractProxyModel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QABSTRACTPROXYMODEL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSortFilterProxyModel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSORTFILTERPROXYMODEL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractListModel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QABSTRACTLISTMODEL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QStringListModel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSTRINGLISTMODEL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractTableModel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QABSTRACTTABLEMODEL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractEventDispatcher >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QABSTRACTEVENTDISPATCHER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractEventDispatcher::TimerInfo >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QABSTRACTEVENTDISPATCHER_TIMERINFO_IDX]); }
template<> inline PyTypeObject* SbkType< ::QIODevice::OpenModeFlag >() { return SbkPySide2_QtCoreTypes[SBK_QIODEVICE_OPENMODEFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QIODevice::OpenModeFlag> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QIODEVICE_OPENMODEFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QIODevice >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QIODEVICE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QBuffer >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QBUFFER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QProcess::ProcessError >() { return SbkPySide2_QtCoreTypes[SBK_QPROCESS_PROCESSERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QProcess::ProcessState >() { return SbkPySide2_QtCoreTypes[SBK_QPROCESS_PROCESSSTATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QProcess::ProcessChannel >() { return SbkPySide2_QtCoreTypes[SBK_QPROCESS_PROCESSCHANNEL_IDX]; }
template<> inline PyTypeObject* SbkType< ::QProcess::ProcessChannelMode >() { return SbkPySide2_QtCoreTypes[SBK_QPROCESS_PROCESSCHANNELMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QProcess::InputChannelMode >() { return SbkPySide2_QtCoreTypes[SBK_QPROCESS_INPUTCHANNELMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QProcess::ExitStatus >() { return SbkPySide2_QtCoreTypes[SBK_QPROCESS_EXITSTATUS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QProcess >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QPROCESS_IDX]); }
template<> inline PyTypeObject* SbkType< ::QFileDevice::FileError >() { return SbkPySide2_QtCoreTypes[SBK_QFILEDEVICE_FILEERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFileDevice::Permission >() { return SbkPySide2_QtCoreTypes[SBK_QFILEDEVICE_PERMISSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QFileDevice::Permission> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QFILEDEVICE_PERMISSION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QFileDevice::FileHandleFlag >() { return SbkPySide2_QtCoreTypes[SBK_QFILEDEVICE_FILEHANDLEFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QFileDevice::FileHandleFlag> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QFILEDEVICE_FILEHANDLEFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QFileDevice::MemoryMapFlags >() { return SbkPySide2_QtCoreTypes[SBK_QFILEDEVICE_MEMORYMAPFLAGS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFileDevice >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QFILEDEVICE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSaveFile >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSAVEFILE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QFile >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QFILE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTemporaryFile >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTEMPORARYFILE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QTextStream::RealNumberNotation >() { return SbkPySide2_QtCoreTypes[SBK_QTEXTSTREAM_REALNUMBERNOTATION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTextStream::FieldAlignment >() { return SbkPySide2_QtCoreTypes[SBK_QTEXTSTREAM_FIELDALIGNMENT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTextStream::Status >() { return SbkPySide2_QtCoreTypes[SBK_QTEXTSTREAM_STATUS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTextStream::NumberFlag >() { return SbkPySide2_QtCoreTypes[SBK_QTEXTSTREAM_NUMBERFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QTextStream::NumberFlag> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QTEXTSTREAM_NUMBERFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QTextStream >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QTEXTSTREAM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QEventLoop::ProcessEventsFlag >() { return SbkPySide2_QtCoreTypes[SBK_QEVENTLOOP_PROCESSEVENTSFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QEventLoop::ProcessEventsFlag> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QEVENTLOOP_PROCESSEVENTSFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QEventLoop >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QEVENTLOOP_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMimeData >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QMIMEDATA_IDX]); }
template<> inline PyTypeObject* SbkType< ::QItemSelectionModel::SelectionFlag >() { return SbkPySide2_QtCoreTypes[SBK_QITEMSELECTIONMODEL_SELECTIONFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QItemSelectionModel::SelectionFlag> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QITEMSELECTIONMODEL_SELECTIONFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QItemSelectionModel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QITEMSELECTIONMODEL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCoreApplication >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QCOREAPPLICATION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QRegExp::PatternSyntax >() { return SbkPySide2_QtCoreTypes[SBK_QREGEXP_PATTERNSYNTAX_IDX]; }
template<> inline PyTypeObject* SbkType< ::QRegExp::CaretMode >() { return SbkPySide2_QtCoreTypes[SBK_QREGEXP_CARETMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QRegExp >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QREGEXP_IDX]); }
template<> inline PyTypeObject* SbkType< ::QByteArray::Base64Option >() { return SbkPySide2_QtCoreTypes[SBK_QBYTEARRAY_BASE64OPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QByteArray::Base64Option> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QBYTEARRAY_BASE64OPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QByteArray >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QBYTEARRAY_IDX]); }
template<> inline PyTypeObject* SbkType< ::QUrl::ParsingMode >() { return SbkPySide2_QtCoreTypes[SBK_QURL_PARSINGMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QUrl::UrlFormattingOption >() { return SbkPySide2_QtCoreTypes[SBK_QURL_URLFORMATTINGOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QUrl::ComponentFormattingOption >() { return SbkPySide2_QtCoreTypes[SBK_QURL_COMPONENTFORMATTINGOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QUrl::ComponentFormattingOption> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QURL_COMPONENTFORMATTINGOPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QUrl::UserInputResolutionOption >() { return SbkPySide2_QtCoreTypes[SBK_QURL_USERINPUTRESOLUTIONOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QUrl::UserInputResolutionOption> >() { return SbkPySide2_QtCoreTypes[SBK_QFLAGS_QURL_USERINPUTRESOLUTIONOPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QUrl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QURL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMetaObject::Connection >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QMETAOBJECT_CONNECTION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGenericArgument >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QGENERICARGUMENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMetaObject::Call >() { return SbkPySide2_QtCoreTypes[SBK_QMETAOBJECT_CALL_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMetaObject >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QMETAOBJECT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGenericReturnArgument >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QGENERICRETURNARGUMENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMetaMethod::Access >() { return SbkPySide2_QtCoreTypes[SBK_QMETAMETHOD_ACCESS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMetaMethod::MethodType >() { return SbkPySide2_QtCoreTypes[SBK_QMETAMETHOD_METHODTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMetaMethod >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QMETAMETHOD_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMutexLocker >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QMUTEXLOCKER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QBasicMutex >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QBASICMUTEX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMutex::RecursionMode >() { return SbkPySide2_QtCoreTypes[SBK_QMUTEX_RECURSIONMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMutex >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QMUTEX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMessageLogContext >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QMESSAGELOGCONTEXT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSysInfo::Sizes >() { return SbkPySide2_QtCoreTypes[SBK_QSYSINFO_SIZES_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSysInfo::Endian >() { return SbkPySide2_QtCoreTypes[SBK_QSYSINFO_ENDIAN_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSysInfo::WinVersion >() { return SbkPySide2_QtCoreTypes[SBK_QSYSINFO_WINVERSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSysInfo >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtCoreTypes[SBK_QSYSINFO_IDX]); }

} // namespace Shiboken

#endif // SBK_QTCORE_PYTHON_H

