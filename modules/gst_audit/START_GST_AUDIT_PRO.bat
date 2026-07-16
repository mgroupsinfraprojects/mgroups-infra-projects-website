@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title GST Audit Pro - One Click Launcher

echo ============================================================
echo  GST Audit Pro v11.13.0 - Easy Workflow Launcher
echo ============================================================
echo.

set "VENV_DIR=.venv"
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
    echo Install Python 3.11 or 3.12 from python.org, tick "Add python.exe to PATH", then run START_GST_AUDIT_PRO.bat again.
    pause
    exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [1/4] Creating local virtual environment...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 goto :fail
)

set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

"%PYTHON_EXE%" -c "import PySide6, pandas, openpyxl, xlsxwriter, cryptography, xlrd" >nul 2>nul
if errorlevel 1 (
    echo [2/4] Installing missing required packages...
    "%PYTHON_EXE%" -m pip install --upgrade pip
    if errorlevel 1 goto :fail
    "%PYTHON_EXE%" -m pip install -r requirements.txt
    if errorlevel 1 goto :fail
) else (
    echo [2/4] Required packages already available.
)

echo [3/4] Running startup preflight...
"%PYTHON_EXE%" scripts\preflight_windows.py
if errorlevel 1 goto :fail

echo [4/4] Opening GST Audit Pro...
"%PYTHON_EXE%" main.py
set "APP_EXIT=%ERRORLEVEL%"
if not "%APP_EXIT%"=="0" (
    echo.
    echo [ERROR] Application closed with error code %APP_EXIT%.
    pause
    exit /b %APP_EXIT%
)
exit /b 0

:fail
echo.
echo [ERROR] Setup or startup failed. Read the message above.
echo Recommended diagnostic command: .venv\Scripts\python.exe scripts\preflight_windows.py
pause
exit /b 1
