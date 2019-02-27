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


#ifndef SBK_QTWEBCHANNEL_PYTHON_H
#define SBK_QTWEBCHANNEL_PYTHON_H

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
#include <qwebchannel.h>
#include <qwebchannelabstracttransport.h>
// Conversion Includes - Primitive Types
#include <QString>
#include <QStringList>
#include <signalmanager.h>
#include <wtypes.h>
#include <qabstractitemmodel.h>

// Conversion Includes - Container Types
#include <QList>
#include <pysideqflags.h>
#include <QSet>
#include <QQueue>
#include <QVector>
#include <QStack>
#include <QMap>
#include <QMultiMap>
#include <QLinkedList>
#include <QPair>

// Type indices
#define SBK_QWEBCHANNEL_IDX                                          0
#define SBK_QWEBCHANNELABSTRACTTRANSPORT_IDX                         1
#define SBK_QtWebChannel_IDX_COUNT                                   2

// This variable stores all Python types exported by this module.
extern PyTypeObject** SbkPySide2_QtWebChannelTypes;

// This variable stores all type converters exported by this module.
extern SbkConverter** SbkPySide2_QtWebChannelTypeConverters;

// Converter indices
#define SBK_QTWEBCHANNEL_QLIST_QOBJECTPTR_IDX                        0 // const QList<QObject * > &
#define SBK_QTWEBCHANNEL_QLIST_QBYTEARRAY_IDX                        1 // QList<QByteArray >
#define SBK_QTWEBCHANNEL_QHASH_QSTRING_QOBJECTPTR_IDX                2 // const QHash<QString, QObject * > &
#define SBK_QTWEBCHANNEL_QLIST_QVARIANT_IDX                          3 // QList<QVariant >
#define SBK_QTWEBCHANNEL_QLIST_QSTRING_IDX                           4 // QList<QString >
#define SBK_QTWEBCHANNEL_QMAP_QSTRING_QVARIANT_IDX                   5 // QMap<QString, QVariant >
#define SBK_QtWebChannel_CONVERTERS_IDX_COUNT                        6

// Macros for type check

namespace Shiboken
{

// PyType functions, to get the PyObjectType for a type T
template<> inline PyTypeObject* SbkType< ::QWebChannel >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWebChannelTypes[SBK_QWEBCHANNEL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWebChannelAbstractTransport >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWebChannelTypes[SBK_QWEBCHANNELABSTRACTTRANSPORT_IDX]); }

} // namespace Shiboken

#endif // SBK_QTWEBCHANNEL_PYTHON_H

