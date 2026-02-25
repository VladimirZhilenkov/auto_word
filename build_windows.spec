# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Windows build
# Build: pyinstaller build_windows.spec
#
# ANTI-VIRUS NOTES:
# - UPX disabled (upx=False) to avoid false positives
# - --onedir mode to avoid temp extraction (less suspicious)
# - Version info embedded for legitimacy

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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy.testing',
        'scipy',
        'PIL',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DocumentGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX OFF — avoid antivirus false positives
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,           # Add icon path here if you have one: 'resources/icon.ico'
    version='file_version_info.txt',  # Embedded version info
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,           # UPX OFF here too
    upx_exclude=[],
    name='DocumentGenerator',
)
