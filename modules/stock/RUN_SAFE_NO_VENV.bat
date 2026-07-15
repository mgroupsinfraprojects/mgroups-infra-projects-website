@echo off
setlocal
cd /d %~dp0

echo SAFE MODE: no virtual environment, no pip.exe direct call.
where py >nul 2>nul
if %errorlevel%==0 (
  set PY=py -3
) else (
  set PY=python
)

%PY% -m pip install --user -r requirements.txt
if errorlevel 1 (
  echo Install failed. Move folder to C:\MGroupsInventory and try again.
  pause
  exit /b 1
)
netsh advfirewall firewall add rule name="M-Groups Inventory 5000" dir=in action=allow protocol=TCP localport=5000 >nul 2>nul
start "" http://127.0.0.1:5000

:START_APP
set MGROUPS_HOST=0.0.0.0
set MGROUPS_PORT=5000
set MGROUPS_DEBUG=0
%PY% app.py
if %errorlevel%==3 (
  echo App restart requested. Restarting...
  timeout /t 2 >nul
  goto START_APP
)
pause
