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


#ifndef SBK_QTCONCURRENT_PYTHON_H
#define SBK_QTCONCURRENT_PYTHON_H

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
#include <qtconcurrentreducekernel.h>
#include <qtconcurrentexception.h>
// Conversion Includes - Primitive Types
#include <QString>
#include <signalmanager.h>
#include <QStringList>
#include <qabstractitemmodel.h>
#include <wtypes.h>

// Conversion Includes - Container Types
#include <pysideqflags.h>
#include <QList>
#include <QMap>
#include <QPair>
#include <QMultiMap>
#include <QSet>
#include <QStack>
#include <QVector>
#include <QLinkedList>
#include <QQueue>

// Type indices
#define SBK_QTCONCURRENT_IDX                                         1
#define SBK_QTCONCURRENT_REDUCEOPTION_IDX                            2
#define SBK_QFLAGS_QTCONCURRENT_REDUCEOPTION__IDX                    0
#define SBK_QtConcurrent_IDX_COUNT                                   3

// This variable stores all Python types exported by this module.
extern PyTypeObject** SbkPySide2_QtConcurrentTypes;

// This variable stores all type converters exported by this module.
extern SbkConverter** SbkPySide2_QtConcurrentTypeConverters;

// Converter indices
#define SBK_QTCONCURRENT_QLIST_QVARIANT_IDX                          0 // QList<QVariant >
#define SBK_QTCONCURRENT_QLIST_QSTRING_IDX                           1 // QList<QString >
#define SBK_QTCONCURRENT_QMAP_QSTRING_QVARIANT_IDX                   2 // QMap<QString, QVariant >
#define SBK_QtConcurrent_CONVERTERS_IDX_COUNT                        3

// Macros for type check

namespace Shiboken
{

// PyType functions, to get the PyObjectType for a type T
template<> inline PyTypeObject* SbkType< ::QtConcurrent::ReduceOption >() { return SbkPySide2_QtConcurrentTypes[SBK_QTCONCURRENT_REDUCEOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QtConcurrent::ReduceOption> >() { return SbkPySide2_QtConcurrentTypes[SBK_QFLAGS_QTCONCURRENT_REDUCEOPTION__IDX]; }

} // namespace Shiboken

#endif // SBK_QTCONCURRENT_PYTHON_H

