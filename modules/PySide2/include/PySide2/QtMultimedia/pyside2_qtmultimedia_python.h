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


#ifndef SBK_QTMULTIMEDIA_PYTHON_H
#define SBK_QTMULTIMEDIA_PYTHON_H

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
#include <pyside2_qtnetwork_python.h>

// Binded library includes
#include <qcameraviewfindersettings.h>
#include <qcameracapturedestinationcontrol.h>
#include <qradiotuner.h>
#include <qvideoencodersettingscontrol.h>
#include <qmediaplaylist.h>
#include <qmediatimerange.h>
#include <qvideoframe.h>
#include <qcameralockscontrol.h>
#include <qcameraviewfindersettingscontrol.h>
#include <qmultimedia.h>
#include <qmediarecordercontrol.h>
#include <qaudiobuffer.h>
#include <qcameracontrol.h>
#include <qmediaencodersettings.h>
#include <qcamera.h>
#include <qvideosurfaceformat.h>
#include <qmedianetworkaccesscontrol.h>
#include <qcameraexposurecontrol.h>
#include <qradiotunercontrol.h>
#include <qcameraimagecapturecontrol.h>
#include <qaudioinputselectorcontrol.h>
#include <qsound.h>
#include <qabstractvideofilter.h>
#include <qmediarecorder.h>
#include <qaudiosystem.h>
#include <qaudiooutput.h>
#include <qabstractvideobuffer.h>
#include <qmediacontainercontrol.h>
#include <qmediaavailabilitycontrol.h>
#include <qradiodata.h>
#include <qvideowindowcontrol.h>
#include <qaudiooutputselectorcontrol.h>
#include <qaudioformat.h>
#include <qvideoprobe.h>
#include <qmediaplayer.h>
#include <qvideorenderercontrol.h>
#include <qmediaplayercontrol.h>
#include <qsoundeffect.h>
#include <qmediagaplessplaybackcontrol.h>
#include <qcamerazoomcontrol.h>
#include <qcameracapturebufferformatcontrol.h>
#include <qmediacontent.h>
#include <qcamerafocus.h>
#include <qaudiodeviceinfo.h>
#include <qmediaobject.h>
#include <qmediaaudioprobecontrol.h>
#include <qradiodatacontrol.h>
#include <qcamerainfo.h>
#include <qaudioinput.h>
#include <qaudioencodersettingscontrol.h>
#include <qmediacontrol.h>
#include <qcamerainfocontrol.h>
#include <qaudioprobe.h>
#include <qaudio.h>
#include <qmediaresource.h>
#include <qmediabindableinterface.h>
#include <qvideodeviceselectorcontrol.h>
#include <qimageencodercontrol.h>
#include <qcameraimagecapture.h>
#include <qaudiodecoder.h>
#include <qaudiodecodercontrol.h>
#include <qaudiorolecontrol.h>
#include <qaudiorecorder.h>
#include <qabstractvideosurface.h>
#include <qcameraimageprocessingcontrol.h>
// Conversion Includes - Primitive Types
#include <QStringList>
#include <qabstractitemmodel.h>
#include <signalmanager.h>
#include <wtypes.h>
#include <QString>

// Conversion Includes - Container Types
#include <QList>
#include <QLinkedList>
#include <QMap>
#include <pysideqflags.h>
#include <QPair>
#include <QQueue>
#include <QMultiMap>
#include <QSet>
#include <QStack>
#include <QVector>

