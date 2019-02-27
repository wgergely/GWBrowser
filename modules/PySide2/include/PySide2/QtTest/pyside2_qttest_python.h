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


#ifndef SBK_QTTEST_PYTHON_H
#define SBK_QTTEST_PYTHON_H

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

// Binded library includes
#include <qtestmouse.h>
#include <qtestkeyboard.h>
#include <qbenchmarkmetric.h>
#include <qtest_global.h>
#include <pysideqtesttouch.h>
// Conversion Includes - Primitive Types
#include <QStringList>
#include <qabstractitemmodel.h>
#include <signalmanager.h>
#include <wtypes.h>
#include <QString>

// Conversion Includes - Container Types
#include <QLinkedList>
#include <QStack>
#include <QQueue>
#include <QList>
#include <QPair>
#include <pysideqflags.h>
#include <QMap>
#include <QVector>
#include <QSet>
#include <QMultiMap>

// Type indices
#define SBK_QTEST_IDX                                                0
#define SBK_QTEST_TESTFAILMODE_IDX                                   5
#define SBK_QTEST_QBENCHMARKMETRIC_IDX                               4
#define SBK_QTEST_KEYACTION_IDX                                      1
#define SBK_QTEST_MOUSEACTION_IDX                                    2
#define SBK_QTEST_PYSIDEQTOUCHEVENTSEQUENCE_IDX                      3
#define SBK_QtTest_IDX_COUNT                                         6

// This variable stores all Python types exported by this module.
extern PyTypeObject** SbkPySide2_QtTestTypes;

// This variable stores all type converters exported by this module.
extern SbkConverter** SbkPySide2_QtTestTypeConverters;

// Converter indices
#define SBK_QTTEST_QLIST_QVARIANT_IDX                                0 // QList<QVariant >
#define SBK_QTTEST_QLIST_QSTRING_IDX                                 1 // QList<QString >
#define SBK_QTTEST_QMAP_QSTRING_QVARIANT_IDX                         2 // QMap<QString, QVariant >
#define SBK_QtTest_CONVERTERS_IDX_COUNT                              3

// Macros for type check

namespace Shiboken
{

// PyType functions, to get the PyObjectType for a type T
template<> inline PyTypeObject* SbkType< ::QTest::TestFailMode >() { return SbkPySide2_QtTestTypes[SBK_QTEST_TESTFAILMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTest::QBenchmarkMetric >() { return SbkPySide2_QtTestTypes[SBK_QTEST_QBENCHMARKMETRIC_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTest::KeyAction >() { return SbkPySide2_QtTestTypes[SBK_QTEST_KEYACTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTest::MouseAction >() { return SbkPySide2_QtTestTypes[SBK_QTEST_MOUSEACTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QTest::PySideQTouchEventSequence >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtTestTypes[SBK_QTEST_PYSIDEQTOUCHEVENTSEQUENCE_IDX]); }

} // namespace Shiboken

#endif // SBK_QTTEST_PYTHON_H

