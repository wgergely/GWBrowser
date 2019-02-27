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


#ifndef SBK_QTQUICK_PYTHON_H
#define SBK_QTQUICK_PYTHON_H

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
#include <pyside2_qtqml_python.h>

// Binded library includes
#include <qsggeometry.h>
#include <qquickpainteditem.h>
#include <qquickimageprovider.h>
#include <qsgsimplerectnode.h>
#include <qsgmaterial.h>
#include <qsgabstractrenderer.h>
#include <qquickwindow.h>
#include <qsgnode.h>
#include <qquickrendercontrol.h>
#include <qquickview.h>
#include <qsgtexture.h>
#include <qsgsimpletexturenode.h>
#include <qquickitem.h>
#include <qquickframebufferobject.h>
#include <qquicktextdocument.h>
#include <qquickitemgrabresult.h>
#include <qsharedpointer.h>
#include <qsgengine.h>
#include <qsgtextureprovider.h>
// Conversion Includes - Primitive Types
#include <QString>
#include "pysideqmlregistertype.h"
#include <QStringList>
#include <qabstractitemmodel.h>
#include <signalmanager.h>
#include <wtypes.h>

// Conversion Includes - Container Types
#include <QPair>
#include <QVector>
#include <QQueue>
#include <pysideqflags.h>
#include <QMap>
#include <QList>
#include <QStack>
#include <QMultiMap>
#include <QLinkedList>
#include <QSet>

// Type indices
#define SBK_QSGMATERIALTYPE_IDX                                      48
#define SBK_QSGNODE_IDX                                              49
#define SBK_QSGNODE_NODETYPE_IDX                                     52
#define SBK_QSGNODE_FLAG_IDX                                         51
#define SBK_QFLAGS_QSGNODE_FLAG__IDX                                 6
#define SBK_QSGNODE_DIRTYSTATEBIT_IDX                                50
#define SBK_QFLAGS_QSGNODE_DIRTYSTATEBIT__IDX                        5
#define SBK_QSGTRANSFORMNODE_IDX                                     61
#define SBK_QSGOPACITYNODE_IDX                                       53
#define SBK_QSGBASICGEOMETRYNODE_IDX                                 35
#define SBK_QSGGEOMETRYNODE_IDX                                      47
#define SBK_QSGSIMPLETEXTURENODE_IDX                                 55
#define SBK_QSGSIMPLETEXTURENODE_TEXTURECOORDINATESTRANSFORMFLAG_IDX 56
#define SBK_QFLAGS_QSGSIMPLETEXTURENODE_TEXTURECOORDINATESTRANSFORMFLAG__IDX 7
#define SBK_QSGSIMPLERECTNODE_IDX                                    54
#define SBK_QSGCLIPNODE_IDX                                          36
#define SBK_QSGGEOMETRY_IDX                                          40
#define SBK_QSGGEOMETRY_DATAPATTERN_IDX                              44
#define SBK_QSGGEOMETRY_COLOREDPOINT2D_IDX                           43
#define SBK_QSGGEOMETRY_TEXTUREDPOINT2D_IDX                          46
#define SBK_QSGGEOMETRY_POINT2D_IDX                                  45
#define SBK_QSGGEOMETRY_ATTRIBUTESET_IDX                             42
#define SBK_QSGGEOMETRY_ATTRIBUTE_IDX                                41
#define SBK_QQUICKIMAGEPROVIDER_IDX                                  11
#define SBK_QQUICKASYNCIMAGEPROVIDER_IDX                             8
#define SBK_QQUICKITEM_IDX                                           13
#define SBK_QQUICKITEM_FLAG_IDX                                      14
#define SBK_QFLAGS_QQUICKITEM_FLAG__IDX                              0
#define SBK_QQUICKITEM_ITEMCHANGE_IDX                                15
#define SBK_QQUICKITEM_TRANSFORMORIGIN_IDX                           16
#define SBK_QQUICKFRAMEBUFFEROBJECT_IDX                              9
#define SBK_QQUICKFRAMEBUFFEROBJECT_RENDERER_IDX                     10
#define SBK_QQUICKITEM_UPDATEPAINTNODEDATA_IDX                       17
#define SBK_QQUICKPAINTEDITEM_IDX                                    19
#define SBK_QQUICKPAINTEDITEM_RENDERTARGET_IDX                       21
#define SBK_QQUICKPAINTEDITEM_PERFORMANCEHINT_IDX                    20
#define SBK_QFLAGS_QQUICKPAINTEDITEM_PERFORMANCEHINT__IDX            1
#define SBK_QQUICKTRANSFORM_IDX                                      25
#define SBK_QQUICKWINDOW_IDX                                         29
#define SBK_QQUICKWINDOW_CREATETEXTUREOPTION_IDX                     30
#define SBK_QFLAGS_QQUICKWINDOW_CREATETEXTUREOPTION__IDX             2
#define SBK_QQUICKWINDOW_RENDERSTAGE_IDX                             31
#define SBK_QQUICKWINDOW_SCENEGRAPHERROR_IDX                         32
#define SBK_QQUICKVIEW_IDX                                           26
#define SBK_QQUICKVIEW_RESIZEMODE_IDX                                27
#define SBK_QQUICKVIEW_STATUS_IDX                                    28
#define SBK_QSGTEXTUREPROVIDER_IDX                                   60
#define SBK_QSGTEXTURE_IDX                                           57
#define SBK_QSGTEXTURE_WRAPMODE_IDX                                  59
#define SBK_QSGTEXTURE_FILTERING_IDX                                 58
#define SBK_QSGDYNAMICTEXTURE_IDX                                    37
#define SBK_QSGENGINE_IDX                                            38
#define SBK_QSGENGINE_CREATETEXTUREOPTION_IDX                        39
#define SBK_QFLAGS_QSGENGINE_CREATETEXTUREOPTION__IDX                4
#define SBK_QSGABSTRACTRENDERER_IDX                                  33
#define SBK_QSGABSTRACTRENDERER_CLEARMODEBIT_IDX                     34
#define SBK_QFLAGS_QSGABSTRACTRENDERER_CLEARMODEBIT__IDX             3
#define SBK_QQUICKRENDERCONTROL_IDX                                  22
#define SBK_QQUICKTEXTDOCUMENT_IDX                                   23
#define SBK_QQUICKITEMGRABRESULT_IDX                                 18
#define SBK_QQUICKTEXTUREFACTORY_IDX                                 24
#define SBK_QQUICKIMAGERESPONSE_IDX                                  12
#define SBK_QSHAREDPOINTER_QQUICKITEMGRABRESULT_IDX                  63 // QSharedPointer<QQuickItemGrabResult >
#define SBK_QtQuick_IDX_COUNT                                        64

