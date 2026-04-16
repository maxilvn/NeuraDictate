@echo off
setlocal enabledelayedexpansion
title NeuraDictate Installer

echo.
echo  ================================
echo    NeuraDictate - Installation
echo  ================================
echo.

:: ---- Check Python, auto-install via winget if missing ----
where python >nul 2>&1
if errorlevel 1 goto install_python
python --version >nul 2>&1
if errorlevel 1 goto install_python
goto python_ready

:install_python
echo  [!] Python nicht gefunden - installiere automatisch...
echo.
where winget >nul 2>&1
if errorlevel 1 (
    echo  [X] winget nicht verfuegbar. Bitte Python manuell installieren:
    echo       https://www.python.org/downloads/
    echo     WICHTIG: "Add Python to PATH" anhaken!
    echo.
    start https://www.python.org/downloads/
    pause
    exit /b 1
)
winget install -e --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
    echo  [X] Python-Installation fehlgeschlagen.
    echo     Bitte manuell installieren: https://www.python.org/downloads/
    pause
    exit /b 1
)
:: Refresh PATH for this session
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
echo  [+] Python installiert

:python_ready
echo  [+] Python bereit
python --version

echo.
echo  [1/4] Installiere Dependencies...
python -m pip install --quiet --upgrade pip >nul 2>&1
python -m pip install --quiet faster-whisper sounddevice numpy pynput pystray Pillow pyperclip pyautogui
if errorlevel 1 (
    echo  [X] Dependency-Installation fehlgeschlagen.
    echo     Pruefe deine Internetverbindung.
    pause
    exit /b 1
)
echo  [+] Dependencies installiert

echo.
echo  [2/4] Lade Whisper Model herunter (ca. 466 MB)...
echo     Dies kann einige Minuten dauern...
python -c "import sys; sys.path.insert(0, '.'); from voice_input.transcriber import download_model; download_model('small')"
echo  [+] Model heruntergeladen

echo.
echo  [3/4] Erstelle Verknuepfungen (Desktop + Startmenue)...
set "PROJ_DIR=%~dp0"
set "PROJ_DIR=%PROJ_DIR:~0,-1%"
set "DESKTOP=%USERPROFILE%\Desktop\NeuraDictate.lnk"
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\NeuraDictate.lnk"

:: Convert PNG icon to ICO for Windows shortcut
powershell -NoProfile -Command ^
  "Add-Type -AssemblyName System.Drawing; ^
   $img = [System.Drawing.Image]::FromFile('%PROJ_DIR%\icon.png'); ^
   $ico = New-Object System.IO.FileStream('%PROJ_DIR%\icon.ico', [System.IO.FileMode]::Create); ^
   $bmp = New-Object System.Drawing.Bitmap($img, 64, 64); ^
   $hicon = $bmp.GetHicon(); ^
   $icon = [System.Drawing.Icon]::FromHandle($hicon); ^
   $icon.Save($ico); ^
   $ico.Close(); $bmp.Dispose(); $img.Dispose()" 2>nul

:: Desktop shortcut
powershell -NoProfile -Command ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%DESKTOP%'); ^
   $s.TargetPath = '%PROJ_DIR%\VoiceInput-Windows.vbs'; ^
   $s.WorkingDirectory = '%PROJ_DIR%'; ^
   $s.IconLocation = '%PROJ_DIR%\icon.ico'; ^
   $s.Description = 'NeuraDictate - Local Speech-to-Text'; ^
   $s.Save()"

:: Start Menu shortcut
powershell -NoProfile -Command ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%STARTMENU%'); ^
   $s.TargetPath = '%PROJ_DIR%\VoiceInput-Windows.vbs'; ^
   $s.WorkingDirectory = '%PROJ_DIR%'; ^
   $s.IconLocation = '%PROJ_DIR%\icon.ico'; ^
   $s.Description = 'NeuraDictate - Local Speech-to-Text'; ^
   $s.Save()"
echo  [+] Verknuepfungen erstellt (Desktop + Startmenue)

echo.
echo  [4/4] Autostart einrichten...
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
powershell -NoProfile -Command ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%STARTUP%\NeuraDictate.lnk'); ^
   $s.TargetPath = '%PROJ_DIR%\VoiceInput-Windows.vbs'; ^
   $s.WorkingDirectory = '%PROJ_DIR%'; ^
   $s.IconLocation = '%PROJ_DIR%\icon.ico'; ^
   $s.Save()"
echo  [+] App startet automatisch bei Windows-Login

echo.
echo  ================================
echo    Installation abgeschlossen!
echo  ================================
echo.
echo  Bedienung:
echo    - Right Alt gedrueckt halten = Aufnahme
echo    - Loslassen = Text wird eingefuegt
echo    - Settings ueber Tray-Icon (unten rechts)
echo.
echo  NeuraDictate startet jetzt...
start "" "%PROJ_DIR%\VoiceInput-Windows.vbs"
timeout /t 3 >nul
exit /b 0
