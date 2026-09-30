@echo off
title Magnus AI Launcher
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo Magnus AI stopped with an error. Press any key to exit.
    pause >nul
)
