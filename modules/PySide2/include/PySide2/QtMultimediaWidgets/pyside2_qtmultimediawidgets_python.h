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


#ifndef SBK_QTMULTIMEDIAWIDGETS_PYTHON_H
#define SBK_QTMULTIMEDIAWIDGETS_PYTHON_H

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
#include <pyside2_qtmultimedia_python.h>
#include <pyside2_qtnetwork_python.h>
#include <pyside2_qtwidgets_python.h>

// Binded library includes
#include <qvideowidgetcontrol.h>
#include <qcameraviewfinder.h>
#include <qgraphicsvideoitem.h>
#include <qvideowidget.h>
// Conversion Includes - Primitive Types
#include <QStringList>
#include <signalmanager.h>
#include <QString>
#include <qabstractitemmodel.h>
#include <wtypes.h>

// Conversion Includes - Container Types
#include <pysideqflags.h>
#include <QStack>
#include <QQueue>
#include <QMultiMap>
#include <QVector>
#include <QLinkedList>
#include <QSet>
#include <QList>
#include <QPair>
#include <QMap>

// Type indices
#define SBK_QVIDEOWIDGETCONTROL_IDX                                  3
#define SBK_QVIDEOWIDGET_IDX                                         2
#define SBK_QCAMERAVIEWFINDER_IDX                                    0
#define SBK_QGRAPHICSVIDEOITEM_IDX                                   1
#define SBK_QtMultimediaWidgets_IDX_COUNT                            4

// This variable stores all Python types exported by this module.
extern PyTypeObject** SbkPySide2_QtMultimediaWidgetsTypes;

// This variable stores all type converters exported by this module.
extern SbkConverter** SbkPySide2_QtMultimediaWidgetsTypeConverters;

// Converter indices
#define SBK_QTMULTIMEDIAWIDGETS_QLIST_QOBJECTPTR_IDX                 0 // const QList<QObject * > &
#define SBK_QTMULTIMEDIAWIDGETS_QLIST_QBYTEARRAY_IDX                 1 // QList<QByteArray >
#define SBK_QTMULTIMEDIAWIDGETS_QLIST_QACTIONPTR_IDX                 2 // QList<QAction * >
#define SBK_QTMULTIMEDIAWIDGETS_QLIST_QGRAPHICSITEMPTR_IDX           3 // QList<QGraphicsItem * >
#define SBK_QTMULTIMEDIAWIDGETS_QLIST_QGRAPHICSTRANSFORMPTR_IDX      4 // const QList<QGraphicsTransform * > &
#define SBK_QTMULTIMEDIAWIDGETS_QLIST_QVARIANT_IDX                   5 // QList<QVariant >
#define SBK_QTMULTIMEDIAWIDGETS_QLIST_QSTRING_IDX                    6 // QList<QString >
#define SBK_QTMULTIMEDIAWIDGETS_QMAP_QSTRING_QVARIANT_IDX            7 // QMap<QString, QVariant >
#define SBK_QtMultimediaWidgets_CONVERTERS_IDX_COUNT                 8

// Macros for type check

namespace Shiboken
{

// PyType functions, to get the PyObjectType for a type T
template<> inline PyTypeObject* SbkType< ::QVideoWidgetControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaWidgetsTypes[SBK_QVIDEOWIDGETCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QVideoWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaWidgetsTypes[SBK_QVIDEOWIDGET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCameraViewfinder >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaWidgetsTypes[SBK_QCAMERAVIEWFINDER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGraphicsVideoItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaWidgetsTypes[SBK_QGRAPHICSVIDEOITEM_IDX]); }

} // namespace Shiboken

#endif // SBK_QTMULTIMEDIAWIDGETS_PYTHON_H

