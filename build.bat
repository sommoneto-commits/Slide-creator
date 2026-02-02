@echo off
REM Build script for Windows - Creates SlideCreator.exe
REM Run this script from the project root directory

echo ========================================
echo   Slide Creator - Build Script
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ and try again
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Check if .env exists, if not copy from example
if not exist ".env" (
    echo Creating .env from template...
    copy .env.example .env
    echo.
    echo IMPORTANT: Please edit .env and add your OPENAI_API_KEY before running!
    echo.
)

REM Build executable
echo.
echo Building executable...
echo This may take a few minutes...
echo.

pyinstaller slide_creator.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

REM Copy necessary files to dist folder
echo.
echo Copying configuration files...
if not exist "dist\.env" (
    copy .env.example dist\.env.example
)
mkdir dist\output 2>nul
mkdir dist\sessions 2>nul
mkdir dist\logs 2>nul

echo.
echo ========================================
echo   Build completed successfully!
echo ========================================
echo.
echo The executable is located at:
echo   dist\SlideCreator.exe
echo.
echo Before running, make sure to:
echo   1. Copy .env.example to .env in the dist folder
echo   2. Edit .env and add your OPENAI_API_KEY
echo.
echo To run: dist\SlideCreator.exe
echo.

pause
