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


#ifndef SBK_QTSQL_PYTHON_H
#define SBK_QTSQL_PYTHON_H

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
#include <qsqldriver.h>
#include <qsqlerror.h>
#include <qsqlrelationaltablemodel.h>
#include <qsqlquerymodel.h>
#include <qsqlquery.h>
#include <qsqlfield.h>
#include <qsql.h>
#include <qsqlresult.h>
#include <qsqlindex.h>
#include <qsqldatabase.h>
#include <qsqlrelationaldelegate.h>
#include <qsqlrecord.h>
#include <qsqltablemodel.h>
// Conversion Includes - Primitive Types
#include <QString>
#include <signalmanager.h>
#include <qabstractitemmodel.h>
#include <wtypes.h>
#include <QStringList>

// Conversion Includes - Container Types
#include <QLinkedList>
#include <QSet>
#include <QQueue>
#include <pysideqflags.h>
#include <QList>
#include <QPair>
#include <QStack>
#include <QMultiMap>
#include <QVector>
#include <QMap>

// Type indices
#define SBK_QSQL_IDX                                                 1
#define SBK_QSQL_LOCATION_IDX                                        2
#define SBK_QSQL_PARAMTYPEFLAG_IDX                                   4
#define SBK_QFLAGS_QSQL_PARAMTYPEFLAG__IDX                           0
#define SBK_QSQL_TABLETYPE_IDX                                       5
#define SBK_QSQL_NUMERICALPRECISIONPOLICY_IDX                        3
#define SBK_QSQLRELATION_IDX                                         23
#define SBK_QSQLRESULT_IDX                                           27
#define SBK_QSQLRESULT_BINDINGSYNTAX_IDX                             28
#define SBK_QSQLRESULT_VIRTUALHOOKOPERATION_IDX                      29
#define SBK_QSQLRECORD_IDX                                           22
#define SBK_QSQLINDEX_IDX                                            18
#define SBK_QSQLFIELD_IDX                                            16
#define SBK_QSQLFIELD_REQUIREDSTATUS_IDX                             17
#define SBK_QSQLERROR_IDX                                            14
#define SBK_QSQLERROR_ERRORTYPE_IDX                                  15
#define SBK_QSQLDATABASE_IDX                                         6
#define SBK_QSQLQUERY_IDX                                            19
#define SBK_QSQLQUERY_BATCHEXECUTIONMODE_IDX                         20
#define SBK_QSQLDRIVERCREATORBASE_IDX                                13
#define SBK_QSQLDRIVER_IDX                                           7
#define SBK_QSQLDRIVER_DRIVERFEATURE_IDX                             9
#define SBK_QSQLDRIVER_STATEMENTTYPE_IDX                             12
#define SBK_QSQLDRIVER_IDENTIFIERTYPE_IDX                            10
#define SBK_QSQLDRIVER_NOTIFICATIONSOURCE_IDX                        11
#define SBK_QSQLDRIVER_DBMSTYPE_IDX                                  8
#define SBK_QSQLRELATIONALDELEGATE_IDX                               24
#define SBK_QSQLQUERYMODEL_IDX                                       21
#define SBK_QSQLTABLEMODEL_IDX                                       30
#define SBK_QSQLTABLEMODEL_EDITSTRATEGY_IDX                          31
#define SBK_QSQLRELATIONALTABLEMODEL_IDX                             25
#define SBK_QSQLRELATIONALTABLEMODEL_JOINMODE_IDX                    26
#define SBK_QtSql_IDX_COUNT                                          32

// This variable stores all Python types exported by this module.
extern PyTypeObject** SbkPySide2_QtSqlTypes;

// This variable stores all type converters exported by this module.
extern SbkConverter** SbkPySide2_QtSqlTypeConverters;

// Converter indices
#define SBK_QTSQL_QVECTOR_QVARIANT_IDX                               0 // QVector<QVariant > &
#define SBK_QTSQL_QMAP_QSTRING_QVARIANT_IDX                          1 // QMap<QString, QVariant >
#define SBK_QTSQL_QLIST_QOBJECTPTR_IDX                               2 // const QList<QObject * > &
#define SBK_QTSQL_QLIST_QBYTEARRAY_IDX                               3 // QList<QByteArray >
#define SBK_QTSQL_QVECTOR_INT_IDX                                    4 // QVector<int >
#define SBK_QTSQL_QHASH_INT_QBYTEARRAY_IDX                           5 // const QHash<int, QByteArray > &
#define SBK_QTSQL_QMAP_INT_QVARIANT_IDX                              6 // QMap<int, QVariant >
#define SBK_QTSQL_QLIST_QPERSISTENTMODELINDEX_IDX                    7 // const QList<QPersistentModelIndex > &
#define SBK_QTSQL_QLIST_QVARIANT_IDX                                 8 // QList<QVariant >
#define SBK_QTSQL_QLIST_QSTRING_IDX                                  9 // QList<QString >
#define SBK_QtSql_CONVERTERS_IDX_COUNT                               10

