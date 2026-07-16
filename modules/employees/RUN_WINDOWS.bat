@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv || goto :error
)
call ".venv\Scripts\activate.bat"
python -m pip install -r requirements.txt || goto :error
python app.py
goto :eof
:error
echo.
echo Setup or startup failed. Review the error above.
pause
exit /b 1
