@echo off
setlocal
cd /d "%~dp0"

set "LOCAL_PYTHON=%~dp0.venv\Scripts\python.exe"

if exist "%LOCAL_PYTHON%" (
    "%LOCAL_PYTHON%" "%~dp0agency_lotus_app.py" %*
    exit /b %errorlevel%
)

where py >nul 2>nul
if %errorlevel%==0 (
    py "%~dp0agency_lotus_app.py" %*
    exit /b %errorlevel%
)

python "%~dp0agency_lotus_app.py" %*
exit /b %errorlevel%
