@echo off
setlocal
call "%~dp0LOTUS.bat" %*
exit /b %errorlevel%
