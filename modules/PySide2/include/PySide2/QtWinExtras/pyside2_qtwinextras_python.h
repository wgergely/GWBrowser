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


#ifndef SBK_QTWINEXTRAS_PYTHON_H
#define SBK_QTWINEXTRAS_PYTHON_H

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

// Binded library includes
#include <qwinthumbnailtoolbar.h>
#include <qwinjumplist.h>
#include <qwintaskbarbutton.h>
#include <qwinjumplistitem.h>
#include <qwinevent.h>
#include <qwinjumplistcategory.h>
#include <qwintaskbarprogress.h>
#include <qwinthumbnailtoolbutton.h>
// Conversion Includes - Primitive Types
#include <QString>
#include <qabstractitemmodel.h>
#include <QStringList>
#include <wtypes.h>
#include <signalmanager.h>

// Conversion Includes - Container Types
#include <QList>
#include <QStack>
#include <QQueue>
#include <QMap>
#include <QMultiMap>
#include <QSet>
#include <QPair>
#include <pysideqflags.h>
#include <QLinkedList>
#include <QVector>

// Type indices
#define SBK_QWINJUMPLISTITEM_IDX                                     6
#define SBK_QWINJUMPLISTITEM_TYPE_IDX                                7
#define SBK_QWINJUMPLISTCATEGORY_IDX                                 4
#define SBK_QWINJUMPLISTCATEGORY_TYPE_IDX                            5
#define SBK_QWINEVENT_IDX                                            2
#define SBK_QWINCOMPOSITIONCHANGEEVENT_IDX                           1
#define SBK_QWINCOLORIZATIONCHANGEEVENT_IDX                          0
#define SBK_QWINJUMPLIST_IDX                                         3
#define SBK_QWINTHUMBNAILTOOLBUTTON_IDX                              11
#define SBK_QWINTASKBARBUTTON_IDX                                    8
#define SBK_QWINTHUMBNAILTOOLBAR_IDX                                 10
#define SBK_QWINTASKBARPROGRESS_IDX                                  9
#define SBK_QtWinExtras_IDX_COUNT                                    12

// This variable stores all Python types exported by this module.
extern PyTypeObject** SbkPySide2_QtWinExtrasTypes;

// This variable stores all type converters exported by this module.
extern SbkConverter** SbkPySide2_QtWinExtrasTypeConverters;

// Converter indices
#define SBK_QTWINEXTRAS_QLIST_QWINJUMPLISTITEMPTR_IDX                0 // QList<QWinJumpListItem * >
#define SBK_QTWINEXTRAS_QLIST_QWINJUMPLISTCATEGORYPTR_IDX            1 // QList<QWinJumpListCategory * >
#define SBK_QTWINEXTRAS_QLIST_QOBJECTPTR_IDX                         2 // const QList<QObject * > &
#define SBK_QTWINEXTRAS_QLIST_QBYTEARRAY_IDX                         3 // QList<QByteArray >
#define SBK_QTWINEXTRAS_QLIST_QWINTHUMBNAILTOOLBUTTONPTR_IDX         4 // QList<QWinThumbnailToolButton * >
#define SBK_QTWINEXTRAS_QLIST_QVARIANT_IDX                           5 // QList<QVariant >
#define SBK_QTWINEXTRAS_QLIST_QSTRING_IDX                            6 // QList<QString >
#define SBK_QTWINEXTRAS_QMAP_QSTRING_QVARIANT_IDX                    7 // QMap<QString, QVariant >
#define SBK_QtWinExtras_CONVERTERS_IDX_COUNT                         8

// Macros for type check

namespace Shiboken
{

// PyType functions, to get the PyObjectType for a type T
template<> inline PyTypeObject* SbkType< ::QWinJumpListItem::Type >() { return SbkPySide2_QtWinExtrasTypes[SBK_QWINJUMPLISTITEM_TYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWinJumpListItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWinExtrasTypes[SBK_QWINJUMPLISTITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWinJumpListCategory::Type >() { return SbkPySide2_QtWinExtrasTypes[SBK_QWINJUMPLISTCATEGORY_TYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QWinJumpListCategory >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWinExtrasTypes[SBK_QWINJUMPLISTCATEGORY_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWinEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWinExtrasTypes[SBK_QWINEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWinCompositionChangeEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWinExtrasTypes[SBK_QWINCOMPOSITIONCHANGEEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWinColorizationChangeEvent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWinExtrasTypes[SBK_QWINCOLORIZATIONCHANGEEVENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWinJumpList >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWinExtrasTypes[SBK_QWINJUMPLIST_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWinThumbnailToolButton >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWinExtrasTypes[SBK_QWINTHUMBNAILTOOLBUTTON_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWinTaskbarButton >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWinExtrasTypes[SBK_QWINTASKBARBUTTON_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWinThumbnailToolBar >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWinExtrasTypes[SBK_QWINTHUMBNAILTOOLBAR_IDX]); }
template<> inline PyTypeObject* SbkType< ::QWinTaskbarProgress >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtWinExtrasTypes[SBK_QWINTASKBARPROGRESS_IDX]); }

} // namespace Shiboken

#endif // SBK_QTWINEXTRAS_PYTHON_H

