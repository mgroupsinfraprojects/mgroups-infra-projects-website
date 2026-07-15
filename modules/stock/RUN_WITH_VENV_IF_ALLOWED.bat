@echo off
setlocal
cd /d %~dp0

where py >nul 2>nul
if %errorlevel%==0 (
  set PY=py -3
) else (
  set PY=python
)

if not exist .venv (
  %PY% -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo VENV install failed. Use RUN_SAFE_NO_VENV.bat instead.
  pause
  exit /b 1
)
start "" http://127.0.0.1:5000

:START_APP
set MGROUPS_HOST=0.0.0.0
set MGROUPS_PORT=5000
set MGROUPS_DEBUG=0
python app.py
if %errorlevel%==3 (
  echo App restart requested after backup restore. Restarting...
  timeout /t 2 >nul
  goto START_APP
)
pause
