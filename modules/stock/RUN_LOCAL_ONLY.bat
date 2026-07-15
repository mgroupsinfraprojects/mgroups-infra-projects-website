@echo off
setlocal
cd /d %~dp0
where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
%PY% -m pip install --user -r requirements.txt
if errorlevel 1 (
  echo Install failed.
  pause
  exit /b 1
)
start "" http://127.0.0.1:5000

:START_APP
set MGROUPS_HOST=127.0.0.1
set MGROUPS_PORT=5000
set MGROUPS_DEBUG=0
%PY% app.py
if %errorlevel%==3 (
  echo App restart requested after backup restore. Restarting...
  timeout /t 2 >nul
  goto START_APP
)
pause
