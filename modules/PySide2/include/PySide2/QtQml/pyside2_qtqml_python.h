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


#ifndef SBK_QTQML_PYTHON_H
#define SBK_QTQML_PYTHON_H

#include <sbkpython.h>
#include <sbkconverter.h>
#include <sbkenum.h>
#include <basewrapper.h>
#include <bindingmanager.h>
#include <memory>

#include <pysidesignal.h>
// Module Includes
#include <pyside2_qtcore_python.h>
#include <pyside2_qtnetwork_python.h>
#include <pyside2_qtgui_python.h>

// Binded library includes
#include <qjsvalue.h>
#include <qqmlengine.h>
#include <qqmlparserstatus.h>
#include <qqmlextensionplugin.h>
#include <qqmlpropertyvaluesource.h>
#include <qqmlextensioninterface.h>
#include <qjsvalueiterator.h>
#include <qqmlcontext.h>
#include <qqmlapplicationengine.h>
#include <qqmlfile.h>
#include <qqmllist.h>
#include <qqmlincubator.h>
#include <qqmlpropertymap.h>
#include <qqmlabstracturlinterceptor.h>
#include <qqmlproperty.h>
#include <qqmlcomponent.h>
#include <qqmlnetworkaccessmanagerfactory.h>
#include <qqmlscriptstring.h>
#include <qqmlfileselector.h>
#include <qqmlerror.h>
#include <qqmldebug.h>
#include <qqmlexpression.h>
#include <qjsengine.h>
// Conversion Includes - Primitive Types
#include <qabstractitemmodel.h>
#include <wtypes.h>
#include <QString>
#include <QStringList>
#include "pysideqmlregistertype.h"
#include <signalmanager.h>

// Conversion Includes - Container Types
#include <QList>
#include <pysideqflags.h>
#include <QVector>
#include <QMap>
#include <QSet>
#include <QStack>
#include <QPair>
#include <QLinkedList>
#include <QQueue>
#include <QMultiMap>

// Type indices
#define SBK_QQMLPROPERTY_IDX                                         36
#define SBK_QQMLPROPERTY_PROPERTYTYPECATEGORY_IDX                    37
#define SBK_QQMLPROPERTY_TYPE_IDX                                    38
#define SBK_QQMLNETWORKACCESSMANAGERFACTORY_IDX                      34
#define SBK_QQMLINCUBATIONCONTROLLER_IDX                             29
#define SBK_QQMLINCUBATOR_IDX                                        30
#define SBK_QQMLINCUBATOR_INCUBATIONMODE_IDX                         31
#define SBK_QQMLINCUBATOR_STATUS_IDX                                 32
#define SBK_QQMLFILE_IDX                                             23
#define SBK_QQMLFILE_STATUS_IDX                                      24
#define SBK_QQMLTYPESEXTENSIONINTERFACE_IDX                          42
#define SBK_QQMLEXTENSIONINTERFACE_IDX                               21
#define SBK_QQMLSCRIPTSTRING_IDX                                     41
#define SBK_QQMLIMAGEPROVIDERBASE_IDX                                26
#define SBK_QQMLIMAGEPROVIDERBASE_IMAGETYPE_IDX                      28
#define SBK_QQMLIMAGEPROVIDERBASE_FLAG_IDX                           27
#define SBK_QFLAGS_QQMLIMAGEPROVIDERBASE_FLAG__IDX                   1
#define SBK_QQMLERROR_IDX                                            19
#define SBK_QQMLABSTRACTURLINTERCEPTOR_IDX                           8
#define SBK_QQMLABSTRACTURLINTERCEPTOR_DATATYPE_IDX                  9
#define SBK_QQMLLISTREFERENCE_IDX                                    33
#define SBK_QQMLPROPERTYVALUESOURCE_IDX                              40
#define SBK_QQMLPARSERSTATUS_IDX                                     35
#define SBK_QJSVALUEITERATOR_IDX                                     6
#define SBK_QJSVALUE_IDX                                             4
#define SBK_QJSVALUE_SPECIALVALUE_IDX                                5
#define SBK_QQMLDEBUGGINGENABLER_IDX                                 15
#define SBK_QQMLDEBUGGINGENABLER_STARTMODE_IDX                       16
#define SBK_QJSENGINE_IDX                                            2
#define SBK_QJSENGINE_EXTENSION_IDX                                  3
#define SBK_QFLAGS_QJSENGINE_EXTENSION__IDX                          0
#define SBK_QQMLENGINE_IDX                                           17
#define SBK_QQMLENGINE_OBJECTOWNERSHIP_IDX                           18
#define SBK_QQMLCOMPONENT_IDX                                        11
#define SBK_QQMLCOMPONENT_COMPILATIONMODE_IDX                        12
#define SBK_QQMLCOMPONENT_STATUS_IDX                                 13
#define SBK_QQMLEXTENSIONPLUGIN_IDX                                  22
#define SBK_QQMLFILESELECTOR_IDX                                     25
#define SBK_QQMLCONTEXT_IDX                                          14
#define SBK_QQMLEXPRESSION_IDX                                       20
#define SBK_QQMLPROPERTYMAP_IDX                                      39
#define SBK_QQMLAPPLICATIONENGINE_IDX                                10
#define SBK_QML_HAS_ATTACHED_PROPERTIES_IDX                          7
#define SBK_QtQml_IDX_COUNT                                          43