// Type indices
#define SBK_QAUDIO_IDX                                               9
#define SBK_QAUDIO_ERROR_IDX                                         10
#define SBK_QAUDIO_STATE_IDX                                         13
#define SBK_QAUDIO_MODE_IDX                                          11
#define SBK_QAUDIO_ROLE_IDX                                          12
#define SBK_QMULTIMEDIA_IDX                                          97
#define SBK_QMULTIMEDIA_SUPPORTESTIMATE_IDX                          101
#define SBK_QMULTIMEDIA_ENCODINGQUALITY_IDX                          100
#define SBK_QMULTIMEDIA_ENCODINGMODE_IDX                             99
#define SBK_QMULTIMEDIA_AVAILABILITYSTATUS_IDX                       98
#define SBK_QVIDEOFILTERRUNNABLE_IDX                                 121
#define SBK_QVIDEOFILTERRUNNABLE_RUNFLAG_IDX                         122
#define SBK_QFLAGS_QVIDEOFILTERRUNNABLE_RUNFLAG__IDX                 69
#define SBK_QMEDIARESOURCE_IDX                                       95
#define SBK_QIMAGEENCODERSETTINGS_IDX                                71
#define SBK_QVIDEOENCODERSETTINGS_IDX                                119
#define SBK_QAUDIOENCODERSETTINGS_IDX                                20
#define SBK_QAUDIODEVICEINFO_IDX                                     19
#define SBK_QAUDIOBUFFER_IDX                                         14
#define SBK_QAUDIOFORMAT_IDX                                         22
#define SBK_QAUDIOFORMAT_SAMPLETYPE_IDX                              24
#define SBK_QAUDIOFORMAT_ENDIAN_IDX                                  23
#define SBK_QMEDIATIMERANGE_IDX                                      96
#define SBK_QCAMERAVIEWFINDERSETTINGS_IDX                            60
#define SBK_QVIDEOFRAME_IDX                                          123
#define SBK_QVIDEOFRAME_FIELDTYPE_IDX                                124
#define SBK_QVIDEOFRAME_PIXELFORMAT_IDX                              125
#define SBK_QABSTRACTVIDEOBUFFER_IDX                                 3
#define SBK_QABSTRACTVIDEOBUFFER_HANDLETYPE_IDX                      4
#define SBK_QABSTRACTVIDEOBUFFER_MAPMODE_IDX                         5
#define SBK_QVIDEOSURFACEFORMAT_IDX                                  128
#define SBK_QVIDEOSURFACEFORMAT_DIRECTION_IDX                        129
#define SBK_QVIDEOSURFACEFORMAT_YCBCRCOLORSPACE_IDX                  130
#define SBK_QCAMERAFOCUSZONE_IDX                                     48
#define SBK_QCAMERAFOCUSZONE_FOCUSZONESTATUS_IDX                     49
#define SBK_QMEDIABINDABLEINTERFACE_IDX                              74
#define SBK_QABSTRACTAUDIODEVICEINFO_IDX                             0
#define SBK_QABSTRACTAUDIOOUTPUT_IDX                                 2
#define SBK_QSOUNDEFFECT_IDX                                         115
#define SBK_QSOUNDEFFECT_LOOP_IDX                                    116
#define SBK_QSOUNDEFFECT_STATUS_IDX                                  117
#define SBK_QMEDIARECORDER_IDX                                       90
#define SBK_QMEDIARECORDER_STATE_IDX                                 92
#define SBK_QMEDIARECORDER_STATUS_IDX                                93
#define SBK_QMEDIARECORDER_ERROR_IDX                                 91
#define SBK_QAUDIORECORDER_IDX                                       30
#define SBK_QCAMERAIMAGECAPTURE_IDX                                  50
#define SBK_QCAMERAIMAGECAPTURE_ERROR_IDX                            53
#define SBK_QCAMERAIMAGECAPTURE_DRIVEMODE_IDX                        52
#define SBK_QCAMERAIMAGECAPTURE_CAPTUREDESTINATION_IDX               51
#define SBK_QFLAGS_QCAMERAIMAGECAPTURE_CAPTUREDESTINATION__IDX       67
#define SBK_QRADIODATA_IDX                                           102
#define SBK_QRADIODATA_ERROR_IDX                                     103
#define SBK_QRADIODATA_PROGRAMTYPE_IDX                               104
#define SBK_QMEDIAPLAYLIST_IDX                                       87
#define SBK_QMEDIAPLAYLIST_PLAYBACKMODE_IDX                          89
#define SBK_QMEDIAPLAYLIST_ERROR_IDX                                 88
#define SBK_QABSTRACTVIDEOFILTER_IDX                                 6
#define SBK_QMEDIAOBJECT_IDX                                         80
#define SBK_QMEDIAPLAYER_IDX                                         81
#define SBK_QMEDIAPLAYER_STATE_IDX                                   85
#define SBK_QMEDIAPLAYER_MEDIASTATUS_IDX                             84
#define SBK_QMEDIAPLAYER_FLAG_IDX                                    83
#define SBK_QFLAGS_QMEDIAPLAYER_FLAG__IDX                            68
#define SBK_QMEDIAPLAYER_ERROR_IDX                                   82
#define SBK_QCAMERA_IDX                                              32
#define SBK_QCAMERA_STATUS_IDX                                       41
#define SBK_QCAMERA_STATE_IDX                                        40
#define SBK_QCAMERA_CAPTUREMODE_IDX                                  33
#define SBK_QFLAGS_QCAMERA_CAPTUREMODE__IDX                          65
#define SBK_QCAMERA_ERROR_IDX                                        34
#define SBK_QCAMERA_LOCKSTATUS_IDX                                   37
#define SBK_QCAMERA_LOCKCHANGEREASON_IDX                             36
#define SBK_QCAMERA_LOCKTYPE_IDX                                     38
#define SBK_QFLAGS_QCAMERA_LOCKTYPE__IDX                             66
#define SBK_QCAMERA_POSITION_IDX                                     39
#define SBK_QCAMERA_FRAMERATERANGE_IDX                               35
#define SBK_QRADIOTUNER_IDX                                          106
#define SBK_QRADIOTUNER_STATE_IDX                                    110
#define SBK_QRADIOTUNER_BAND_IDX                                     107
#define SBK_QRADIOTUNER_ERROR_IDX                                    108
#define SBK_QRADIOTUNER_STEREOMODE_IDX                               111
#define SBK_QRADIOTUNER_SEARCHMODE_IDX                               109
#define SBK_QAUDIODECODER_IDX                                        15
#define SBK_QAUDIODECODER_STATE_IDX                                  17
#define SBK_QAUDIODECODER_ERROR_IDX                                  16
#define SBK_QABSTRACTVIDEOSURFACE_IDX                                7
#define SBK_QABSTRACTVIDEOSURFACE_ERROR_IDX                          8
#define SBK_QVIDEOPROBE_IDX                                          126
#define SBK_QMEDIACONTROL_IDX                                        77
#define SBK_QMEDIACONTAINERCONTROL_IDX                               75
#define SBK_QMEDIAAUDIOPROBECONTROL_IDX                              72
#define SBK_QMEDIAAVAILABILITYCONTROL_IDX                            73
#define SBK_QMEDIANETWORKACCESSCONTROL_IDX                           79
#define SBK_QMEDIAGAPLESSPLAYBACKCONTROL_IDX                         78
#define SBK_QRADIODATACONTROL_IDX                                    105
#define SBK_QMEDIAPLAYERCONTROL_IDX                                  86
#define SBK_QMEDIARECORDERCONTROL_IDX                                94
#define SBK_QVIDEODEVICESELECTORCONTROL_IDX                          118
#define SBK_QVIDEOENCODERSETTINGSCONTROL_IDX                         120
#define SBK_QRADIOTUNERCONTROL_IDX                                   112
#define SBK_QAUDIODECODERCONTROL_IDX                                 18
#define SBK_QVIDEORENDERERCONTROL_IDX                                127
#define SBK_QVIDEOWINDOWCONTROL_IDX                                  131
#define SBK_QAUDIOOUTPUTSELECTORCONTROL_IDX                          28
#define SBK_QAUDIOROLECONTROL_IDX                                    31
#define SBK_QAUDIOENCODERSETTINGSCONTROL_IDX                         21
#define SBK_QAUDIOINPUTSELECTORCONTROL_IDX                           26
#define SBK_QCAMERACONTROL_IDX                                       44
#define SBK_QCAMERACONTROL_PROPERTYCHANGETYPE_IDX                    45
#define SBK_QCAMERAEXPOSURECONTROL_IDX                               46
#define SBK_QCAMERAEXPOSURECONTROL_EXPOSUREPARAMETER_IDX             47
#define SBK_QCAMERACAPTUREBUFFERFORMATCONTROL_IDX                    42
#define SBK_QCAMERACAPTUREDESTINATIONCONTROL_IDX                     43
#define SBK_QCAMERAINFOCONTROL_IDX                                   58
#define SBK_QCAMERALOCKSCONTROL_IDX                                  59
#define SBK_QCAMERAIMAGECAPTURECONTROL_IDX                           54
#define SBK_QCAMERAIMAGEPROCESSINGCONTROL_IDX                        55
#define SBK_QCAMERAIMAGEPROCESSINGCONTROL_PROCESSINGPARAMETER_IDX    56
#define SBK_QCAMERAZOOMCONTROL_IDX                                   64
#define SBK_QIMAGEENCODERCONTROL_IDX                                 70
#define SBK_QCAMERAVIEWFINDERSETTINGSCONTROL_IDX                     61
#define SBK_QCAMERAVIEWFINDERSETTINGSCONTROL_VIEWFINDERPARAMETER_IDX 63
#define SBK_QCAMERAVIEWFINDERSETTINGSCONTROL2_IDX                    62
#define SBK_QAUDIOOUTPUT_IDX                                         27
#define SBK_QAUDIOPROBE_IDX                                          29
#define SBK_QAUDIOINPUT_IDX                                          25
#define SBK_QABSTRACTAUDIOINPUT_IDX                                  1
#define SBK_QSOUND_IDX                                               113
#define SBK_QSOUND_LOOP_IDX                                          114
#define SBK_QCAMERAINFO_IDX                                          57
#define SBK_QMEDIACONTENT_IDX                                        76
#define SBK_QtMultimedia_IDX_COUNT                                   132

