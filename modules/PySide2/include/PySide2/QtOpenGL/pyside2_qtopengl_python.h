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


#ifndef SBK_QTOPENGL_PYTHON_H
#define SBK_QTOPENGL_PYTHON_H

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
#include <qglshaderprogram.h>
#include <qglcolormap.h>
#include <qglframebufferobject.h>
#include <qgl.h>
#include <qglbuffer.h>
#include <qglpixelbuffer.h>
// Conversion Includes - Primitive Types
#include <wtypes.h>
#include <QString>
#include <signalmanager.h>
#include <QStringList>
#include <qabstractitemmodel.h>

// Conversion Includes - Container Types
#include <QStack>
#include <QQueue>
#include <QVector>
#include <QLinkedList>
#include <QMap>
#include <QSet>
#include <QList>
#include <pysideqflags.h>
#include <QPair>
#include <QMultiMap>

// Type indices
#define SBK_QGL_IDX                                                  4
#define SBK_QGL_FORMATOPTION_IDX                                     5
#define SBK_QFLAGS_QGL_FORMATOPTION__IDX                             0
#define SBK_QGLFRAMEBUFFEROBJECTFORMAT_IDX                           18
#define SBK_QGLBUFFER_IDX                                            6
#define SBK_QGLBUFFER_TYPE_IDX                                       8
#define SBK_QGLBUFFER_USAGEPATTERN_IDX                               9
#define SBK_QGLBUFFER_ACCESS_IDX                                     7
#define SBK_QGLCONTEXT_IDX                                           11
#define SBK_QGLCONTEXT_BINDOPTION_IDX                                12
#define SBK_QFLAGS_QGLCONTEXT_BINDOPTION__IDX                        1
#define SBK_QGLFORMAT_IDX                                            13
#define SBK_QGLFORMAT_OPENGLCONTEXTPROFILE_IDX                       14
#define SBK_QGLFORMAT_OPENGLVERSIONFLAG_IDX                          15
#define SBK_QFLAGS_QGLFORMAT_OPENGLVERSIONFLAG__IDX                  2
#define SBK_QGLCOLORMAP_IDX                                          10
#define SBK_QGLPIXELBUFFER_IDX                                       19
#define SBK_QGLFRAMEBUFFEROBJECT_IDX                                 16
#define SBK_QGLFRAMEBUFFEROBJECT_ATTACHMENT_IDX                      17
#define SBK_QGLSHADER_IDX                                            20
#define SBK_QGLSHADER_SHADERTYPEBIT_IDX                              21
#define SBK_QFLAGS_QGLSHADER_SHADERTYPEBIT__IDX                      3
#define SBK_QGLSHADERPROGRAM_IDX                                     22
#define SBK_QGLWIDGET_IDX                                            23
#define SBK_QtOpenGL_IDX_COUNT                                       24

// This variable stores all Python types exported by this module.
extern PyTypeObject** SbkPySide2_QtOpenGLTypes;

// This variable stores all type converters exported by this module.
extern SbkConverter** SbkPySide2_QtOpenGLTypeConverters;

// Converter indices
#define SBK_QTOPENGL_QLIST_QOBJECTPTR_IDX                            0 // const QList<QObject * > &
#define SBK_QTOPENGL_QLIST_QBYTEARRAY_IDX                            1 // QList<QByteArray >
#define SBK_QTOPENGL_QLIST_QGLSHADERPTR_IDX                          2 // QList<QGLShader * >
#define SBK_QTOPENGL_QLIST_QACTIONPTR_IDX                            3 // QList<QAction * >
#define SBK_QTOPENGL_QLIST_QVARIANT_IDX                              4 // QList<QVariant >
#define SBK_QTOPENGL_QLIST_QSTRING_IDX                               5 // QList<QString >
#define SBK_QTOPENGL_QMAP_QSTRING_QVARIANT_IDX                       6 // QMap<QString, QVariant >
#define SBK_QtOpenGL_CONVERTERS_IDX_COUNT                            7

// Macros for type check

namespace Shiboken
{

// PyType functions, to get the PyObjectType for a type T
template<> inline PyTypeObject* SbkType< ::QGL::FormatOption >() { return SbkPySide2_QtOpenGLTypes[SBK_QGL_FORMATOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QGL::FormatOption> >() { return SbkPySide2_QtOpenGLTypes[SBK_QFLAGS_QGL_FORMATOPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QGLFramebufferObjectFormat >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtOpenGLTypes[SBK_QGLFRAMEBUFFEROBJECTFORMAT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGLBuffer::Type >() { return SbkPySide2_QtOpenGLTypes[SBK_QGLBUFFER_TYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QGLBuffer::UsagePattern >() { return SbkPySide2_QtOpenGLTypes[SBK_QGLBUFFER_USAGEPATTERN_IDX]; }
template<> inline PyTypeObject* SbkType< ::QGLBuffer::Access >() { return SbkPySide2_QtOpenGLTypes[SBK_QGLBUFFER_ACCESS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QGLBuffer >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtOpenGLTypes[SBK_QGLBUFFER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGLContext::BindOption >() { return SbkPySide2_QtOpenGLTypes[SBK_QGLCONTEXT_BINDOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QGLContext::BindOption> >() { return SbkPySide2_QtOpenGLTypes[SBK_QFLAGS_QGLCONTEXT_BINDOPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QGLContext >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtOpenGLTypes[SBK_QGLCONTEXT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGLFormat::OpenGLContextProfile >() { return SbkPySide2_QtOpenGLTypes[SBK_QGLFORMAT_OPENGLCONTEXTPROFILE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QGLFormat::OpenGLVersionFlag >() { return SbkPySide2_QtOpenGLTypes[SBK_QGLFORMAT_OPENGLVERSIONFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QGLFormat::OpenGLVersionFlag> >() { return SbkPySide2_QtOpenGLTypes[SBK_QFLAGS_QGLFORMAT_OPENGLVERSIONFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QGLFormat >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtOpenGLTypes[SBK_QGLFORMAT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGLColormap >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtOpenGLTypes[SBK_QGLCOLORMAP_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGLPixelBuffer >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtOpenGLTypes[SBK_QGLPIXELBUFFER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGLFramebufferObject::Attachment >() { return SbkPySide2_QtOpenGLTypes[SBK_QGLFRAMEBUFFEROBJECT_ATTACHMENT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QGLFramebufferObject >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtOpenGLTypes[SBK_QGLFRAMEBUFFEROBJECT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGLShader::ShaderTypeBit >() { return SbkPySide2_QtOpenGLTypes[SBK_QGLSHADER_SHADERTYPEBIT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QGLShader::ShaderTypeBit> >() { return SbkPySide2_QtOpenGLTypes[SBK_QFLAGS_QGLSHADER_SHADERTYPEBIT__IDX]; }
template<> inline PyTypeObject* SbkType< ::QGLShader >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtOpenGLTypes[SBK_QGLSHADER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGLShaderProgram >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtOpenGLTypes[SBK_QGLSHADERPROGRAM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QGLWidget >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtOpenGLTypes[SBK_QGLWIDGET_IDX]); }

} // namespace Shiboken

#endif // SBK_QTOPENGL_PYTHON_H

