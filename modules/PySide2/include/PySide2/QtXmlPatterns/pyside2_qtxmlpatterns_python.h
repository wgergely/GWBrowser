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


#ifndef SBK_QTXMLPATTERNS_PYTHON_H
#define SBK_QTXMLPATTERNS_PYTHON_H

#include <sbkpython.h>
#include <sbkconverter.h>
#include <sbkenum.h>
#include <basewrapper.h>
#include <bindingmanager.h>
#include <memory>

#include <pysidesignal.h>
// Module Includes
#include <pyside2_qtcore_python.h>

// Binded library includes
#include <qxmlserializer.h>
#include <qsourcelocation.h>
#include <qabstracturiresolver.h>
#include <qxmlnamepool.h>
#include <qxmlformatter.h>
#include <qxmlschemavalidator.h>
#include <qxmlschema.h>
#include <qabstractxmlnodemodel.h>
#include <qxmlname.h>
#include <qxmlquery.h>
#include <qabstractmessagehandler.h>
#include <qxmlresultitems.h>
#include <qabstractxmlreceiver.h>
// Conversion Includes - Primitive Types
#include <QStringList>
#include <QString>
#include <signalmanager.h>
#include <qabstractitemmodel.h>
#include <wtypes.h>

// Conversion Includes - Container Types
#include <QLinkedList>
#include <QMultiMap>
#include <QSet>
#include <QList>
#include <QVector>
#include <QStack>
#include <QMap>
#include <QPair>
#include <pysideqflags.h>
#include <QQueue>

// Type indices
#define SBK_QXMLRESULTITEMS_IDX                                      16
#define SBK_QXMLNAMEPOOL_IDX                                         10
#define SBK_QABSTRACTXMLRECEIVER_IDX                                 5
#define SBK_QXMLSERIALIZER_IDX                                       19
#define SBK_QXMLFORMATTER_IDX                                        7
#define SBK_QXMLITEM_IDX                                             8
#define SBK_QABSTRACTXMLNODEMODEL_IDX                                2
#define SBK_QABSTRACTXMLNODEMODEL_SIMPLEAXIS_IDX                     4
#define SBK_QABSTRACTXMLNODEMODEL_NODECOPYSETTING_IDX                3
#define SBK_QXMLNODEMODELINDEX_IDX                                   11
#define SBK_QXMLNODEMODELINDEX_NODEKIND_IDX                          13
#define SBK_QXMLNODEMODELINDEX_DOCUMENTORDER_IDX                     12
#define SBK_QXMLNAME_IDX                                             9
#define SBK_QSOURCELOCATION_IDX                                      6
#define SBK_QABSTRACTURIRESOLVER_IDX                                 1
#define SBK_QXMLQUERY_IDX                                            14
#define SBK_QXMLQUERY_QUERYLANGUAGE_IDX                              15
#define SBK_QXMLSCHEMAVALIDATOR_IDX                                  18
#define SBK_QABSTRACTMESSAGEHANDLER_IDX                              0
#define SBK_QXMLSCHEMA_IDX                                           17
#define SBK_QtXmlPatterns_IDX_COUNT                                  20

// This variable stores all Python types exported by this module.
extern PyTypeObject** SbkPySide2_QtXmlPatternsTypes;

// This variable stores all type converters exported by this module.
extern SbkConverter** SbkPySide2_QtXmlPatternsTypeConverters;

// Converter indices
#define SBK_QTXMLPATTERNS_QVECTOR_QXMLNODEMODELINDEX_IDX             0 // QVector<QXmlNodeModelIndex >
#define SBK_QTXMLPATTERNS_QVECTOR_QXMLNAME_IDX                       1 // QVector<QXmlName >
#define SBK_QTXMLPATTERNS_QLIST_QOBJECTPTR_IDX                       2 // const QList<QObject * > &
#define SBK_QTXMLPATTERNS_QLIST_QBYTEARRAY_IDX                       3 // QList<QByteArray >
#define SBK_QTXMLPATTERNS_QLIST_QVARIANT_IDX                         4 // QList<QVariant >
#define SBK_QTXMLPATTERNS_QLIST_QSTRING_IDX                          5 // QList<QString >
#define SBK_QTXMLPATTERNS_QMAP_QSTRING_QVARIANT_IDX                  6 // QMap<QString, QVariant >
#define SBK_QtXmlPatterns_CONVERTERS_IDX_COUNT                       7

// Macros for type check

namespace Shiboken
{

// PyType functions, to get the PyObjectType for a type T
template<> inline PyTypeObject* SbkType< ::QXmlResultItems >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtXmlPatternsTypes[SBK_QXMLRESULTITEMS_IDX]); }
template<> inline PyTypeObject* SbkType< ::QXmlNamePool >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtXmlPatternsTypes[SBK_QXMLNAMEPOOL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractXmlReceiver >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtXmlPatternsTypes[SBK_QABSTRACTXMLRECEIVER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QXmlSerializer >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtXmlPatternsTypes[SBK_QXMLSERIALIZER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QXmlFormatter >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtXmlPatternsTypes[SBK_QXMLFORMATTER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QXmlItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtXmlPatternsTypes[SBK_QXMLITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractXmlNodeModel::SimpleAxis >() { return SbkPySide2_QtXmlPatternsTypes[SBK_QABSTRACTXMLNODEMODEL_SIMPLEAXIS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractXmlNodeModel::NodeCopySetting >() { return SbkPySide2_QtXmlPatternsTypes[SBK_QABSTRACTXMLNODEMODEL_NODECOPYSETTING_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractXmlNodeModel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtXmlPatternsTypes[SBK_QABSTRACTXMLNODEMODEL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QXmlNodeModelIndex::NodeKind >() { return SbkPySide2_QtXmlPatternsTypes[SBK_QXMLNODEMODELINDEX_NODEKIND_IDX]; }
template<> inline PyTypeObject* SbkType< ::QXmlNodeModelIndex::DocumentOrder >() { return SbkPySide2_QtXmlPatternsTypes[SBK_QXMLNODEMODELINDEX_DOCUMENTORDER_IDX]; }
template<> inline PyTypeObject* SbkType< ::QXmlNodeModelIndex >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtXmlPatternsTypes[SBK_QXMLNODEMODELINDEX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QXmlName >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtXmlPatternsTypes[SBK_QXMLNAME_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSourceLocation >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtXmlPatternsTypes[SBK_QSOURCELOCATION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractUriResolver >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtXmlPatternsTypes[SBK_QABSTRACTURIRESOLVER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QXmlQuery::QueryLanguage >() { return SbkPySide2_QtXmlPatternsTypes[SBK_QXMLQUERY_QUERYLANGUAGE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QXmlQuery >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtXmlPatternsTypes[SBK_QXMLQUERY_IDX]); }
template<> inline PyTypeObject* SbkType< ::QXmlSchemaValidator >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtXmlPatternsTypes[SBK_QXMLSCHEMAVALIDATOR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractMessageHandler >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtXmlPatternsTypes[SBK_QABSTRACTMESSAGEHANDLER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QXmlSchema >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtXmlPatternsTypes[SBK_QXMLSCHEMA_IDX]); }

} // namespace Shiboken

#endif // SBK_QTXMLPATTERNS_PYTHON_H

