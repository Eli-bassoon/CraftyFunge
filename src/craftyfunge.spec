# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['craftyfunge.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

import os
startPath = r"C:\Files\Programming\Python\MyCode\CraftyFunge\src"
a.datas.extend([
    ('data/block_to_value.csv', os.path.join(startPath, 'data/block_to_value.csv'), 'DATA'),
])

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='craftyfunge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Copy config over
import shutil
shutil.copyfile(os.path.join(startPath, 'world.cfg'), os.path.join(DISTPATH, 'world.cfg'))