@echo off
echo ============================================
echo  polycontroller -- Dependency Installer
echo ============================================
echo.

:: Detect working Python command (py launcher first, avoids Windows Store stub)
set PYTHON=
py --version >nul 2>&1
if not errorlevel 1 ( set PYTHON=py & goto :found )

python3 --version >nul 2>&1
if not errorlevel 1 ( set PYTHON=python3 & goto :found )

python --version >nul 2>&1
if not errorlevel 1 ( set PYTHON=python & goto :found )

echo ERROR: Python not found.
echo Install Python from https://python.org and check "Add to PATH" during setup.
echo If Python is already installed, open the Start menu, search "Manage App
echo Execution Aliases" and disable the Python Store entries.
pause
exit /b 1

:found
echo Python command : %PYTHON%
%PYTHON% --version
echo.

:: pygame and pygame-ce cannot coexist -- remove pygame if present
echo Removing old pygame (if installed)...
%PYTHON% -m pip uninstall pygame -y >nul 2>&1

echo Installing dependencies...
%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed. Check the output above.
    pause
    exit /b 1
)

echo.
echo Done! Run start.bat to launch polycontroller.
pause
