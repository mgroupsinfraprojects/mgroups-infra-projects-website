@echo off
setlocal
cd /d %~dp0

echo =====================================================
echo M-Groups Inventory V6.2 - Safe LAN Run
echo =====================================================
echo.

echo Checking Python...
where py >nul 2>nul
if %errorlevel%==0 (
  set PY=py -3
) else (
  set PY=python
)

%PY% --version
if errorlevel 1 (
  echo Python not found. Install Python 3.10+ and tick Add Python to PATH.
  pause
  exit /b 1
)

echo.
echo Installing required packages using python -m pip...
echo This avoids blocked .venv\Scripts\pip.exe on Device Guard PCs.
%PY% -m pip install --user -r requirements.txt
if errorlevel 1 (
  echo.
  echo Package install failed.
  echo Try moving this folder out of Downloads to C:\MGroupsInventory and run again.
  pause
  exit /b 1
)

echo.
echo Allowing Windows Firewall port 5000 if permission is available...
netsh advfirewall firewall add rule name="M-Groups Inventory 5000" dir=in action=allow protocol=TCP localport=5000 >nul 2>nul

echo.
echo Starting M-Groups Inventory V6.2...
echo Local PC: http://127.0.0.1:5000
echo Phone/LAN: open the LAN URL printed by the app below, e.g. http://YOUR-PC-IP:5000
echo.
start "" http://127.0.0.1:5000

:START_APP
set MGROUPS_HOST=0.0.0.0
set MGROUPS_PORT=5000
set MGROUPS_DEBUG=0
%PY% app.py
if %errorlevel%==3 (
  echo.
  echo App restart requested after backup restore. Restarting...
  timeout /t 2 >nul
  goto START_APP
)

echo.
echo App stopped.
pause
