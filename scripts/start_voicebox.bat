@echo off
TITLE Voicebox TTS Server
SETLOCAL EnableDelayedExpansion

:: --- 1. FIND THE VOICEBOX FOLDER ---
set "VOICEBOX_ROOT="
set "TARGET_FOLDER=voicebox\voicebox"

:: Check common drives for the installation
for %%D in (D C E F G) do (
    if exist "%%D:\!TARGET_FOLDER!" (
        set "VOICEBOX_ROOT=%%D:\!TARGET_FOLDER!"
        goto :FOUND
    )
)

:FOUND
if "%VOICEBOX_ROOT%"=="" (
    echo.
    echo ❌ ERROR: Could not find Voicebox installation at \voicebox\voicebox on any drive.
    pause
    exit /b 1
)

:: --- 2. RUN THE SERVER (THE MANUAL WAY) ---
echo [1/2] Navigating to: %VOICEBOX_ROOT%
cd /d "%VOICEBOX_ROOT%"

echo [2/2] Starting server in a manual window...
:: This opens the server exactly like you do manually. It will NOT close.
start "Voicebox Backend" cmd /k "call conda activate voicebox && python -m backend.server --host 127.0.0.1 --port 17493"

echo.
echo =====================================================
echo  SERVER LAUNCHED IN A NEW WINDOW.
echo  The server handles model loading automatically.
echo =====================================================
timeout /t 3 > nul
exit
