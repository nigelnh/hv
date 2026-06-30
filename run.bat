@echo off
title HV Pro Terminal Orchestrator (Node & React Edition)
color 0B
cls

echo =======================================================================
echo              WELCOME TO HISTORICAL VOLATILITY PRO TERMINAL
echo =======================================================================
echo.

:: Check for node_modules
if not exist "node_modules\" (
    echo [WARN] node_modules folder not found!
    echo Installing npm dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install packages! Please ensure Node.js is installed.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed.
    echo.
)

:menu
echo =======================================================================
echo   Please select an option to start:
echo =======================================================================
echo   [1] RUN FULL PIPELINE (Fetch SSI API data, process HVs, start UI)
echo   [2] RUN UI ONLY (Fast start - launches React dashboard using cached JSON)
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
echo Running full pipeline (Stage 1: API Fetch, Stage 2: Local HV Processing)...
call node pipeline.js
if errorlevel 1 (
    echo [ERROR] Data pipeline execution failed!
    pause
    exit /b 1
)
echo.
echo Launching React/Vite UI dashboard...
call npm run dev
goto end

:ui_only
echo.
echo Launching React/Vite UI dashboard directly...
call npm run dev
goto end

:end
echo.
echo Thank you for using HV Pro Terminal!
pause

