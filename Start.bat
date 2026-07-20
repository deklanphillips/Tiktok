@echo off
REM Opens the app. Launches with pythonw (no console) and closes this window.
cd /d "%~dp0"
start "" pythonw gui.py
exit
