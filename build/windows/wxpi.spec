# wxPi Windows Packaging Specification
# PyInstaller spec file for building wxPi as a single executable
#
# To build:
#   cd build/windows
#   pyinstaller wxpi.spec
#
# Output will be in build/windows/dist/wxPi/

import sys
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

block_cipher = None

a = Analysis(
    [str(PROJECT_ROOT / 'wxpi' / 'app.py')],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        # Include README for the packaged app
        (str(PROJECT_ROOT / 'README.md'), '.'),
    ],
    hiddenimports=[
        'wx',
        'wx.core',
        'wx.adv',
        'wx.stc',
        'wx.html',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='wxPi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI app, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Could add custom icon later
    version=None,  # Could add version info later
)