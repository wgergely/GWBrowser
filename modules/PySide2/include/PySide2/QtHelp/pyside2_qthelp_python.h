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


#ifndef SBK_QTHELP_PYTHON_H
#define SBK_QTHELP_PYTHON_H

#include <sbkpython.h>
#include <sbkconverter.h>
#include <sbkenum.h>
#include <basewrapper.h>
#include <bindingmanager.h>
#include <memory>

#include <pysidesignal.h>
// Module Includes
#include <pyside2_qtwidgets_python.h>
#include <pyside2_qtgui_python.h>
#include <pyside2_qtcore_python.h>

// Binded library includes
#include <qhelpenginecore.h>
#include <qhelpsearchengine.h>
#include <qhelpindexwidget.h>
#include <qhelpsearchresultwidget.h>
#include <qhelpsearchquerywidget.h>
#include <qhelpcontentwidget.h>
#include <qhelpengine.h>
// Conversion Includes - Primitive Types
#include <qabstractitemmodel.h>
#include <QString>
#include <QStringList>
#include <wtypes.h>
#include <signalmanager.h>

// Conversion Includes - Container Types
#include <QMultiMap>
#include <QVector>
#include <QMap>
#include <QPair>
#include <pysideqflags.h>
#include <QList>
#include <QLinkedList>
#include <QStack>
#include <QSet>
#include <QQueue>

// Type indices
#define SBK_QHELPSEARCHQUERY_IDX                                     8
#define SBK_QHELPSEARCHQUERY_FIELDNAME_IDX                           9
#define SBK_QHELPCONTENTITEM_IDX                                     0
#define SBK_QHELPENGINECORE_IDX                                      4
#define SBK_QHELPENGINE_IDX                                          3
#define SBK_QHELPSEARCHENGINE_IDX                                    7
#define SBK_QHELPCONTENTMODEL_IDX                                    1
#define SBK_QHELPINDEXMODEL_IDX                                      5
#define SBK_QHELPSEARCHRESULTWIDGET_IDX                              11
#define SBK_QHELPSEARCHQUERYWIDGET_IDX                               10
#define SBK_QHELPINDEXWIDGET_IDX                                     6
#define SBK_QHELPCONTENTWIDGET_IDX                                   2
#define SBK_QtHelp_IDX_COUNT                                         12

// This variable stores all Python types exported by this module.
extern PyTypeObject** SbkPySide2_QtHelpTypes;

// This variable stores all type converters exported by this module.
extern SbkConverter** SbkPySide2_QtHelpTypeConverters;

// Converter indices
#define SBK_QTHELP_QLIST_QOBJECTPTR_IDX                              0 // const QList<QObject * > &
#define SBK_QTHELP_QLIST_QBYTEARRAY_IDX                              1 // QList<QByteArray >
#define SBK_QTHELP_QLIST_QURL_IDX                                    2 // QList<QUrl >
#define SBK_QTHELP_QLIST_QSTRINGLIST_IDX                             3 // QList<QStringList >
#define SBK_QTHELP_QMAP_QSTRING_QURL_IDX                             4 // QMap<QString, QUrl >
#define SBK_QTHELP_QPAIR_QSTRING_QSTRING_IDX                         5 // QPair<QString, QString >
#define SBK_QTHELP_QLIST_QPAIR_QSTRING_QSTRING_IDX                   6 // QList<QPair<QString, QString > >
#define SBK_QTHELP_QLIST_QHELPSEARCHQUERY_IDX                        7 // QList<QHelpSearchQuery >
#define SBK_QTHELP_QVECTOR_INT_IDX                                   8 // const QVector<int > &
#define SBK_QTHELP_QHASH_INT_QBYTEARRAY_IDX                          9 // const QHash<int, QByteArray > &
#define SBK_QTHELP_QMAP_INT_QVARIANT_IDX                             10 // QMap<int, QVariant >
#define SBK_QTHELP_QLIST_QPERSISTENTMODELINDEX_IDX                   11 // const QList<QPersistentModelIndex > &
#define SBK_QTHELP_QLIST_QACTIONPTR_IDX                              12 // QList<QAction * >
#define SBK_QTHELP_QLIST_QWIDGETPTR_IDX                              13 // QList<QWidget * >
#define SBK_QTHELP_QLIST_QVARIANT_IDX                                14 // QList<QVariant >
#define SBK_QTHELP_QLIST_QSTRING_IDX                                 15 // QList<QString >
#define SBK_QTHELP_QMAP_QSTRING_QVARIANT_IDX                         16 // QMap<QString, QVariant >
#define SBK_QtHelp_CONVERTERS_IDX_COUNT                              17

// Macros for type check

namespace Shiboken
{

// PyType functions, to get the PyObjectType for a type T
template<> inline PyTypeObject* SbkType< ::QHelpSearchQuery::FieldName >() { return SbkPySide2_QtHelpTypes[SBK_QHELPSEARCHQUERY_FIELDNAME_IDX]; }
template<> inline PyTypeObject* SbkType< ::QHelpSearchQuery >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtHelpTypes[SBK_QHELPSEARCHQUERY_IDX]); }
template<> inline PyTypeObject* SbkType< ::QHelpContentItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtHelpTypes[SBK_QHELPCONTENTITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QHelpEngineCore >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtHelpTypes[SBK_QHELPENGINECORE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QHelpEngine >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtHelpTypes[SBK_QHELPENGINE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QHelpSearchEngine >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtHelpTypes[SBK_QHELPSEARCHENGINE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QHelpContentModel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtHelpTypes[SBK_QHELPCONTENTMODEL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QHelpIndexModel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtHelpTypes[SBK_QHELPINDEXMODEL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QHelpSearchResultWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtHelpTypes[SBK_QHELPSEARCHRESULTWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QHelpSearchQueryWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtHelpTypes[SBK_QHELPSEARCHQUERYWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QHelpIndexWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtHelpTypes[SBK_QHELPINDEXWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QHelpContentWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtHelpTypes[SBK_QHELPCONTENTWIDGET_IDX]); }

} // namespace Shiboken

#endif // SBK_QTHELP_PYTHON_H

