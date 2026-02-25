@echo off
REM Build script for Windows
REM Run this on a Windows machine with Python installed

echo === Document Generator - Windows Build ===
echo.

REM Check Python
python --version
if errorlevel 1 (
    echo ERROR: Python not found! Install Python 3.10+ first.
    pause
    exit /b 1
)

REM Create virtual environment if not exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

REM Build executable
echo.
echo Building executable...
pyinstaller build_windows.spec --clean

echo.
echo === Build complete! ===
echo Output folder: dist\DocumentGenerator\
echo Executable:    dist\DocumentGenerator\DocumentGenerator.exe
echo.
echo NOTE: Copy the entire dist\DocumentGenerator\ folder to distribute.
echo.
pause
