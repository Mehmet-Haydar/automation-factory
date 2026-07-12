@echo off
REM ============================================================
REM  AUTOMATION FACTORY - one-time setup
REM  Run this ONCE after unpacking. Afterwards use start.bat.
REM
REM  Needs: Python 3.10+  (https://www.python.org/downloads/)
REM         internet access (downloads Python packages)
REM ============================================================

setlocal
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"

echo === AUTOMATION FACTORY - Setup ===
echo.

REM -- 1. Python present? -----------------------------------------
python --version >nul 2>&1
if errorlevel 1 goto NOPYTHON
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% found.

REM -- 2. Create venv (skip if it already exists) -----------------
if exist ".venv\Scripts\python.exe" (
    echo [OK] .venv already exists - reusing it.
) else (
    echo [..] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 goto ERR
)

REM -- 3. Install dependencies ------------------------------------
echo [..] Installing dependencies (a few minutes on first run)...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto ERR

REM -- 4. Smoke check ---------------------------------------------
".venv\Scripts\python.exe" -c "import webview, yaml, pdfplumber" >nul 2>&1
if errorlevel 1 goto ERR

echo.
echo [DONE] Setup complete. Double-click start.bat to launch the GUI.
goto END

:NOPYTHON
echo.
echo [ERROR] Python was not found on this computer.
echo.
echo   1. Install Python 3.10 or newer:  https://www.python.org/downloads/
echo   2. IMPORTANT: tick "Add python.exe to PATH" in the installer.
echo   3. Run install.bat again.
echo.
echo   Details: INSTALLATION.md
goto END

:ERR
echo.
echo [ERROR] Setup failed - see the messages above. Details: INSTALLATION.md

:END
echo.
pause
