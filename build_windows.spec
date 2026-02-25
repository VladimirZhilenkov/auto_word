# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Windows build
# Build: pyinstaller build_windows.spec
#
# ONEFILE mode — single DocumentGenerator.exe, no _internal folder.
# This is the same approach as v2.4.0 with additional hiddenimports.

import sys
from pathlib import Path

block_cipher = None

# Get the project root
project_root = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('app', 'app'),
    ],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'sqlalchemy',
        'sqlalchemy.sql.default_comparator',
        'sqlalchemy.ext.declarative',
        'sqlalchemy.dialects.sqlite',
        'docxtpl',
        'docx',
        'jinja2',
        'lxml',
        'lxml._elementpath',
        'pandas',
        'openpyxl',
        'pymorphy3',
        'pymorphy3_dicts_ru',
        'dawg_python',
        'packaging',
        'packaging.version',
        'certifi',
    ],
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DocumentGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one: 'icon.ico'
    version='file_version_info.txt',  # Embedded version info
)
