@echo off
rem Builds dist\QuickSpecs.exe - a single file that runs on any Windows PC, no Python needed.
rem Put it on a USB stick and run it on each laptop you sell.
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller pillow
rem The excludes keep the exe small (they're big libraries QuickSpecs doesn't use).
python -m PyInstaller --noconfirm --onefile --console --name QuickSpecs ^
  --exclude-module numpy --exclude-module tkinter --exclude-module PIL.ImageTk --exclude-module PIL.ImageQt ^
  --exclude-module PyQt5 --exclude-module PyQt6 --exclude-module PySide6 ^
  --exclude-module matplotlib --exclude-module scipy --exclude-module pandas ^
  quickspecs.py
echo.
echo Done: %~dp0dist\QuickSpecs.exe
pause
