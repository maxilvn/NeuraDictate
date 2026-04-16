# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for NeuraDictate

import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_all

block_cipher = None

hidden = [
    'voice_input',
    'voice_input.app',
    'voice_input.config',
    'voice_input.recorder',
    'voice_input.transcriber',
    'voice_input.settings_window',
    'voice_input.hotkey',
    'voice_input.hud',
    'voice_input.tray',
    'voice_input.clipboard',
    'sounddevice',
    'numpy',
    'json',
    'threading',
    'subprocess',
    'tempfile',
    'pathlib',
    'tkinter',
    'tkinter.ttk',
    'tkinter.scrolledtext',
]

datas = [
    ('icon.png', '.'),
    ('logo.png', '.'),
]

# Collect EVERYTHING for critical packages (modules + data + binaries)
binaries = []
for pkg in ['faster_whisper', 'ctranslate2', 'tokenizers', 'huggingface_hub']:
    try:
        _d, _b, _h = collect_all(pkg)
        datas += _d
        binaries += _b
        hidden += _h
    except Exception:
        pass

# Also collect voice_input submodules (ensure they're all picked up)
hidden += collect_submodules('voice_input')

# Platform-specific hidden imports
if sys.platform == 'darwin':
    hidden += [
        'rumps', 'Quartz', 'AppKit', 'Foundation', 'PyObjCTools',
        'PyObjCTools.AppHelper',
        'objc',
    ]
    hidden += collect_submodules('Quartz')
    hidden += collect_submodules('AppKit')
elif sys.platform == 'win32':
    for pkg in ['pynput', 'pystray', 'PIL', 'pyperclip', 'pyautogui']:
        try:
            _d, _b, _h = collect_all(pkg)
            datas += _d
            binaries += _b
            hidden += _h
        except Exception:
            pass

a = Analysis(
    ['start.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'pandas', 'IPython', 'jupyter'],
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
    name='NeuraDictate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.icns' if sys.platform == 'darwin' else 'icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='NeuraDictate',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='NeuraDictate.app',
        icon='icon.icns',
        bundle_identifier='com.neura.dictate',
        version='1.0',
        info_plist={
            'CFBundleShortVersionString': '1.0',
            'CFBundleVersion': '1.0',
            'LSMinimumSystemVersion': '10.13',
            'LSUIElement': True,  # Menu-bar only, no dock icon
            'NSHighResolutionCapable': True,
            'NSMicrophoneUsageDescription':
                'NeuraDictate needs microphone access to transcribe your speech.',
            'NSAppleEventsUsageDescription':
                'NeuraDictate uses AppleScript to paste transcribed text.',
        },
    )
