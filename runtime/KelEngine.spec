# -*- mode: python ; coding: utf-8 -*-
# Kel Runtime PyInstaller spec (repository-relative).
# Build (from the repository root):  pyinstaller runtime/KelEngine.spec
import os
from pathlib import Path

BASE = Path(SPECPATH).resolve()

a = Analysis(
    [str(BASE / 'kel_backend_entry.py')],
    pathex=[str(BASE)],
    binaries=[],
    datas=[
        (str(BASE / 'kel' / 'web'), 'kel/web'),
        (str(BASE / 'kel' / 'native_claude.mjs'), 'kel'),
        (str(BASE / 'kel' / 'native_group.py'), 'kel'),
        (str(BASE / 'kel' / 'host_claude.mjs'), 'kel'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig=dict(),
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='KelEngine',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KelEngine',
)
