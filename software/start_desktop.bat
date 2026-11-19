@echo off
cd /d "%~dp0"
title RiverTemp-Reconstructor
echo.
echo Starting RiverTemp-Reconstructor (Python 3.11)...
echo.

set "PY=py -3.11"

%PY% -c "import sys" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.11 not found. Install from https://www.python.org/downloads/
    echo         During install, check "Add python.exe to PATH".
    pause
    exit /b 1
)

%PY% -c "import PyQt5" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies, please wait...
    %PY% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] pip install failed.
        pause
        exit /b 1
    )
)

%PY% app.py
if errorlevel 1 (
    echo.
    echo [ERROR] App exited with error. See startup_error.log
    echo.
    pause
)
