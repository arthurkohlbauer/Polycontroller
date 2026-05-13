@echo off
cd /d "%~dp0"

set PYTHON=
py --version >nul 2>&1
if not errorlevel 1 ( set PYTHON=py & goto :run )
python3 --version >nul 2>&1
if not errorlevel 1 ( set PYTHON=python3 & goto :run )
python --version >nul 2>&1
if not errorlevel 1 ( set PYTHON=python & goto :run )

echo Python not found. Run install.bat first.
pause & exit /b 1

:run
%PYTHON% main.py
if errorlevel 1 ( echo Error - run install.bat & pause )
