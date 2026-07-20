@echo off
REM ============================================================
REM  Daily auto-upload job (run by Windows Task Scheduler).
REM  Uploads the next 6 NEW videos from your profile to YouTube.
REM  Duplicate protection means it never re-does old ones.
REM
REM  EDIT the two values below if your profile or hashtags change.
REM ============================================================

set PROFILE=https://www.tiktok.com/@notbliqy
set HASHTAGS=#gtastorymode #gta #memes #gtav #funny #gtamemes #gta6

cd /d "%~dp0"
REM Never pop a browser during an unattended run — fail with a clear log instead.
set TIKTOK_NONINTERACTIVE=1
echo ==== Run started %DATE% %TIME% ==== >> daily_log.txt
python tiktok_to_youtube.py "%PROFILE%" --limit 6 --hashtags "%HASHTAGS%" >> daily_log.txt 2>&1
echo ==== Run finished %DATE% %TIME% ==== >> daily_log.txt
echo. >> daily_log.txt
