@echo off
REM Run this to turn OFF the daily automatic upload.
schtasks /Delete /TN "TikTokToYouTube" /F
echo.
echo The daily uploader has been turned off.
echo.
pause
