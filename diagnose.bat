@echo off
echo ============================================
echo  polycontroller -- Controller Diagnostic
echo ============================================
echo  Move sticks, press throttle, brake, etc.
echo  Watch which axes/buttons change.
echo  Ctrl+C to quit.
echo ============================================
echo.

cd /d "%~dp0"

set PYTHON=
py --version >nul 2>&1
if not errorlevel 1 ( set PYTHON=py & goto :run )
python3 --version >nul 2>&1
if not errorlevel 1 ( set PYTHON=python3 & goto :run )
python --version >nul 2>&1
if not errorlevel 1 ( set PYTHON=python & goto :run )

echo ERROR: Python not found. Run install.bat first.
pause
exit /b 1

:run
%PYTHON% diagnose.py
pause
