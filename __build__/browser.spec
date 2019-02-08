# -*- mode: python -*-

block_cipher = None


a = Analysis(
    ['../standalone.py'],
    pathex=['E:\\GW_ASSETS\\git\\browser'],
    binaries=[],
    datas=[
        ('../rsc/*', 'browser/rsc'),
        ('../rsc/fonts*', 'browser/rsc/fonts'),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Browser',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    icon='../rsc/custom.ico',
    console=False)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='Browser')
