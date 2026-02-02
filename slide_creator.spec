# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Slide Creator.
Build with: pyinstaller slide_creator.spec
"""

import os
import sys

block_cipher = None

# Get the directory containing this spec file
spec_dir = os.path.dirname(os.path.abspath(SPEC))

# Collect data files
datas = [
    # Include frameworks.json
    (os.path.join(spec_dir, 'app', 'frameworks.json'), 'app'),
    # Include .env.example as template
    (os.path.join(spec_dir, '.env.example'), '.'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'pydantic',
    'pydantic.deprecated',
    'pydantic.deprecated.decorator',
    'pydantic_core',
    'openai',
    'httpx',
    'rich',
    'rich.console',
    'rich.panel',
    'rich.prompt',
    'rich.table',
    'rich.markdown',
    'rich.progress',
    'pptx',
    'pptx.util',
    'pptx.dml.color',
    'pptx.enum.text',
    'pptx.enum.shapes',
    'tenacity',
    'dotenv',
]

a = Analysis(
    ['slide_creator.py'],
    pathex=[spec_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'tkinter',
        'PIL',
        'cv2',
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
    name='SlideCreator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for CLI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one: icon='icon.ico'
)