// This variable stores all Python types exported by this module.
extern PyTypeObject** SbkPySide2_QtQuickTypes;

// This variable stores all type converters exported by this module.
extern SbkConverter** SbkPySide2_QtQuickTypeConverters;

// Converter indices
#define SBK_QTQUICK_QLIST_QQUICKITEMPTR_IDX                          0 // QList<QQuickItem * >
#define SBK_QTQUICK_QLIST_QOBJECTPTR_IDX                             1 // const QList<QObject * > &
#define SBK_QTQUICK_QLIST_QBYTEARRAY_IDX                             2 // QList<QByteArray >
#define SBK_QTQUICK_QVECTOR_INT_IDX                                  3 // const QVector<int > &
#define SBK_QTQUICK_QLIST_QQMLERROR_IDX                              4 // QList<QQmlError >
#define SBK_QTQUICK_QLIST_QVARIANT_IDX                               5 // QList<QVariant >
#define SBK_QTQUICK_QLIST_QSTRING_IDX                                6 // QList<QString >
#define SBK_QTQUICK_QMAP_QSTRING_QVARIANT_IDX                        7 // QMap<QString, QVariant >
#define SBK_QtQuick_CONVERTERS_IDX_COUNT                             8

// Macros for type check

namespace Shiboken
{

// PyType functions, to get the PyObjectType for a type T
template<> inline PyTypeObject* SbkType< ::QSGMaterialType >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGMATERIALTYPE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGNode::NodeType >() { return SbkPySide2_QtQuickTypes[SBK_QSGNODE_NODETYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSGNode::Flag >() { return SbkPySide2_QtQuickTypes[SBK_QSGNODE_FLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QSGNode::Flag> >() { return SbkPySide2_QtQuickTypes[SBK_QFLAGS_QSGNODE_FLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QSGNode::DirtyStateBit >() { return SbkPySide2_QtQuickTypes[SBK_QSGNODE_DIRTYSTATEBIT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QSGNode::DirtyStateBit> >() { return SbkPySide2_QtQuickTypes[SBK_QFLAGS_QSGNODE_DIRTYSTATEBIT__IDX]; }
template<> inline PyTypeObject* SbkType< ::QSGNode >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGNODE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGTransformNode >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGTRANSFORMNODE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGOpacityNode >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGOPACITYNODE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGBasicGeometryNode >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGBASICGEOMETRYNODE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGGeometryNode >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGGEOMETRYNODE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGSimpleTextureNode::TextureCoordinatesTransformFlag >() { return SbkPySide2_QtQuickTypes[SBK_QSGSIMPLETEXTURENODE_TEXTURECOORDINATESTRANSFORMFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QSGSimpleTextureNode::TextureCoordinatesTransformFlag> >() { return SbkPySide2_QtQuickTypes[SBK_QFLAGS_QSGSIMPLETEXTURENODE_TEXTURECOORDINATESTRANSFORMFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QSGSimpleTextureNode >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGSIMPLETEXTURENODE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGSimpleRectNode >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGSIMPLERECTNODE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGClipNode >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGCLIPNODE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGGeometry::DataPattern >() { return SbkPySide2_QtQuickTypes[SBK_QSGGEOMETRY_DATAPATTERN_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSGGeometry >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGGEOMETRY_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGGeometry::ColoredPoint2D >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGGEOMETRY_COLOREDPOINT2D_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGGeometry::TexturedPoint2D >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGGEOMETRY_TEXTUREDPOINT2D_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGGeometry::Point2D >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGGEOMETRY_POINT2D_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGGeometry::AttributeSet >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGGEOMETRY_ATTRIBUTESET_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGGeometry::Attribute >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGGEOMETRY_ATTRIBUTE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQuickImageProvider >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QQUICKIMAGEPROVIDER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQuickAsyncImageProvider >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QQUICKASYNCIMAGEPROVIDER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQuickItem::Flag >() { return SbkPySide2_QtQuickTypes[SBK_QQUICKITEM_FLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QQuickItem::Flag> >() { return SbkPySide2_QtQuickTypes[SBK_QFLAGS_QQUICKITEM_FLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QQuickItem::ItemChange >() { return SbkPySide2_QtQuickTypes[SBK_QQUICKITEM_ITEMCHANGE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQuickItem::TransformOrigin >() { return SbkPySide2_QtQuickTypes[SBK_QQUICKITEM_TRANSFORMORIGIN_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQuickItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QQUICKITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQuickFramebufferObject >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QQUICKFRAMEBUFFEROBJECT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQuickFramebufferObject::Renderer >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QQUICKFRAMEBUFFEROBJECT_RENDERER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQuickItem::UpdatePaintNodeData >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QQUICKITEM_UPDATEPAINTNODEDATA_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQuickPaintedItem::RenderTarget >() { return SbkPySide2_QtQuickTypes[SBK_QQUICKPAINTEDITEM_RENDERTARGET_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQuickPaintedItem::PerformanceHint >() { return SbkPySide2_QtQuickTypes[SBK_QQUICKPAINTEDITEM_PERFORMANCEHINT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QQuickPaintedItem::PerformanceHint> >() { return SbkPySide2_QtQuickTypes[SBK_QFLAGS_QQUICKPAINTEDITEM_PERFORMANCEHINT__IDX]; }
template<> inline PyTypeObject* SbkType< ::QQuickPaintedItem >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QQUICKPAINTEDITEM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQuickTransform >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QQUICKTRANSFORM_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQuickWindow::CreateTextureOption >() { return SbkPySide2_QtQuickTypes[SBK_QQUICKWINDOW_CREATETEXTUREOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QQuickWindow::CreateTextureOption> >() { return SbkPySide2_QtQuickTypes[SBK_QFLAGS_QQUICKWINDOW_CREATETEXTUREOPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QQuickWindow::RenderStage >() { return SbkPySide2_QtQuickTypes[SBK_QQUICKWINDOW_RENDERSTAGE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQuickWindow::SceneGraphError >() { return SbkPySide2_QtQuickTypes[SBK_QQUICKWINDOW_SCENEGRAPHERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQuickWindow >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QQUICKWINDOW_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQuickView::ResizeMode >() { return SbkPySide2_QtQuickTypes[SBK_QQUICKVIEW_RESIZEMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQuickView::Status >() { return SbkPySide2_QtQuickTypes[SBK_QQUICKVIEW_STATUS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QQuickView >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QQUICKVIEW_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGTextureProvider >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGTEXTUREPROVIDER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGTexture::WrapMode >() { return SbkPySide2_QtQuickTypes[SBK_QSGTEXTURE_WRAPMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSGTexture::Filtering >() { return SbkPySide2_QtQuickTypes[SBK_QSGTEXTURE_FILTERING_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSGTexture >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGTEXTURE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGDynamicTexture >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGDYNAMICTEXTURE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGEngine::CreateTextureOption >() { return SbkPySide2_QtQuickTypes[SBK_QSGENGINE_CREATETEXTUREOPTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QSGEngine::CreateTextureOption> >() { return SbkPySide2_QtQuickTypes[SBK_QFLAGS_QSGENGINE_CREATETEXTUREOPTION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QSGEngine >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGENGINE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSGAbstractRenderer::ClearModeBit >() { return SbkPySide2_QtQuickTypes[SBK_QSGABSTRACTRENDERER_CLEARMODEBIT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QSGAbstractRenderer::ClearModeBit> >() { return SbkPySide2_QtQuickTypes[SBK_QFLAGS_QSGABSTRACTRENDERER_CLEARMODEBIT__IDX]; }
template<> inline PyTypeObject* SbkType< ::QSGAbstractRenderer >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSGABSTRACTRENDERER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQuickRenderControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QQUICKRENDERCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQuickTextDocument >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QQUICKTEXTDOCUMENT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQuickItemGrabResult >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QQUICKITEMGRABRESULT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQuickTextureFactory >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QQUICKTEXTUREFACTORY_IDX]); }
template<> inline PyTypeObject* SbkType< ::QQuickImageResponse >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QQUICKIMAGERESPONSE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSharedPointer<QQuickItemGrabResult > >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtQuickTypes[SBK_QSHAREDPOINTER_QQUICKITEMGRABRESULT_IDX]); }

} // namespace Shiboken

#endif // SBK_QTQUICK_PYTHON_H