// This variable stores all Python types exported by this module.
extern PyTypeObject** SbkPySide2_QtMultimediaTypes;

// This variable stores all type converters exported by this module.
extern SbkConverter** SbkPySide2_QtMultimediaTypeConverters;

// Converter indices
#define SBK_QTMULTIMEDIA_QLIST_QAUDIODEVICEINFO_IDX                  0 // QList<QAudioDeviceInfo >
#define SBK_QTMULTIMEDIA_QLIST_QAUDIOFORMAT_ENDIAN_IDX               1 // QList<QAudioFormat::Endian >
#define SBK_QTMULTIMEDIA_QLIST_INT_IDX                               2 // QList<int >
#define SBK_QTMULTIMEDIA_QLIST_QAUDIOFORMAT_SAMPLETYPE_IDX           3 // QList<QAudioFormat::SampleType >
#define SBK_QTMULTIMEDIA_QLIST_QBYTEARRAY_IDX                        4 // QList<QByteArray >
#define SBK_QTMULTIMEDIA_QLIST_QOBJECTPTR_IDX                        5 // const QList<QObject * > &
#define SBK_QTMULTIMEDIA_QLIST_QREAL_IDX                             6 // QList<qreal >
#define SBK_QTMULTIMEDIA_QLIST_QSIZE_IDX                             7 // QList<QSize >
#define SBK_QTMULTIMEDIA_QLIST_QVIDEOFRAME_PIXELFORMAT_IDX           8 // QList<QVideoFrame::PixelFormat >
#define SBK_QTMULTIMEDIA_QLIST_QMEDIACONTENT_IDX                     9 // const QList<QMediaContent > &
#define SBK_QTMULTIMEDIA_QLIST_QNETWORKCONFIGURATION_IDX             10 // const QList<QNetworkConfiguration > &
#define SBK_QTMULTIMEDIA_QLIST_QAUDIO_ROLE_IDX                       11 // QList<QAudio::Role >
#define SBK_QTMULTIMEDIA_QLIST_QCAMERA_FRAMERATERANGE_IDX            12 // QList<QCamera::FrameRateRange >
#define SBK_QTMULTIMEDIA_QLIST_QCAMERAVIEWFINDERSETTINGS_IDX         13 // QList<QCameraViewfinderSettings >
#define SBK_QTMULTIMEDIA_QPAIR_INT_INT_IDX                           14 // QPair<int, int >
#define SBK_QTMULTIMEDIA_QLIST_QSTRING_IDX                           15 // QList<QString >
#define SBK_QTMULTIMEDIA_QLIST_QVARIANT_IDX                          16 // QList<QVariant >
#define SBK_QTMULTIMEDIA_QLIST_QCAMERAINFO_IDX                       17 // QList<QCameraInfo >
#define SBK_QTMULTIMEDIA_QLIST_QMEDIARESOURCE_IDX                    18 // const QList<QMediaResource > &
#define SBK_QTMULTIMEDIA_QMAP_QSTRING_QVARIANT_IDX                   19 // QMap<QString, QVariant >
#define SBK_QtMultimedia_CONVERTERS_IDX_COUNT                        20

