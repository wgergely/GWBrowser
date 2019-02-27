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


#ifndef SBK_QTWEBENGINEWIDGETS_PYTHON_H
#define SBK_QTWEBENGINEWIDGETS_PYTHON_H

#include <sbkpython.h>
#include <sbkconverter.h>
#include <sbkenum.h>
#include <basewrapper.h>
#include <bindingmanager.h>
#include <memory>

#include <pysidesignal.h>
// Module Includes
#include <pyside2_qtcore_python.h>
#include <pyside2_qtgui_python.h>
#include <pyside2_qtwidgets_python.h>
#include <pyside2_qtnetwork_python.h>
#include <pyside2_qtwebchannel_python.h>

// Binded library includes
#include <qwebenginecertificateerror.h>
#include <qwebenginepage.h>
#include <qwebengineprofile.h>
#include <qwebenginescript.h>
#include <qwebenginedownloaditem.h>
#include <qwebenginehistory.h>
#include <qwebengineview.h>
// Conversion Includes - Primitive Types
#include <QStringList>
#include <QString>
#include <qabstractitemmodel.h>
#include <signalmanager.h>
#include <wtypes.h>

// Conversion Includes - Container Types
#include <QStack>
#include <pysideqflags.h>
#include <QMultiMap>
#include <QLinkedList>
#include <QQueue>
#include <QList>
#include <QSet>
#include <QPair>
#include <QVector>
#include <QMap>

// Type indices
#define SBK_QWEBENGINESCRIPT_IDX                                     18
#define SBK_QWEBENGINESCRIPT_INJECTIONPOINT_IDX                      19
#define SBK_QWEBENGINESCRIPT_SCRIPTWORLDID_IDX                       20
#define SBK_QWEBENGINEHISTORYITEM_IDX                                5
#define SBK_QWEBENGINECERTIFICATEERROR_IDX                           1
#define SBK_QWEBENGINECERTIFICATEERROR_ERROR_IDX                     2
#define SBK_QWEBENGINEDOWNLOADITEM_IDX                               3
#define SBK_QWEBENGINEDOWNLOADITEM_DOWNLOADSTATE_IDX                 4
#define SBK_QWEBENGINEPROFILE_IDX                                    15
#define SBK_QWEBENGINEPROFILE_HTTPCACHETYPE_IDX                      16
#define SBK_QWEBENGINEPROFILE_PERSISTENTCOOKIESPOLICY_IDX            17
#define SBK_QWEBENGINEPAGE_IDX                                       6
#define SBK_QWEBENGINEPAGE_WEBACTION_IDX                             13
#define SBK_QWEBENGINEPAGE_FINDFLAG_IDX                              9
#define SBK_QFLAGS_QWEBENGINEPAGE_FINDFLAG__IDX                      0
#define SBK_QWEBENGINEPAGE_WEBWINDOWTYPE_IDX                         14
#define SBK_QWEBENGINEPAGE_PERMISSIONPOLICY_IDX                      12
#define SBK_QWEBENGINEPAGE_NAVIGATIONTYPE_IDX                        11
#define SBK_QWEBENGINEPAGE_FEATURE_IDX                               7
#define SBK_QWEBENGINEPAGE_FILESELECTIONMODE_IDX                     8
#define SBK_QWEBENGINEPAGE_JAVASCRIPTCONSOLEMESSAGELEVEL_IDX         10
#define SBK_QWEBENGINEVIEW_IDX                                       21
#define SBK_QtWebEngineWidgets_IDX_COUNT                             22

// This variable stores all Python types exported by this module.
extern PyTypeObject** SbkPySide2_QtWebEngineWidgetsTypes;

// This variable stores all type converters exported by this module.
extern SbkConverter** SbkPySide2_QtWebEngineWidgetsTypeConverters;

// Converter indices
#define SBK_QTWEBENGINEWIDGETS_QLIST_QOBJECTPTR_IDX                  0 // const QList<QObject * > &
#define SBK_QTWEBENGINEWIDGETS_QLIST_QBYTEARRAY_IDX                  1 // QList<QByteArray >
#define SBK_QTWEBENGINEWIDGETS_QLIST_QURL_IDX                        2 // const QList<QUrl > &
#define SBK_QTWEBENGINEWIDGETS_QLIST_QACTIONPTR_IDX                  3 // QList<QAction * >
#define SBK_QTWEBENGINEWIDGETS_QLIST_QVARIANT_IDX                    4 // QList<QVariant >
#define SBK_QTWEBENGINEWIDGETS_QLIST_QSTRING_IDX                     5 // QList<QString >
#define SBK_QTWEBENGINEWIDGETS_QMAP_QSTRING_QVARIANT_IDX             6 // QMap<QString, QVariant >
#define SBK_QtWebEngineWidgets_CONVERTERS_IDX_COUNT                  7

// Macros for type check

namespace Shiboken
{

// PyType functions, to get the PyObjectType for a type T
template<> inline PyTypeObject* SbkType< ::QWebEngineScript::InjectionPoint >() { return SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINESCRIPT_INJECTIONPOINT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWebEngineScript::ScriptWorldId >() { return SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINESCRIPT_SCRIPTWORLDID_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWebEngineScript >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINESCRIPT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWebEngineHistoryItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINEHISTORYITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWebEngineCertificateError::Error >() { return SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINECERTIFICATEERROR_ERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWebEngineCertificateError >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINECERTIFICATEERROR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWebEngineDownloadItem::DownloadState >() { return SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINEDOWNLOADITEM_DOWNLOADSTATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWebEngineDownloadItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINEDOWNLOADITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWebEngineProfile::HttpCacheType >() { return SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINEPROFILE_HTTPCACHETYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWebEngineProfile::PersistentCookiesPolicy >() { return SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINEPROFILE_PERSISTENTCOOKIESPOLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWebEngineProfile >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINEPROFILE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWebEnginePage::WebAction >() { return SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINEPAGE_WEBACTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWebEnginePage::FindFlag >() { return SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINEPAGE_FINDFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QWebEnginePage::FindFlag> >() { return SbkPySide2_QtWebEngineWidgetsTypes[SBK_QFLAGS_QWEBENGINEPAGE_FINDFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QWebEnginePage::WebWindowType >() { return SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINEPAGE_WEBWINDOWTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWebEnginePage::PermissionPolicy >() { return SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINEPAGE_PERMISSIONPOLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWebEnginePage::NavigationType >() { return SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINEPAGE_NAVIGATIONTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWebEnginePage::Feature >() { return SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINEPAGE_FEATURE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWebEnginePage::FileSelectionMode >() { return SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINEPAGE_FILESELECTIONMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWebEnginePage::JavaScriptConsoleMessageLevel >() { return SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINEPAGE_JAVASCRIPTCONSOLEMESSAGELEVEL_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWebEnginePage >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINEPAGE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWebEngineView >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWebEngineWidgetsTypes[SBK_QWEBENGINEVIEW_IDX]); }

} // namespace Shiboken

#endif // SBK_QTWEBENGINEWIDGETS_PYTHON_H

