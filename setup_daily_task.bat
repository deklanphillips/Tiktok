@echo off
REM ============================================================
REM  Run this ONCE to schedule the daily upload.
REM  It creates a Windows task that runs daily_upload.bat every
REM  day at 9:00 AM. Change 09:00 below to any time you want.
REM ============================================================

schtasks /Create /SC DAILY /TN "TikTokToYouTube" /TR "\"%~dp0daily_upload.bat\"" /ST 09:00 /F

echo.
echo Done. The uploader will now run automatically every day at 9:00 AM.
echo Results are written to daily_log.txt in this folder.
echo To stop it later, run remove_daily_task.bat
echo.
pause
