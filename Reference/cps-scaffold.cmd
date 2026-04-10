@echo off
REM ==========================================================================
REM  cps-scaffold.cmd  -  Double-click launcher for cps-scaffold.ps1
REM
REM  Runs the sibling cps-scaffold.ps1 with ExecutionPolicy Bypass (no need to
REM  unblock), targeting the folder this .cmd lives in. Pauses at the end so
REM  the console window stays open for you to read the outcome table.
REM
REM  Drop both files (this .cmd and cps-scaffold.ps1) into any project folder
REM  and double-click this file.
REM ==========================================================================

setlocal
cd /d "%~dp0"

if not exist "%~dp0cps-scaffold.ps1" (
    echo.
    echo ERROR: cps-scaffold.ps1 not found next to this launcher.
    echo Expected: %~dp0cps-scaffold.ps1
    echo.
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0cps-scaffold.ps1"
set RC=%ERRORLEVEL%

echo.
if %RC% EQU 0 (
    echo [cps-scaffold] Done.
) else (
    echo [cps-scaffold] Exited with code %RC%.
)
echo.
pause
endlocal