// Macros for type check

namespace Shiboken
{

// PyType functions, to get the PyObjectType for a type T
template<> inline PyTypeObject* SbkType< ::QAudio::Error >() { return SbkPySide2_QtMultimediaTypes[SBK_QAUDIO_ERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAudio::State >() { return SbkPySide2_QtMultimediaTypes[SBK_QAUDIO_STATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAudio::Mode >() { return SbkPySide2_QtMultimediaTypes[SBK_QAUDIO_MODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAudio::Role >() { return SbkPySide2_QtMultimediaTypes[SBK_QAUDIO_ROLE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMultimedia::SupportEstimate >() { return SbkPySide2_QtMultimediaTypes[SBK_QMULTIMEDIA_SUPPORTESTIMATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMultimedia::EncodingQuality >() { return SbkPySide2_QtMultimediaTypes[SBK_QMULTIMEDIA_ENCODINGQUALITY_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMultimedia::EncodingMode >() { return SbkPySide2_QtMultimediaTypes[SBK_QMULTIMEDIA_ENCODINGMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMultimedia::AvailabilityStatus >() { return SbkPySide2_QtMultimediaTypes[SBK_QMULTIMEDIA_AVAILABILITYSTATUS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QVideoFilterRunnable::RunFlag >() { return SbkPySide2_QtMultimediaTypes[SBK_QVIDEOFILTERRUNNABLE_RUNFLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QVideoFilterRunnable::RunFlag> >() { return SbkPySide2_QtMultimediaTypes[SBK_QFLAGS_QVIDEOFILTERRUNNABLE_RUNFLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QVideoFilterRunnable >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QVIDEOFILTERRUNNABLE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMediaResource >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QMEDIARESOURCE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QImageEncoderSettings >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QIMAGEENCODERSETTINGS_IDX]); }
template<> inline PyTypeObject* SbkType< ::QVideoEncoderSettings >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QVIDEOENCODERSETTINGS_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAudioEncoderSettings >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QAUDIOENCODERSETTINGS_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAudioDeviceInfo >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QAUDIODEVICEINFO_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAudioBuffer >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QAUDIOBUFFER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAudioFormat::SampleType >() { return SbkPySide2_QtMultimediaTypes[SBK_QAUDIOFORMAT_SAMPLETYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAudioFormat::Endian >() { return SbkPySide2_QtMultimediaTypes[SBK_QAUDIOFORMAT_ENDIAN_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAudioFormat >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QAUDIOFORMAT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMediaTimeRange >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QMEDIATIMERANGE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCameraViewfinderSettings >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERAVIEWFINDERSETTINGS_IDX]); }
template<> inline PyTypeObject* SbkType< ::QVideoFrame::FieldType >() { return SbkPySide2_QtMultimediaTypes[SBK_QVIDEOFRAME_FIELDTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QVideoFrame::PixelFormat >() { return SbkPySide2_QtMultimediaTypes[SBK_QVIDEOFRAME_PIXELFORMAT_IDX]; }
template<> inline PyTypeObject* SbkType< ::QVideoFrame >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QVIDEOFRAME_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractVideoBuffer::HandleType >() { return SbkPySide2_QtMultimediaTypes[SBK_QABSTRACTVIDEOBUFFER_HANDLETYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractVideoBuffer::MapMode >() { return SbkPySide2_QtMultimediaTypes[SBK_QABSTRACTVIDEOBUFFER_MAPMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractVideoBuffer >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QABSTRACTVIDEOBUFFER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QVideoSurfaceFormat::Direction >() { return SbkPySide2_QtMultimediaTypes[SBK_QVIDEOSURFACEFORMAT_DIRECTION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QVideoSurfaceFormat::YCbCrColorSpace >() { return SbkPySide2_QtMultimediaTypes[SBK_QVIDEOSURFACEFORMAT_YCBCRCOLORSPACE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QVideoSurfaceFormat >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QVIDEOSURFACEFORMAT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCameraFocusZone::FocusZoneStatus >() { return SbkPySide2_QtMultimediaTypes[SBK_QCAMERAFOCUSZONE_FOCUSZONESTATUS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCameraFocusZone >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERAFOCUSZONE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMediaBindableInterface >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QMEDIABINDABLEINTERFACE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractAudioDeviceInfo >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QABSTRACTAUDIODEVICEINFO_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractAudioOutput >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QABSTRACTAUDIOOUTPUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSoundEffect::Loop >() { return SbkPySide2_QtMultimediaTypes[SBK_QSOUNDEFFECT_LOOP_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSoundEffect::Status >() { return SbkPySide2_QtMultimediaTypes[SBK_QSOUNDEFFECT_STATUS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSoundEffect >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QSOUNDEFFECT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMediaRecorder::State >() { return SbkPySide2_QtMultimediaTypes[SBK_QMEDIARECORDER_STATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMediaRecorder::Status >() { return SbkPySide2_QtMultimediaTypes[SBK_QMEDIARECORDER_STATUS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMediaRecorder::Error >() { return SbkPySide2_QtMultimediaTypes[SBK_QMEDIARECORDER_ERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMediaRecorder >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QMEDIARECORDER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAudioRecorder >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QAUDIORECORDER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCameraImageCapture::Error >() { return SbkPySide2_QtMultimediaTypes[SBK_QCAMERAIMAGECAPTURE_ERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCameraImageCapture::DriveMode >() { return SbkPySide2_QtMultimediaTypes[SBK_QCAMERAIMAGECAPTURE_DRIVEMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCameraImageCapture::CaptureDestination >() { return SbkPySide2_QtMultimediaTypes[SBK_QCAMERAIMAGECAPTURE_CAPTUREDESTINATION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QCameraImageCapture::CaptureDestination> >() { return SbkPySide2_QtMultimediaTypes[SBK_QFLAGS_QCAMERAIMAGECAPTURE_CAPTUREDESTINATION__IDX]; }
template<> inline PyTypeObject* SbkType< ::QCameraImageCapture >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERAIMAGECAPTURE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QRadioData::Error >() { return SbkPySide2_QtMultimediaTypes[SBK_QRADIODATA_ERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QRadioData::ProgramType >() { return SbkPySide2_QtMultimediaTypes[SBK_QRADIODATA_PROGRAMTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QRadioData >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QRADIODATA_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMediaPlaylist::PlaybackMode >() { return SbkPySide2_QtMultimediaTypes[SBK_QMEDIAPLAYLIST_PLAYBACKMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMediaPlaylist::Error >() { return SbkPySide2_QtMultimediaTypes[SBK_QMEDIAPLAYLIST_ERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMediaPlaylist >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QMEDIAPLAYLIST_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractVideoFilter >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QABSTRACTVIDEOFILTER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMediaObject >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QMEDIAOBJECT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMediaPlayer::State >() { return SbkPySide2_QtMultimediaTypes[SBK_QMEDIAPLAYER_STATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMediaPlayer::MediaStatus >() { return SbkPySide2_QtMultimediaTypes[SBK_QMEDIAPLAYER_MEDIASTATUS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMediaPlayer::Flag >() { return SbkPySide2_QtMultimediaTypes[SBK_QMEDIAPLAYER_FLAG_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QMediaPlayer::Flag> >() { return SbkPySide2_QtMultimediaTypes[SBK_QFLAGS_QMEDIAPLAYER_FLAG__IDX]; }
template<> inline PyTypeObject* SbkType< ::QMediaPlayer::Error >() { return SbkPySide2_QtMultimediaTypes[SBK_QMEDIAPLAYER_ERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QMediaPlayer >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QMEDIAPLAYER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCamera::Status >() { return SbkPySide2_QtMultimediaTypes[SBK_QCAMERA_STATUS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCamera::State >() { return SbkPySide2_QtMultimediaTypes[SBK_QCAMERA_STATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCamera::CaptureMode >() { return SbkPySide2_QtMultimediaTypes[SBK_QCAMERA_CAPTUREMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QCamera::CaptureMode> >() { return SbkPySide2_QtMultimediaTypes[SBK_QFLAGS_QCAMERA_CAPTUREMODE__IDX]; }
template<> inline PyTypeObject* SbkType< ::QCamera::Error >() { return SbkPySide2_QtMultimediaTypes[SBK_QCAMERA_ERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCamera::LockStatus >() { return SbkPySide2_QtMultimediaTypes[SBK_QCAMERA_LOCKSTATUS_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCamera::LockChangeReason >() { return SbkPySide2_QtMultimediaTypes[SBK_QCAMERA_LOCKCHANGEREASON_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCamera::LockType >() { return SbkPySide2_QtMultimediaTypes[SBK_QCAMERA_LOCKTYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QFlags<QCamera::LockType> >() { return SbkPySide2_QtMultimediaTypes[SBK_QFLAGS_QCAMERA_LOCKTYPE__IDX]; }
template<> inline PyTypeObject* SbkType< ::QCamera::Position >() { return SbkPySide2_QtMultimediaTypes[SBK_QCAMERA_POSITION_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCamera >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERA_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCamera::FrameRateRange >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERA_FRAMERATERANGE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QRadioTuner::State >() { return SbkPySide2_QtMultimediaTypes[SBK_QRADIOTUNER_STATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QRadioTuner::Band >() { return SbkPySide2_QtMultimediaTypes[SBK_QRADIOTUNER_BAND_IDX]; }
template<> inline PyTypeObject* SbkType< ::QRadioTuner::Error >() { return SbkPySide2_QtMultimediaTypes[SBK_QRADIOTUNER_ERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QRadioTuner::StereoMode >() { return SbkPySide2_QtMultimediaTypes[SBK_QRADIOTUNER_STEREOMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QRadioTuner::SearchMode >() { return SbkPySide2_QtMultimediaTypes[SBK_QRADIOTUNER_SEARCHMODE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QRadioTuner >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QRADIOTUNER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAudioDecoder::State >() { return SbkPySide2_QtMultimediaTypes[SBK_QAUDIODECODER_STATE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAudioDecoder::Error >() { return SbkPySide2_QtMultimediaTypes[SBK_QAUDIODECODER_ERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAudioDecoder >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QAUDIODECODER_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractVideoSurface::Error >() { return SbkPySide2_QtMultimediaTypes[SBK_QABSTRACTVIDEOSURFACE_ERROR_IDX]; }
template<> inline PyTypeObject* SbkType< ::QAbstractVideoSurface >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QABSTRACTVIDEOSURFACE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QVideoProbe >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QVIDEOPROBE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMediaControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QMEDIACONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMediaContainerControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QMEDIACONTAINERCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMediaAudioProbeControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QMEDIAAUDIOPROBECONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMediaAvailabilityControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QMEDIAAVAILABILITYCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMediaNetworkAccessControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QMEDIANETWORKACCESSCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMediaGaplessPlaybackControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QMEDIAGAPLESSPLAYBACKCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QRadioDataControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QRADIODATACONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMediaPlayerControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QMEDIAPLAYERCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMediaRecorderControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QMEDIARECORDERCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QVideoDeviceSelectorControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QVIDEODEVICESELECTORCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QVideoEncoderSettingsControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QVIDEOENCODERSETTINGSCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QRadioTunerControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QRADIOTUNERCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAudioDecoderControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QAUDIODECODERCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QVideoRendererControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QVIDEORENDERERCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QVideoWindowControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QVIDEOWINDOWCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAudioOutputSelectorControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QAUDIOOUTPUTSELECTORCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAudioRoleControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QAUDIOROLECONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAudioEncoderSettingsControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QAUDIOENCODERSETTINGSCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAudioInputSelectorControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QAUDIOINPUTSELECTORCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCameraControl::PropertyChangeType >() { return SbkPySide2_QtMultimediaTypes[SBK_QCAMERACONTROL_PROPERTYCHANGETYPE_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCameraControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERACONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCameraExposureControl::ExposureParameter >() { return SbkPySide2_QtMultimediaTypes[SBK_QCAMERAEXPOSURECONTROL_EXPOSUREPARAMETER_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCameraExposureControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERAEXPOSURECONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCameraCaptureBufferFormatControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERACAPTUREBUFFERFORMATCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCameraCaptureDestinationControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERACAPTUREDESTINATIONCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCameraInfoControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERAINFOCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCameraLocksControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERALOCKSCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCameraImageCaptureControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERAIMAGECAPTURECONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCameraImageProcessingControl::ProcessingParameter >() { return SbkPySide2_QtMultimediaTypes[SBK_QCAMERAIMAGEPROCESSINGCONTROL_PROCESSINGPARAMETER_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCameraImageProcessingControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERAIMAGEPROCESSINGCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCameraZoomControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERAZOOMCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QImageEncoderControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QIMAGEENCODERCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCameraViewfinderSettingsControl::ViewfinderParameter >() { return SbkPySide2_QtMultimediaTypes[SBK_QCAMERAVIEWFINDERSETTINGSCONTROL_VIEWFINDERPARAMETER_IDX]; }
template<> inline PyTypeObject* SbkType< ::QCameraViewfinderSettingsControl >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERAVIEWFINDERSETTINGSCONTROL_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCameraViewfinderSettingsControl2 >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERAVIEWFINDERSETTINGSCONTROL2_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAudioOutput >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QAUDIOOUTPUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAudioProbe >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QAUDIOPROBE_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAudioInput >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QAUDIOINPUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QAbstractAudioInput >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QABSTRACTAUDIOINPUT_IDX]); }
template<> inline PyTypeObject* SbkType< ::QSound::Loop >() { return SbkPySide2_QtMultimediaTypes[SBK_QSOUND_LOOP_IDX]; }
template<> inline PyTypeObject* SbkType< ::QSound >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QSOUND_IDX]); }
template<> inline PyTypeObject* SbkType< ::QCameraInfo >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QCAMERAINFO_IDX]); }
template<> inline PyTypeObject* SbkType< ::QMediaContent >() { return reinterpret_cast<PyTypeObject*>(SbkPySide2_QtMultimediaTypes[SBK_QMEDIACONTENT_IDX]); }

} // namespace Shiboken

#endif // SBK_QTMULTIMEDIA_PYTHON_H

