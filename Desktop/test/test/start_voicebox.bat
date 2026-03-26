@echo off
TITLE Voicebox TTS Server
echo =====================================================
echo  VOICEBOX SERVER LAUNCHER
echo =====================================================

:: Step 1: Switch to voicebox repo
echo [1/3] Navigating to Voicebox repo...
D:
cd /d "D:\voicebox\voicebox"

:: Step 2: Activate conda environment
echo [2/3] Activating 'voicebox' conda environment...
call conda activate voicebox

:: Step 3: Launch the backend server in a separate window
echo [3/3] Starting backend server on 127.0.0.1:17493...
start "Voicebox Backend" python -m backend.server --host 127.0.0.1 --port 17493

:: Step 4: Wait for server to be ready, then preload the model into VRAM
echo.
echo Waiting 10 seconds for server to start...
timeout /t 10 /nobreak > nul

echo Pre-loading 1.7B model into VRAM (prevents first-call timeout)...
python -c "import requests, time; time.sleep(2); r = requests.post('http://127.0.0.1:17493/models/load?model_size=1.7B', timeout=60); print('Model load: ' + r.text)"

echo.
echo =====================================================
echo  SERVER IS READY. You can now run factory_floor.py
echo =====================================================
pause
