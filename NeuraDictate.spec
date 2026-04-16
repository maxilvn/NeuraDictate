# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for NeuraDictate

import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

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

# faster-whisper needs ctranslate2 and tokenizers — collect submodules
hidden += collect_submodules('faster_whisper')
hidden += collect_submodules('ctranslate2')
hidden += collect_submodules('tokenizers')
hidden += collect_submodules('huggingface_hub')

datas = [
    ('icon.png', '.'),
    ('logo.png', '.'),
]

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
    hidden += [
        'pynput', 'pynput.keyboard', 'pynput.mouse',
        'pystray', 'PIL', 'PIL.Image', 'PIL.ImageDraw',
        'pyperclip', 'pyautogui',
    ]
    hidden += collect_submodules('pynput')
    hidden += collect_submodules('pystray')

a = Analysis(
    ['start.py'],
    pathex=['.'],
    binaries=[],
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
