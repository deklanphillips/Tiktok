@echo off
REM Double-click this file to open the TikTok -> YouTube uploader window.
cd /d "%~dp0"
python gui.py
if errorlevel 1 pause
