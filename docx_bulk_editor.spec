# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification file for DOCX Bulk Editor.

This file configures how PyInstaller packages the application into a
standalone executable for Windows distribution.

Build command:
    pyinstaller docx_bulk_editor.spec --clean

Output:
    dist/docx_bulk_editor.exe (~150-200MB single-file executable)

Target:
    - Size: <200MB (PRD NFR-11.2)
    - Startup time: <3 seconds (PRD NFR-1.1)
    - No console window
    - UPX compression enabled
"""

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.json', '.'),  # Include default configuration
    ],
    hiddenimports=[
        # Critical for multiprocessing
        'multiprocessing',
        'multiprocessing.pool',

        # Document processing
        'docx',
        'lxml',
        'lxml.etree',
        'lxml._elementpath',

        # PySide6 Qt modules
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',

        # Application processors (dynamic imports)
        'src.processors.search_replace',
        'src.processors.metadata',
        'src.processors.validator',
        'src.processors.table_formatter',
        'src.processors.style_enforcer',
        'src.processors.shading_remover',

        # Other application modules
        'src.core.config',
        'src.core.logger',
        'src.core.backup',
        'src.database.db_manager',
        'src.workers.job_worker',
        'src.ui.main_window',
        'src.ui.progress_dialog',
        'src.ui.settings_dialog',
        'src.ui.history_window',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary packages to reduce size
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'sphinx',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='docx_bulk_editor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Enable UPX compression
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI application)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # TODO: Add icon file when available
)
