@echo off
setlocal
set "TARGET=%~dp0..\lotus\LOTUS.bat"

if exist "%TARGET%" (
    call "%TARGET%" %*
    exit /b %errorlevel%
)

cd /d "%~dp0"
python "%~dp0lotus_app.py" %*
exit /b %errorlevel%
