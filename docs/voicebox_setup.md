# Voicebox Local TTS Integration Guide

This guide provides a complete, one-shot setup for using [voicebox](https://github.com/jamiepine/voicebox) as a local REST API for automated video narration on Windows 11.

---

## A) Setup Steps (Windows 11 + Conda)

Execute these steps in strict order to start the backend server.

1.  **Open Terminal**: Open the **Anaconda Prompt** (miniconda or Anaconda).
2.  **Activate Environment**:
    ```cmd
    conda activate voicebox
    ```
3.  **Navigate to Repo**:
    ```cmd
    cd /d D:\voicebox\voicebox
    ```
4.  **Install Dependencies**:
    ```cmd
    pip install -r backend\requirements.txt
    ```
5.  **Verify CUDA Connectivity**:
    ```cmd
    python -c "import torch; print(f'Torch: {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"NONE\"}')"
    ```
6.  **Start the Backend Server**:
    Run as a module from the repo root:
    ```cmd
    python -m backend.server --host 127.0.0.1 --port 17493 --data-dir "%LOCALAPPDATA%\voicebox-conda"
    ```
7.  **Access API Docs**:
    Open [http://127.0.0.1:17493/docs](http://127.0.0.1:17493/docs) in your browser to view the interactive Swagger documentation.

---

## B) API Intelligence Summary

Voicebox backend uses **FastAPI**. It exposes synchronous and asynchronous endpoints for voice synthesis and model management.

- **Base URL**: `http://127.0.0.1:17493`
- **Key Endpoints**:
    - `GET /health`: Check server status and GPU availability.
    - `POST /models/load?model_size=1.7B`: Manual trigger to load the weights into VRAM.
    - `POST /generate`: The primary TTS trigger. Returns a `generation_id`.
    - `GET /audio/{generation_id}`: Streams the generated WAV file.
    - `GET /profiles`: List available cloned voices.

**Automation Note**: Voicebox requires a `profile_id` (the ID of your cloned Rudra voice) to generate audio. Once you create the Rudra profile in the UI or via API, that ID becomes a persistent constant for your pipeline.

---

## C) Automated Narration Pipeline Sequence

To get `narration.wav` from raw text in your Python pipeline:

1.  **Server Check**: Confirm `GET /health` returns `status: "ok"`.
2.  **Model Loading**: If `model_loaded` is false, call `POST /models/load?model_size=1.7B`.
3.  **Speech Synthesis**:
    - Call `POST /generate` with JSON: `{"text": "...", "profile_id": "YOUR_RUDRA_ID", "language": "en"}`.
    - Store the `generation_id` from the response.
4.  **Download**:
    - Call `GET /audio/{generation_id}`.
    - Save the binary stream directly to `narration.wav`.
5.  **FFmpeg Integration**:
    - Merge with video:
      ```cmd
      ffmpeg -y -i video.mp4 -i narration.wav -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 output_narrated.mp4
      ```

---

## D) Copy/Paste Examples

### 1. CURL Commands (Manual Testing)

**Check Health:**
```cmd
curl http://127.0.0.1:17493/health
```

**Generate Audio:**
```cmd
curl -X POST http://127.0.0.1:17493/generate ^
     -H "Content-Type: application/json" ^
     -d "{\"text\": \"The shadow archive survives.\", \"profile_id\": \"rudra_cloned_id\", \"language\": \"en\"}"
```

### 2. Minimal Python Client

```python
import requests
import os

BASE_URL = "http://127.0.0.1:17493"

def generate_local_narration(text, profile_id, output_path="narration.wav"):
    try:
        # 1. Trigger Generation
        payload = {"text": text, "profile_id": profile_id, "language": "en"}
        resp = requests.post(f"{BASE_URL}/generate", json=payload, timeout=120)
        
        if resp.status_code != 200:
            print(f"❌ Generation failed ({resp.status_code}): {resp.text}")
            return None
            
        gen_id = resp.json().get("generation_id")
        
        # 2. Download File
        audio_resp = requests.get(f"{BASE_URL}/audio/{gen_id}", timeout=60)
        if audio_resp.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(audio_resp.content)
            print(f"✅ Saved to {output_path} ({os.path.getsize(output_path)} bytes)")
            return gen_id
        else:
            print(f"❌ Audio download failed: {audio_resp.status_code}")
            
    except Exception as e:
        print(f"⚠️ Voicebox Error: {e}")
    return None
```

---

## E) Troubleshooting

### 1. Windows Pagefile Error (OS Error 1455)
This occurs when the system runs out of virtual memory while loading the 1.7B parameter model.
- **Fix**: Open **System Properties** > **Advanced** > **Performance Settings** > **Advanced** > **Virtual Memory (Change)**.
- Set a **Custom Size** on your fastest drive (SSD):
  - Initial: 16384 MB (16GB)
  - Maximum: 32768 MB (32GB)
- Restart Windows.

### 2. Port 17493 Already in Use
If the server won't start:
- **Check process**: `netstat -ano | findstr :17493`
- **Kill process**: `taskkill /PID <PID_FROM_PREVIOUS_COMMAND> /F`

### 3. Missing 'sox' or 'flash-attn'
- **sox**: Download `sox` binaries for Windows and add to PATH if audio manipulation errors occur.
- **flash-attn**: Can be ignored on the RTX 4060; it only improves speed at the cost of complex local compilation. Voicebox will fall back to standard attention.
