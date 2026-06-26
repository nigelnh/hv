@echo off
title HV Pro Terminal Orchestrator (Local Parquet Edition)
color 0B
cls

echo =======================================================================
echo              WELCOM TO HISTORICAL VOLATILITY PRO TERMINAL
echo =======================================================================
echo.

:: Check for virtual environment
if not exist "venv\" (
    echo [WARN] Virtual environment 'venv' not found in this folder!
    echo Creating a new virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment! Please ensure Python is installed.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
    echo.
)

:: Activate virtual environment
echo Activating virtual environment...
call .\venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment!
    pause
    exit /b 1
)
echo [OK] Virtual environment activated.
echo.

:: Install / Update dependencies
echo Checking and installing required packages (this may take a few seconds)...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install requirements! Please check your internet connection.
    pause
    exit /b 1
)
echo [OK] Dependencies are up-to-date.
echo.

:menu
echo =======================================================================
echo   Please select an option to start:
echo =======================================================================
echo   [1] RUN FULL PIPELINE (Fetch data from API, process HV, run UI)
echo   [2] RUN UI ONLY (Fast start - loads dashboard from local Parquet files)
echo   [3] EXIT
echo =======================================================================
echo.

set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" goto pipeline
if "%choice%"=="2" goto ui_only
if "%choice%"=="3" goto end
echo Invalid choice, please try again.
echo.
goto menu

:pipeline
echo.
echo Running full pipeline (Stage 1: API Fetch, Stage 2: Local HV Processing, Stage 3: UI)...
python main.py
goto end

:ui_only
echo.
echo Launching Streamlit UI dashboard directly...
streamlit run ui.py
goto end

:end
echo.
echo Thank you for using HV Pro Terminal!
pause
