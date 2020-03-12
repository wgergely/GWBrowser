"""There currently no automated packaging set up.

I am using

"""

import os
import sys

DUMPBIN = ur'"C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\bin\amd64\dumpbin.exe"'
PACKAGE_ROOT = ur'I:\dev\bookmarks-standalone\standalone'

ALEMBIC_ROOT = ur'I:\dev\alembic-build\install'
OIIO_ROOT = ur'I:\dev\OpenImageIO-build\install'
OPENEXR_ROOT = ur'I:\dev\openexr-build\install'
OPENVDB_ROOT = ur'I:\dev\openvdb-build\install'
HEIF_ROOT = ur'I:\dev\libheif-build\libheif\Release'
VCPKG_BIN = ur'I:\dev\vcpkg\installed\x64-windows\bin'
PYTHON_ROOT = ur'C:\Python27'

LIB_ALEMBIC = ALEMBIC_ROOT + os.path.sep + 'lib' + os.path.sep + 'Alembic.dll'
LIB_ALEMBIC_D = ALEMBIC_ROOT + os.path.sep + 'site-packages' + os.path.sep + 'alembic.pyd'
LIB_OIIO =  OIIO_ROOT + os.path.sep + 'bin' + os.path.sep + 'OpenImageIO.dll'
LIB_OIIO_D =  OIIO_ROOT + os.path.sep + 'lib' + os.path.sep + 'python2.7' + os.path.sep + 'site-packages' + os.path.sep + 'OpenImageIO.pyd'
LIB_OPENVDB =  OPENVDB_ROOT + os.path.sep + 'bin' + os.path.sep + 'openvdb.dll'


TOPLIBS = (
    LIB_ALEMBIC,
    LIB_ALEMBIC_D,
    LIB_OIIO,
    LIB_OIIO_D,
    LIB_OPENVDB,
    # LIB_ALEMBIC_D,
    # LIB_ALEMBIC,
    # LIB_IEX,
    # LIB_IMATH,
    # LIB_SSL,
    # LIB_CRYPTO
)

for l in TOPLIBS:
    if not os.path.isfile(l):
        raise OSError('{} does not exists'.format(l))

def get_dependencies():
    def _get_libs(libpath, l):
        DUMPCMD = '{} /dependents {}'.format(DUMPBIN, libpath)
        r = os.popen(DUMPCMD).read()
        r = r.strip().split('\n')
        _dep = [f.strip() for f in r if f.lower().endswith('dll') and not f.lower().startswith('dump')]
        _dep = [f for f in _dep if not f.lower().startswith('file type')]
        _dep = [f for f in _dep if not [s for s in builtins if s.lower() in f.lower()]]
        l = sorted(list(set(l)))
        if not _dep:
            return l
        l += _dep
        for libpath in _dep:
            l = _get_libs(libpath, l)
        l = sorted(list(set(l)))
        return l

    builtins = ('ADVAPI32', 'dbgeng', 'MSVCP', 'KERNEL', 'VCRUNTIME', 'api-ms', 'SHELL32', 'WS2_32', 'dbeng', 'ole32')

    dependencies = []
    for L in TOPLIBS:
        dependencies = _get_libs(L, dependencies)

    LIBS = {}
    for lib in dependencies:
        LIBS[lib] = None
        for _ROOT in (
            ALEMBIC_ROOT,
            OIIO_ROOT,
            OPENEXR_ROOT,
            HEIF_ROOT,
            OPENVDB_ROOT,
            PYTHON_ROOT,
            HEIF_ROOT,
            VCPKG_BIN,
        ):
            for root, _, files in os.walk(_ROOT):
                for f in files:
                    if f.lower() == lib.lower():
                        LIBS[lib] = root + os.path.sep + f
                        break
            if LIBS[lib]:
                break

    for k, v in sorted(LIBS.items(), key=lambda x: x[0]):
        if v is None:
            print '\x1B[37m\n', k, '\x1B[0m\n', '\x1B[31mNot Found\x1B[0m'
        else:
            print '\x1B[37m\n', k, '\x1B[0m\n', '\x1B[32m', v, '\x1B[0m'

    if not all(LIBS.values()):
        raise EnvironmentError('Not all dependencies found.\nMissing: {}'.format(
            ','.join([i[0] for i in LIBS.items() if i[1] is None])
        ))




get_dependencies()
