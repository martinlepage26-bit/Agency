@echo off
setlocal
set "TARGET=%~dp0..\scripto\Dr. Sort-Academic Helper.bat"

if exist "%TARGET%" (
    call "%TARGET%" %*
    exit /b %errorlevel%
)

cd /d "%~dp0"
python "%~dp0dr_sort_academic_helper.py" %*
exit /b %errorlevel%
