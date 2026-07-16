@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title GST Audit Pro - Web Mode

echo ============================================================
echo  GST Audit Pro v11.13.0 - Browser/Web Mode
echo ============================================================
echo.

set "VENV_DIR=.venv-web"
set "PYTHON_CMD="

if exist "%VENV_DIR%\Scripts\python.exe" (
    set "PYTHON_CMD=%VENV_DIR%\Scripts\python.exe"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3.11 -c "import sys; raise SystemExit(0 if (3,11) <= sys.version_info[:2] < (3,13) else 1)" >nul 2>nul
        if not errorlevel 1 set "PYTHON_CMD=py -3.11"
        if not defined PYTHON_CMD (
            py -3.12 -c "import sys; raise SystemExit(0 if (3,11) <= sys.version_info[:2] < (3,13) else 1)" >nul 2>nul
            if not errorlevel 1 set "PYTHON_CMD=py -3.12"
        )
    )
    if not defined PYTHON_CMD (
        where python >nul 2>nul
        if not errorlevel 1 (
            python -c "import sys; raise SystemExit(0 if (3,11) <= sys.version_info[:2] < (3,13) else 1)" >nul 2>nul
            if not errorlevel 1 set "PYTHON_CMD=python"
        )
    )
)

if not defined PYTHON_CMD (
    echo [ERROR] Python 3.11 or 3.12 was not found.
    echo Install Python 3.11 or 3.12 from python.org and tick "Add Python to PATH".
    pause
    exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [1/4] Creating web virtual environment...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 goto :fail
)

set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

echo [2/4] Installing web/runtime dependencies...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%PYTHON_EXE%" -m pip install -r requirements-web.txt
if errorlevel 1 goto :fail

echo [3/4] Running core smoke test...
"%PYTHON_EXE%" scripts\smoke_test_processor.py --self-check
if errorlevel 1 goto :fail

echo [4/4] Starting web mode at http://127.0.0.1:8088
start "" "%PYTHON_EXE%" web_portal\open_browser_later.py http://127.0.0.1:8088 2
"%PYTHON_EXE%" web_app.py --host 127.0.0.1 --port 8088
exit /b %ERRORLEVEL%

:fail
echo.
echo [ERROR] Web mode setup/start failed. Read the message above.
pause
exit /b 1
