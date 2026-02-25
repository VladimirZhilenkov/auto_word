# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Document Generator application.
Build command: pyinstaller document_generator.spec
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect pymorphy2 data files
pymorphy2_datas = collect_data_files('pymorphy2_dicts_ru')

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('docx_files', 'docx_files'),
        ('data', 'data'),
    ] + pymorphy2_datas,
    hiddenimports=[
        'pymorphy2',
        'pymorphy2_dicts_ru',
        'sqlalchemy.dialects.sqlite',
        'pandas',
        'openpyxl',
        'docxtpl',
        'jinja2',
    ] + collect_submodules('pymorphy2'),
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

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

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
    console=False,      # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,           # Add icon path here: 'resources/icon.ico'
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

# For macOS app bundle (optional)
app = BUNDLE(
    exe,
    name='DocumentGenerator.app',
    icon=None,  # Add icon path here: 'assets/icon.icns'
    bundle_identifier='com.documentgenerator.app',
    info_plist={
        'CFBundleName': 'Document Generator',
        'CFBundleDisplayName': 'Генератор документов',
        'CFBundleVersion': '2.4.0',
        'CFBundleShortVersionString': '2.4.0',
        'NSHighResolutionCapable': True,
    },
)