// This variable stores all Python types exported by this module.
extern PyTypeObject** SbkPySide2_QtQmlTypes;

// This variable stores all type converters exported by this module.
extern SbkConverter** SbkPySide2_QtQmlTypeConverters;

// Converter indices
#define SBK_QTQML_QLIST_QQMLERROR_IDX                                0 // QList<QQmlError >
#define SBK_QTQML_QLIST_QJSVALUE_IDX                                 1 // const QList<QJSValue > &
#define SBK_QTQML_QLIST_QOBJECTPTR_IDX                               2 // const QList<QObject * > &
#define SBK_QTQML_QLIST_QBYTEARRAY_IDX                               3 // QList<QByteArray >
#define SBK_QTQML_QLIST_QVARIANT_IDX                                 4 // QList<QVariant >
#define SBK_QTQML_QLIST_QSTRING_IDX                                  5 // QList<QString >
#define SBK_QTQML_QMAP_QSTRING_QVARIANT_IDX                          6 // QMap<QString, QVariant >
#define SBK_QtQml_CONVERTERS_IDX_COUNT                               7

// Macros for type check

namespace Shiboken
{

// PyType functions, to get the PyObjectType for a type T
template<> inline PyTypeObject* SbkType< ::QQmlProperty::PropertyTypeCategory >() { return SbkPySide2_QtQmlTypes[SBK_QQMLPROPERTY_PROPERTYTYPECATEGORY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQmlProperty::Type >() { return SbkPySide2_QtQmlTypes[SBK_QQMLPROPERTY_TYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQmlProperty >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLPROPERTY_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlNetworkAccessManagerFactory >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLNETWORKACCESSMANAGERFACTORY_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlIncubationController >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLINCUBATIONCONTROLLER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlIncubator::IncubationMode >() { return SbkPySide2_QtQmlTypes[SBK_QQMLINCUBATOR_INCUBATIONMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQmlIncubator::Status >() { return SbkPySide2_QtQmlTypes[SBK_QQMLINCUBATOR_STATUS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQmlIncubator >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLINCUBATOR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlFile::Status >() { return SbkPySide2_QtQmlTypes[SBK_QQMLFILE_STATUS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQmlFile >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLFILE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlTypesExtensionInterface >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLTYPESEXTENSIONINTERFACE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlExtensionInterface >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLEXTENSIONINTERFACE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlScriptString >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLSCRIPTSTRING_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlImageProviderBase::ImageType >() { return SbkPySide2_QtQmlTypes[SBK_QQMLIMAGEPROVIDERBASE_IMAGETYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQmlImageProviderBase::Flag >() { return SbkPySide2_QtQmlTypes[SBK_QQMLIMAGEPROVIDERBASE_FLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QQmlImageProviderBase::Flag> >() { return SbkPySide2_QtQmlTypes[SBK_QFLAGS_QQMLIMAGEPROVIDERBASE_FLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QQmlImageProviderBase >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLIMAGEPROVIDERBASE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlError >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLERROR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlAbstractUrlInterceptor::DataType >() { return SbkPySide2_QtQmlTypes[SBK_QQMLABSTRACTURLINTERCEPTOR_DATATYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQmlAbstractUrlInterceptor >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLABSTRACTURLINTERCEPTOR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlListReference >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLLISTREFERENCE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlPropertyValueSource >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLPROPERTYVALUESOURCE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlParserStatus >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLPARSERSTATUS_IDX]); }
template<> inline PyTypeObject* SbkType< ::QJSValueIterator >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QJSVALUEITERATOR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QJSValue::SpecialValue >() { return SbkPySide2_QtQmlTypes[SBK_QJSVALUE_SPECIALVALUE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QJSValue >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QJSVALUE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlDebuggingEnabler::StartMode >() { return SbkPySide2_QtQmlTypes[SBK_QQMLDEBUGGINGENABLER_STARTMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQmlDebuggingEnabler >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLDEBUGGINGENABLER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QJSEngine::Extension >() { return SbkPySide2_QtQmlTypes[SBK_QJSENGINE_EXTENSION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QJSEngine::Extension> >() { return SbkPySide2_QtQmlTypes[SBK_QFLAGS_QJSENGINE_EXTENSION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QJSEngine >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QJSENGINE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlEngine::ObjectOwnership >() { return SbkPySide2_QtQmlTypes[SBK_QQMLENGINE_OBJECTOWNERSHIP_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQmlEngine >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLENGINE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlComponent::CompilationMode >() { return SbkPySide2_QtQmlTypes[SBK_QQMLCOMPONENT_COMPILATIONMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQmlComponent::Status >() { return SbkPySide2_QtQmlTypes[SBK_QQMLCOMPONENT_STATUS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQmlComponent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLCOMPONENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlExtensionPlugin >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLEXTENSIONPLUGIN_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlFileSelector >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLFILESELECTOR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlContext >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLCONTEXT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlExpression >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLEXPRESSION_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlPropertyMap >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLPROPERTYMAP_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQmlApplicationEngine >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQmlTypes[SBK_QQMLAPPLICATIONENGINE_IDX]); }

} // namespace Shiboken

#endif // SBK_QTQML_PYTHON_H

