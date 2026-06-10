# -*- mode: python ; coding: utf-8 -*-
import os


block_cipher = None

added_files = [
    ('pygui', 'pygui'),
    ('assets', 'assets'),
    ('Docs', 'Docs'),
    ('LICENSE', '.'),
    ('locales', 'locales'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=['PySide6.QtCore', 'PySide6.QtWidgets', 'PySide6.QtGui', 'PySide6.QtUiTools', 'psutil', 'requests'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6', 'PyQt5'],
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
    name='TailscaleClientPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TailscaleClientPro',
)
app = BUNDLE(
    coll,
    name='TailscaleClientPro.app',
    icon='assets/icon.icns' if os.path.exists('assets/icon.icns') else None,
    bundle_identifier='com.arean82.tailscaleclientpro',
    info_plist={
        'CFBundleShortVersionString': '5.0.0',
        'CFBundleVersion': '5.0.0.0',
        'NSHumanReadableCopyright': 'Copyright (c) 2026 Arean82. All rights reserved.',
        'CFBundleDisplayName': 'Tailscale VPN Client Pro',
    },
)
