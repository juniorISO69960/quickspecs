@echo off
rem Double-click to make a spec sheet for this PC (needs Python installed).
cd /d "%~dp0"
python quickspecs.py %*
if errorlevel 1 pause
