@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title GST Audit Pro v11.13.0 - Windows EXE Build Gate

echo ============================================================
echo  GST Audit Pro v11.13.0 - Windows EXE Build Gate
echo ============================================================
echo.

set "BUILD_VENV=.venv-build"
set "PYTHON_EXE=%BUILD_VENV%\Scripts\python.exe"

echo [1/7] Creating isolated build virtual environment if needed...
if not exist "%PYTHON_EXE%" (
    py -3.11 -m venv "%BUILD_VENV%"
    if errorlevel 1 py -3.12 -m venv "%BUILD_VENV%"
    if errorlevel 1 python -m venv "%BUILD_VENV%"
    if errorlevel 1 goto :fail
)

echo [2/7] Installing build and runtime dependencies...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%PYTHON_EXE%" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :fail

echo [3/7] Running source release gate...
"%PYTHON_EXE%" scripts\dev.py release-check
if errorlevel 1 goto :fail

echo [4/7] Running full regression suite...
"%PYTHON_EXE%" -m pytest --no-cov
if errorlevel 1 goto :fail

echo [5/7] Running Windows preflight and GUI smoke test...
"%PYTHON_EXE%" scripts\preflight_windows.py
if errorlevel 1 goto :fail
"%PYTHON_EXE%" scripts\gui_smoke_test.py
if errorlevel 1 goto :fail

echo [6/7] Building Windows application folder...
"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean GSTInvoiceAudit.spec
if errorlevel 1 goto :fail

echo [7/7] Verifying EXE output...
if not exist "dist\GSTInvoiceAudit\GSTInvoiceAudit.exe" (
    echo [ERROR] EXE build failed: output file not found.
    goto :fail
)
dir "dist\GSTInvoiceAudit\GSTInvoiceAudit.exe"

echo.
echo Build successful: dist\GSTInvoiceAudit\GSTInvoiceAudit.exe
echo Manual final check: open EXE, upload sample_data files, process, review, export, close, reopen.
echo Signing stage: sign the EXE/installer before client delivery.
pause
exit /b 0

:fail
echo.
echo [ERROR] EXE build gate failed. Do not distribute this build.
pause
exit /b 1
