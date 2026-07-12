@echo off
REM ============================================================
REM  AUTOMATION FACTORY - Workbench (Web GUI)
REM  Fast launcher. First-time setup: run install.bat once.
REM ============================================================

setlocal
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"

echo === AUTOMATION FACTORY - Workbench ===
echo.

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" goto NOSETUP

"%PY%" "05_SCRIPTS\factory_web.py"
if errorlevel 1 goto ERR
goto END

:NOSETUP
echo [INFO] Environment not set up yet - running install.bat first...
echo.
call install.bat
if not exist "%PY%" goto END
"%PY%" "05_SCRIPTS\factory_web.py"
if errorlevel 1 goto ERR
goto END

:ERR
echo.
echo [ERROR] The program exited with an error - see the messages above.

:END
echo.
pause
