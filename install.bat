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
where winget >nul 2>&1
if errorlevel 1 (
    echo  [X] winget nicht verfuegbar. Bitte Python manuell installieren:
    echo       https://www.python.org/downloads/
    echo     WICHTIG: "Add Python to PATH" anhaken!
    start https://www.python.org/downloads/
    pause
    exit /b 1
)
winget install -e --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
    echo  [X] Python-Installation fehlgeschlagen.
    pause
    exit /b 1
)
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
echo  [+] Python installiert

:python_ready
echo  [+] Python bereit
python --version

echo.
echo  [1/5] Installiere Dependencies...
python -m pip install --quiet --upgrade pip >nul 2>&1
python -m pip install --quiet faster-whisper sounddevice numpy pynput pystray Pillow pyperclip pyautogui
if errorlevel 1 (
    echo  [X] Dependency-Installation fehlgeschlagen.
    pause
    exit /b 1
)
echo  [+] Dependencies installiert

echo.
echo  [2/5] Lade Whisper Model herunter (ca. 466 MB)...
python -c "import sys; sys.path.insert(0, '.'); from voice_input.transcriber import download_model; download_model('small')"
echo  [+] Model heruntergeladen

echo.
echo  [3/5] Installiere NeuraDictate nach %%LOCALAPPDATA%%\NeuraDictate...
set "PROJ_DIR=%~dp0"
set "PROJ_DIR=%PROJ_DIR:~0,-1%"
set "INSTALL_DIR=%LOCALAPPDATA%\NeuraDictate"

if exist "%INSTALL_DIR%" rmdir /S /Q "%INSTALL_DIR%"
mkdir "%INSTALL_DIR%"
xcopy /E /I /Q /Y "%PROJ_DIR%\voice_input" "%INSTALL_DIR%\voice_input" >nul
copy /Y "%PROJ_DIR%\start.py" "%INSTALL_DIR%\start.py" >nul
copy /Y "%PROJ_DIR%\icon.png" "%INSTALL_DIR%\icon.png" >nul
copy /Y "%PROJ_DIR%\logo.png" "%INSTALL_DIR%\logo.png" >nul

:: Create NeuraDictate.vbs (silent launcher, no console window)
(
echo Set fso = CreateObject^("Scripting.FileSystemObject"^)
echo dir = fso.GetParentFolderName^(WScript.ScriptFullName^)
echo Set shell = CreateObject^("WScript.Shell"^)
echo shell.CurrentDirectory = dir
echo shell.Run "pythonw """ ^& dir ^& "\start.py""", 0, False
) > "%INSTALL_DIR%\NeuraDictate.vbs"

:: Convert PNG to ICO
powershell -NoProfile -Command ^
  "Add-Type -AssemblyName System.Drawing; ^
   $img = [System.Drawing.Image]::FromFile('%INSTALL_DIR%\icon.png'); ^
   $bmp = New-Object System.Drawing.Bitmap($img, 64, 64); ^
   $hicon = $bmp.GetHicon(); ^
   $icon = [System.Drawing.Icon]::FromHandle($hicon); ^
   $fs = New-Object System.IO.FileStream('%INSTALL_DIR%\icon.ico', [System.IO.FileMode]::Create); ^
   $icon.Save($fs); $fs.Close(); $bmp.Dispose(); $img.Dispose()" 2>nul

echo  [+] Installiert nach %INSTALL_DIR%

echo.
echo  [4/5] Erstelle Verknuepfungen...
set "DESKTOP=%USERPROFILE%\Desktop\NeuraDictate.lnk"
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\NeuraDictate.lnk"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\NeuraDictate.lnk"

for %%T in ("%DESKTOP%" "%STARTMENU%" "%STARTUP%") do (
    powershell -NoProfile -Command ^
      "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%%~T'); ^
       $s.TargetPath = '%INSTALL_DIR%\NeuraDictate.vbs'; ^
       $s.WorkingDirectory = '%INSTALL_DIR%'; ^
       $s.IconLocation = '%INSTALL_DIR%\icon.ico'; ^
       $s.Description = 'NeuraDictate - Local Speech-to-Text'; ^
       $s.Save()"
)
echo  [+] Desktop + Startmenue + Autostart eingerichtet

echo.
echo  [5/5] Starte NeuraDictate...
start "" "%INSTALL_DIR%\NeuraDictate.vbs"

echo.
echo  ================================
echo    Installation abgeschlossen!
echo  ================================
echo.
echo  Die App ist installiert in: %INSTALL_DIR%
echo  Du kannst diesen Download-Ordner loeschen.
echo.
echo  Starten:
echo    - Desktop-Verknuepfung NeuraDictate
echo    - Startmenue: NeuraDictate
echo    - Taskbar-Icon (unten rechts)
echo.
timeout /t 3 >nul
exit /b 0