// Macros for type check

// Protected enum surrogates
enum PySide2_QtSql_QSqlResult_BindingSyntax_Surrogate {};
enum PySide2_QtSql_QSqlResult_VirtualHookOperation_Surrogate {};

namespace Shiboken
{

// PyType functions, to get the PyObjectType for a type T
template<> inline PyTypeObject* SbkType< ::QSql::Location >() { return SbkPySide2_QtSqlTypes[SBK_QSQL_LOCATION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSql::ParamTypeFlag >() { return SbkPySide2_QtSqlTypes[SBK_QSQL_PARAMTYPEFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QSql::ParamTypeFlag> >() { return SbkPySide2_QtSqlTypes[SBK_QFLAGS_QSQL_PARAMTYPEFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QSql::TableType >() { return SbkPySide2_QtSqlTypes[SBK_QSQL_TABLETYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSql::NumericalPrecisionPolicy >() { return SbkPySide2_QtSqlTypes[SBK_QSQL_NUMERICALPRECISIONPOLICY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSqlRelation >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtSqlTypes[SBK_QSQLRELATION_IDX]); }
template<> inline PyTypeObject* SbkType< ::PySide2_QtSql_QSqlResult_BindingSyntax_Surrogate >() { return SbkPySide2_QtSqlTypes[SBK_QSQLRESULT_BINDINGSYNTAX_IDX]; }
template<> inline PyTypeObject* SbkType< ::PySide2_QtSql_QSqlResult_VirtualHookOperation_Surrogate >() { return SbkPySide2_QtSqlTypes[SBK_QSQLRESULT_VIRTUALHOOKOPERATION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSqlResult >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtSqlTypes[SBK_QSQLRESULT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSqlRecord >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtSqlTypes[SBK_QSQLRECORD_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSqlIndex >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtSqlTypes[SBK_QSQLINDEX_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSqlField::RequiredStatus >() { return SbkPySide2_QtSqlTypes[SBK_QSQLFIELD_REQUIREDSTATUS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSqlField >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtSqlTypes[SBK_QSQLFIELD_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSqlError::ErrorType >() { return SbkPySide2_QtSqlTypes[SBK_QSQLERROR_ERRORTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSqlError >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtSqlTypes[SBK_QSQLERROR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSqlDatabase >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtSqlTypes[SBK_QSQLDATABASE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSqlQuery::BatchExecutionMode >() { return SbkPySide2_QtSqlTypes[SBK_QSQLQUERY_BATCHEXECUTIONMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSqlQuery >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtSqlTypes[SBK_QSQLQUERY_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSqlDriverCreatorBase >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtSqlTypes[SBK_QSQLDRIVERCREATORBASE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSqlDriver::DriverFeature >() { return SbkPySide2_QtSqlTypes[SBK_QSQLDRIVER_DRIVERFEATURE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSqlDriver::StatementType >() { return SbkPySide2_QtSqlTypes[SBK_QSQLDRIVER_STATEMENTTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSqlDriver::IdentifierType >() { return SbkPySide2_QtSqlTypes[SBK_QSQLDRIVER_IDENTIFIERTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSqlDriver::NotificationSource >() { return SbkPySide2_QtSqlTypes[SBK_QSQLDRIVER_NOTIFICATIONSOURCE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSqlDriver::DbmsType >() { return SbkPySide2_QtSqlTypes[SBK_QSQLDRIVER_DBMSTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSqlDriver >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtSqlTypes[SBK_QSQLDRIVER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSqlRelationalDelegate >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtSqlTypes[SBK_QSQLRELATIONALDELEGATE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSqlQueryModel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtSqlTypes[SBK_QSQLQUERYMODEL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSqlTableModel::EditStrategy >() { return SbkPySide2_QtSqlTypes[SBK_QSQLTABLEMODEL_EDITSTRATEGY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSqlTableModel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtSqlTypes[SBK_QSQLTABLEMODEL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSqlRelationalTableModel::JoinMode >() { return SbkPySide2_QtSqlTypes[SBK_QSQLRELATIONALTABLEMODEL_JOINMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSqlRelationalTableModel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtSqlTypes[SBK_QSQLRELATIONALTABLEMODEL_IDX]); }

} // namespace Shiboken

#endif // SBK_QTSQL_PYTHON_H

