# 🚀 N8N Workflow Guide — Lofi Video Automation (Full Cloud Deployment)

> **Goal**: Transform the existing Python pipeline into a 24/7 n8n workflow running on a cloud VM.  
> **Trigger**: WhatsApp message (via Twilio) → **Output**: Uploaded TikTok video.

---

## 📐 Architecture Overview

```mermaid
graph TD
    A["📱 WhatsApp Message (Twilio)"] --> B["⚡ Twilio Trigger Node"]
    B --> C["🧹 Set Node (Topic)"]
    C --> D["🧠 OpenRouter LLM Node"]
    C --> D["🎙️ ElevenLabs Voice (HTTP Request)"]
    C --> E["🎬 Meta AI Video (FastAPI)"]
    D --> F["🎵 FFmpeg Fusion (FastAPI)"]
    E --> F
    F --> G["📤 TikTok Upload Node"]
    G --> H["📱 WhatsApp Reply (Twilio)"]
    
    style E fill:#ff9800,color:#000
    style F fill:#ff9800,color:#000
```

> [!IMPORTANT]
> **Key Design Decision**: Since n8n no longer has an "Execute Command" node, all Python scripts (`video.py`, `addMusic.py`) are wrapped in a **FastAPI server** running on the same VM. n8n calls them via **HTTP Request** nodes to `http://localhost:8000`.

**Flow Summary**:
1. User sends a topic via WhatsApp
2. Twilio forwards the message to n8n via webhook
3. n8n orchestrates: LLM → Voice + Video (parallel) → Audio/Video Fusion → TikTok Upload
4. n8n sends a confirmation back to WhatsApp

---

## 🛠️ Part 1 — Cloud VM Setup

### Step 1.1 — Provision a VPS

Choose a provider (recommended: **Hetzner**, **DigitalOcean**, or **Contabo**).

| Spec | Minimum | Recommended |
|------|---------|-------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Disk | 40 GB SSD | 80 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

> [!IMPORTANT]
> Video processing with FFmpeg/MoviePy is CPU-heavy. Don't go below 4 GB RAM.

### Step 1.2 — Install System Dependencies

SSH into your VM and ensure you have these installed (skip anything you already have):

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install FFmpeg (required for audio/video processing)
sudo apt install -y ffmpeg

# Install Python 3.11+ and pip
sudo apt install -y python3 python3-pip python3-venv
```

> [!NOTE]
> You already have **n8n installed via npm** and **Node.js** on your VM — no need to reinstall those.

### Step 1.3 — n8n (Already Installed ✅)

You already have n8n running via npm. Just make sure it's configured to accept webhooks:

```bash
# Set the public webhook URL so Twilio can reach your n8n instance
export WEBHOOK_URL=https://n8n.yourdomain.com/

# If not already running, start n8n
n8n start

# Or to run it in the background with auto-restart:
npx pm2 start n8n -- start
```

> [!TIP]
> Use **pm2** (`npm install -g pm2`) to keep n8n running 24/7 and auto-restart on crash:
> ```bash
> pm2 start n8n -- start
> pm2 save
> pm2 startup  # generates a system service for boot persistence
> ```
>
> Twilio needs a publicly accessible **HTTPS** URL. Use **Caddy** or **Nginx** as a reverse proxy with Let's Encrypt for free SSL.

### Step 1.4 — Set Up Reverse Proxy with Caddy (for HTTPS)

```bash
# Install Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy

# Create Caddyfile
sudo tee /etc/caddy/Caddyfile <<EOF
n8n.yourdomain.com {
    reverse_proxy localhost:5678
}
EOF

# Restart Caddy
sudo systemctl restart caddy
```

Point your domain's DNS A record to the VM's public IP. Caddy auto-provisions SSL.

### Step 1.5 — Set Up the Pipeline on the VM (No Git — Just Copy-Paste)

**Run these commands first** to create the folder and install dependencies:

```bash
# Create project folder and subdirectories
sudo mkdir -p ~/content-automation/{outputs,final_videos,music}

# Create virtual environment
cd ~/content-automation
python3 -m venv venv
source venv/bin/activate

# Install ALL Python dependencies
pip install meta-ai-api requests moviepy python-dotenv elevenlabs fastapi uvicorn
```

Now you need to create **4 files** on the VM. Use `nano` (or any editor) to create each one and paste the code.

---

#### 📄 File 1: `~/content-automation/video.py`

```bash
nano ~/content-automation/video.py
```

Paste the **entire contents** of your local `video.py` file from this project.

> [!CAUTION]
> Before pasting, update the **cookies** dict at the top of `video.py` with fresh Meta AI session cookies. Also change the hardcoded `C:\ffmpeg\bin` path to just remove it (FFmpeg is in PATH on Linux). See Part 6 for cookie maintenance.

---

#### 📄 File 2: `~/content-automation/voice_engine.py`

```bash
nano ~/content-automation/voice_engine.py
```

Paste the **entire contents** of your local `voice_engine.py` file.

> [!NOTE]
> Remove or change the line `os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"` — that's Windows-only. On Linux, FFmpeg is already in PATH after `apt install ffmpeg`.

---

#### 📄 File 3: `~/content-automation/addMusic.py`

```bash
nano ~/content-automation/addMusic.py
```

Paste the **entire contents** of your local `addMusic.py` file.

> Same note: remove the `C:\ffmpeg\bin` PATH line.

---

#### 📄 File 4: `~/content-automation/api_server.py` ⭐ NEW

This is the FastAPI wrapper that lets n8n call your Python scripts via HTTP (since n8n removed the Execute Command node).

```bash
nano ~/content-automation/api_server.py
```

Paste this:

```python
"""
FastAPI wrapper for the Lofi Video Pipeline.
Exposes the Python scripts as HTTP endpoints so n8n can call them.

Run with: uvicorn api_server:app --host 0.0.0.0 --port 8000
"""

import os
import sys
import json
import glob
import subprocess
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Ensure FFmpeg is in PATH
os.environ["PATH"] += os.pathsep + "/usr/bin"

app = FastAPI(title="Lofi Pipeline API")

# -------------------------------------------------------------------
# Request Models
# -------------------------------------------------------------------
class VideoRequest(BaseModel):
    prompt: str

class FusionRequest(BaseModel):
    video_path: str
    voice_path: str = None
    output_name: str = "final_output.mp4"

class CleanupRequest(BaseModel):
    max_age_minutes: int = 1440  # 24 hours

# -------------------------------------------------------------------
# Endpoint 1: Generate Video via Meta AI
# -------------------------------------------------------------------
@app.post("/generate-video")
def generate_video(req: VideoRequest):
    """Runs video.py with the given prompt. Returns path to generated video."""
    try:
        cmd = [
            sys.executable, "video.py",
            "--prompt", req.prompt
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout
            cwd="~/content-automation"
        )

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"video.py failed: {result.stderr}"
            )

        # Find the latest generated video
        videos = sorted(
            glob.glob("~/content-automation/outputs/*.mp4"),
            key=os.path.getmtime,
            reverse=True
        )

        if not videos:
            raise HTTPException(status_code=404, detail="No video files generated")

        return {
            "status": "success",
            "video_path": videos[0],
            "stdout": result.stdout
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Video generation timed out (5 min)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------------
# Endpoint 2: Music Fusion + Ping-Pong Loop
# -------------------------------------------------------------------
@app.post("/fuse-video")
def fuse_video(req: FusionRequest):
    """Runs addMusic.py to merge music, voice, and apply ping-pong looping."""
    output_path = f"~/content-automation/final_videos/{req.output_name}"
    Path("~/content-automation/final_videos").mkdir(exist_ok=True)

    try:
        cmd = [
            sys.executable, "addMusic.py",
            "--video", req.video_path,
            "--music", "music",
            "--output", output_path
        ]
        if req.voice_path:
            cmd.extend(["--voice", req.voice_path])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd="~/content-automation"
        )

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"addMusic.py failed: {result.stderr}"
            )

        return {
            "status": "success",
            "final_video_path": output_path,
            "stdout": result.stdout
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Fusion timed out (5 min)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------------
# Endpoint 3: Download final video (for TikTok upload)
# -------------------------------------------------------------------
@app.get("/download/{filename}")
def download_video(filename: str):
    """Returns the final video file as a downloadable response."""
    filepath = f"~/content-automation/final_videos/{filename}"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath, media_type="video/mp4", filename=filename)

# -------------------------------------------------------------------
# Endpoint 4: Cleanup old files
# -------------------------------------------------------------------
@app.post("/cleanup")
def cleanup(req: CleanupRequest):
    """Deletes video/audio files older than max_age_minutes."""
    import time
    now = time.time()
    cutoff = now - (req.max_age_minutes * 60)
    deleted = []

    for pattern in [
        "~/content-automation/outputs/*.mp4",
        "~/content-automation/final_videos/*.mp4",
        "~/content-automation/voice_*.mp3"
    ]:
        for f in glob.glob(pattern):
            if os.path.getmtime(f) < cutoff:
                os.remove(f)
                deleted.append(f)

    return {"status": "success", "deleted_count": len(deleted), "deleted": deleted}

# -------------------------------------------------------------------
# Health check
# -------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
```

**Start the FastAPI server** (run alongside n8n):

```bash
cd ~/content-automation
source venv/bin/activate
uvicorn api_server:app --host 127.0.0.1 --port 8000
```

> [!IMPORTANT]
> Bind to `127.0.0.1` (not `0.0.0.0`) so the API is only accessible from the VM itself — n8n calls it locally, and it's never exposed to the internet.

**Keep it running 24/7 with pm2**:

```bash
# Using pm2 (best option — manages both n8n and the API)
pm2 start "cd ~/content-automation && source venv/bin/activate && uvicorn api_server:app --host 127.0.0.1 --port 8000" --name lofi-api
pm2 save
```

Or with a **systemd service** (alternative):

```bash
sudo tee /etc/systemd/system/lofi-api.service <<EOF
[Unit]
Description=Lofi Pipeline FastAPI Server
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=/home/azureuser/content-automation
ExecStart=/home/azureuser/content-automation/venv/bin/uvicorn api_server:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable lofi-api
sudo systemctl start lofi-api
```

---

## 📱 Part 2 — Twilio WhatsApp Setup (Trigger)

### Step 2.1 — Create a Twilio Account

1. Sign up at [twilio.com](https://www.twilio.com/)
2. Go to **Messaging → Try it out → Send a WhatsApp message**
3. Follow the sandbox setup: Send `join <your-sandbox-word>` to Twilio's WhatsApp number
4. Note your:
   - **Account SID**
   - **Auth Token**
   - **WhatsApp Sandbox Number** (e.g., `whatsapp:+14155238886`)

### Step 2.2 — Configure Twilio Webhook

1. In Twilio Console → **Messaging → Settings → WhatsApp Sandbox Settings**
2. Set **"When a message comes in"** URL to:
   ```
   https://n8n.yourdomain.com/webhook/whatsapp-lofi
   ```
3. Method: **POST**

---

## 🔗 Part 3 — Building the n8n Workflow (Node by Node)

Open n8n at `https://n8n.yourdomain.com` and create a new workflow.

> [!IMPORTANT]
> **About Variables**: Since `$env` access is restricted in your n8n version, use **n8n Variables** instead. Go to **Settings → Variables** in the n8n UI and create your variables there. In expressions, access them with `$vars.VARIABLE_NAME` instead of `$env.VARIABLE_NAME`.
>
> Create these variables in the n8n UI first:
> | Variable Name | Value |
> |--------------|-------|
> | `OPENROUTER_API_KEY` | `sk-or-v1-your-key` |
> | `ELEVEN_API_KEY` | `sk_your-elevenlabs-key` |
> | `TWILIO_ACCOUNT_SID` | `ACxxxxxxxxxxxxxxx` |
> | `TWILIO_AUTH_TOKEN` | `your_auth_token` |
> | `TIKTOK_ACCESS_TOKEN` | `your_tiktok_token` |
> | `TWILIO_WHATSAPP_NUMBER` | `whatsapp:+14155238886` |

---

### Node 1: ⚡ Twilio Trigger (WhatsApp Incoming)

| Setting | Value |
|---------|-------|
| **Node Type** | Twilio Trigger |
| **Event** | SMS Received |
| **Authentication** | Credentials (add your Twilio account SID/Token) |

**Output**: The node automatically outputs the message details.
- `{{ $json.Body }}` = The topic
- `{{ $json.From }}` = Sender number

---

### Node 2: 🧹 Set Node — Extract Topic

| Setting | Value |
|---------|-------|
| **Node Type** | Set |
| **Name** | `Set Topic` |

**Assignments**:

| Field Name | Value (Expression) |
|------------|-------------------|
| `topic` | `{{ $json.Body.trim() }}` |
| `sender` | `{{ $json.From }}` |

> [!NOTE]
> The Twilio Trigger simplifies things by handling the webhook verification automatically. You just need to connect your Twilio account credentials in n8n.

---

### Node 3: 🧠 HTTP Request — OpenRouter LLM Call

| Setting | Value |
|---------|-------|
| **Node Type** | HTTP Request |
| **Method** | POST |
| **URL** | `https://openrouter.ai/api/v1/chat/completions` |

**Headers**:

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer your_openrouter_api_key_here` |
| `Content-Type` | `application/json` |
| `HTTP-Referer` | `https://github.com/meta-ai-api` |
| `X-Title` | `Lofi n8n Automation` |

**Body (JSON)**:
```json
{
  "model": "openrouter/free",
  "messages": [
    {
      "role": "system",
      "content": "You are an expert Lofi video content creator specializing in viral 2D Anime-style YouTube Shorts and TikToks.\n\nCORE DIRECTIVE 1: VARIETY AND UNIQUENESS.\nDO NOT repeat the same scene structure. Each prompt must be a fresh interpretation of the TOPIC.\n\nCORE DIRECTIVE 2: FIXED CAMERA STABILITY.\nTHE CAMERA MUST BE FIXED. No pans, rotations, or zooms.\n\nCORE DIRECTIVE 3: INVISIBLE PING-PONG LOOPS.\nFocus on objects with SYMMETRICAL or CYCLICAL motion (steam, rain, flickering).\n\nCORE DIRECTIVE 4: 2D ILLUSTRATIVE AESTHETIC.\nMUST BE 2D anime/illustration style (Studio Ghibli / 90s retro anime). NO photorealism.\n\nCORE DIRECTIVE 5: DEEP & IMMERSIVE NARRATION (PREMIUM).\nGenerate a \"narrative_pitch\" that is:\n- Hook & Depth: Start with a scroll-stopping hook, then dive into a deeper, philosophical, or emotionally resonant observation.\n- Poetic & Wise: Use rich, evocative language.\n- Length: Exactly 3-5 powerful sentences (around 40-60 words).\n- Atmospheric Pacing: Use ellipses (...) frequently.\n- Vibe-Matched: Perfectly aligns with the visual mood.\n\nOUTPUT FORMAT (JSON ONLY):\n{\"video_prompt\": \"...\", \"narrative_pitch\": \"...\", \"title\": \"...\", \"tags\": [...], \"description\": \"...\"}"
    },
    {
      "role": "user",
      "content": "Create a viral TikTok Lofi concept for: \"{{ $node['Extract Topic'].json.topic }}\"\n\nRequirements:\n- Visuals must be loop-friendly (forward/reverse).\n- Narration (narrative_pitch) must be an elite, emotional hook that stops the scroll.\n- Lighting/Atmosphere must be immersive.\n\nGenerate JSON response."
    }
  ]
}
```

**Output Parsing** — Add a **Code Node** (Node 3b) right after to clean the JSON:

```javascript
// Node: Parse LLM Response
const raw = $input.first().json.choices[0].message.content;
let clean = raw.trim();
if (clean.startsWith('```json')) clean = clean.slice(7);
if (clean.startsWith('```'))    clean = clean.slice(3);
if (clean.endsWith('```'))      clean = clean.slice(0, -3);

const data = JSON.parse(clean.trim());
return [{ json: data }];
```

After this node, you have:
- `$json.video_prompt` — the prompt for Meta AI  
- `$json.narrative_pitch` — the text for ElevenLabs  
- `$json.title`, `$json.tags`, `$json.description` — TikTok metadata

---

### Node 4: 🎙️ HTTP Request — ElevenLabs Voice Generation

| Setting | Value |
|---------|-------|
| **Node Type** | HTTP Request |
| **Method** | POST |
| **URL** | `https://api.elevenlabs.io/v1/text-to-speech/JBFqnCBsd6RMkjVDRZzb` |

> `JBFqnCBsd6RMkjVDRZzb` = George voice ID. Change as needed.

**Headers**:

| Header | Value |
|--------|-------|
| `xi-api-key` | `your_elevenlabs_api_key_here` |
| `Content-Type` | `application/json` |
| `Accept` | `audio/mpeg` |

**Body (JSON)**:
```json
{
  "text": "{{ $json.narrative_pitch }}",
  "model_id": "eleven_multilingual_v2",
  "voice_settings": {
    "stability": 0.7,
    "similarity_boost": 0.75,
    "style": 0.0,
    "use_speaker_boost": true,
    "speed": 0.8
  }
}
```

**Response**: Set **Response Format** to `File` → this gives you the binary MP3 data.

**Next** (Node 4b): Add a **Write Binary File** node to save the audio:
```
~/content-automation/voice_{{ $node['Extract Topic'].json.timestamp }}.mp3
```

---

### Node 5: 🎬 HTTP Request → FastAPI — Meta AI Video Generation

> [!NOTE]
> Since n8n no longer has an "Execute Command" node, we call the FastAPI server running on `localhost:8000` which wraps `video.py`.

| Setting | Value |
|---------|-------|
| **Node Type** | HTTP Request |
| **Method** | POST |
| **URL** | `http://localhost:8000/generate-video` |

**Headers**:

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |

**Body (JSON)**:
```json
{
  "prompt": "{{ $node['Parse LLM Response'].json.video_prompt }}"
}
```

**Timeout**: Set to **300 seconds** (5 min) — video generation takes a while.

**Output**: The response contains:
```json
{
  "status": "success",
  "video_path": "/opt/content-automation/outputs/lofi_scene_20260215_130000_1.mp4"
}
```

You'll use `{{ $json.video_path }}` in the next node.

> [!TIP]
> Nodes 4 and 5 can run **in parallel** — connect both to the output of Node 3b. Then use a **Merge** node to collect both results:
> - **Mode**: Combine
> - **Combine By**: Position
>
> This ensures n8n waits for both the voice and video to generation to finish before proceeding to fusion.

---

### Node 6: 🎵 HTTP Request → FastAPI — Music Fusion + Ping-Pong Loop

| Setting | Value |
|---------|-------|
| **Node Type** | HTTP Request |
| **Method** | POST |
| **URL** | `http://localhost:8000/fuse-video` |

**Body (JSON)**:
```json
{
  "video_path": "{{ $node['Generate Video'].json.video_path }}",
  "voice_path": "/opt/content-automation/voice_{{ $node['Extract Topic'].json.timestamp }}.mp3",
  "output_name": "final_{{ $node['Extract Topic'].json.timestamp }}.mp4"
}
```

**Timeout**: Set to **300 seconds**.

**Output**:
```json
{
  "status": "success",
  "final_video_path": "/opt/content-automation/final_videos/final_20260215_130000.mp4"
}
```

---

### Node 7: 📤 TikTok Upload

> [!IMPORTANT]
> TikTok does **not** have a public "direct upload" API for personal accounts. Here are your options, ranked by feasibility:

#### Option A: TikTok Developer API (Content Posting API) ✅ Recommended

1. Register at [TikTok for Developers](https://developers.tiktok.com/)
2. Create an app and request **Content Posting API** access
3. Complete the app review process (takes a few days)
4. Get your **Client Key**, **Client Secret**, and complete the OAuth 2.0 flow to get an **Access Token**

**Step 1 — Init the upload** (HTTP Request node):

| Setting | Value |
|---------|-------|
| **Node Type** | HTTP Request |
| **Method** | POST |
| **URL** | `https://open.tiktokapis.com/v2/post/publish/video/init/` |

**Headers**:

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer your_tiktok_access_token_here` |
| `Content-Type` | `application/json` |

**Body (JSON)**:
```json
{
  "post_info": {
    "title": "{{ $node['Parse LLM Response'].json.title }} 🌙 #lofi #anime #aesthetic",
    "privacy_level": "PUBLIC_TO_EVERYONE",
    "disable_duet": false,
    "disable_stitch": false,
    "disable_comment": false
  },
  "source_info": {
    "source": "FILE_UPLOAD",
    "video_size": {{ $json.fileSize }},
    "chunk_size": {{ $json.fileSize }},
    "total_chunk_count": 1
  }
}
```

**Step 2 — Upload the binary** (second HTTP Request node):

| Setting | Value |
|---------|-------|
| **Method** | PUT |
| **URL** | `{{ $json.data.upload_url }}` |

Set **Body Content Type** to `Binary` and select the video file binary.

> [!TIP]
> Use the FastAPI `/download/{filename}` endpoint to get the video binary into n8n first:
> ```
> GET http://localhost:8000/download/final_{{ $node['Extract Topic'].json.timestamp }}.mp4
> ```
> Set Response Format to `File` so n8n receives it as binary data.

#### Option B: Use a Third-Party Service (Tokapi / Tikapi)

Services like [tikapi.io](https://tikapi.io) or [tokapi.com](https://tokapi.com) provide simpler REST APIs:

```
POST https://api.tikapi.io/post/video
Headers: X-API-KEY: your-tikapi-key
Body: multipart/form-data with video file + caption
```

#### Option C: Selenium/Puppeteer Automation (Last Resort)

Use a Python Selenium script wrapped in a **new FastAPI endpoint** that automates the TikTok web upload flow. Fragile but works without API approval.

---

### Node 8: 📱 HTTP Request — WhatsApp Reply (Confirmation)

| Setting | Value |
|---------|-------|
| **Node Type** | HTTP Request |
| **Method** | POST |
| **URL** | `https://api.twilio.com/2010-04-01/Accounts/your_twilio_account_sid_here/Messages.json` |

**Authentication**: Basic Auth  
- Username: `your_twilio_account_sid_here`  
- Password: `your_twilio_auth_token_here`  

**Body** (Form URL-Encoded):

| Field | Value |
|-------|-------|
| `From` | `whatsapp:+14155238886` |
| `To` | `{{ $node['Extract Topic'].json.sender }}` |
| `Body` | `✅ Your Lofi video for "{{ $node['Extract Topic'].json.topic }}" is done! 🎬🌙 Uploaded to TikTok.` |

---

## ⚙️ Part 4 — Credentials

> [!NOTE]
> Since n8n Variables are a premium feature, just **hardcode your API keys** directly into the nodes as shown above.

---

## 🔄 Part 5 — Complete Node Wiring Summary

```
┌──────────────────────────────────────────────────────────┐
│                      n8n WORKFLOW                        │
│                                                          │
│  [1] Webhook (POST /whatsapp-lofi)                      │
│       │                                                  │
│  [2] Set Node (Extract Topic, Sender, Timestamp)        │
│       │                                                  │
│  [3] HTTP Request → OpenRouter LLM                      │
│       │                                                  │
│  [3b] Code Node → Parse JSON Response                   │
│       │                                                  │
│       ├──────────────────────┐                           │
│       │                      │                           │
│  [4] HTTP Request         [5] HTTP Request               │
│  ElevenLabs TTS           POST localhost:8000            │
│  (returns MP3 binary)     /generate-video                │
│       │                      │                           │
│  [4b] Write Binary File     │                           │
│  (save voice.mp3)            │                           │
│       │                      │                           │
│       └──────┬───────────────┘                           │
│              │  (Merge node)                             │
│              │                                           │
│  [6] HTTP Request → POST localhost:8000/fuse-video       │
│              │                                           │
│  [7] TikTok Upload (HTTP Request)                       │
│              │                                           │
│  [8] HTTP Request → Twilio WhatsApp Reply               │
│                                                          │
│  ─── FastAPI Server on localhost:8000 ───                │
│  • POST /generate-video  (wraps video.py)               │
│  • POST /fuse-video      (wraps addMusic.py)            │
│  • GET  /download/{file} (serves final videos)          │
│  • POST /cleanup         (delete old files)             │
│  • GET  /health          (health check)                 │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 🍪 Part 6 — Meta AI Cookie Maintenance

The biggest reliability risk is the **Meta AI session cookies** expiring.

### Strategy: Semi-Automated Cookie Refresh

1. **Create a `cookies.json`** file on the VM:
   ```json
   {
     "datr": "YOUR_DATR_VALUE",
     "abra_sess": "YOUR_ABRA_SESS_VALUE",
     "ecto_1_sess": "YOUR_ECTO_1_SESS_VALUE"
   }
   ```

2. **Modify `video.py`** to read cookies from this file instead of hardcoding:
   ```python
   import json
   with open("cookies.json") as f:
       cookies = json.load(f)
   ```

3. **Set up a monitoring node** in n8n: After the video generation HTTP Request (Node 5), add an **IF** node that checks `{{ $json.status }}`. If it's not `"success"`, send yourself a WhatsApp alert:
   ```
   ⚠️ Meta AI cookies expired! Please refresh them.
   ```

4. **Refresh process**: Log into [meta.ai](https://www.meta.ai/) in your browser, extract new cookies from DevTools → Network tab, and update `cookies.json` via SSH.

---

## 🧹 Part 7 — Maintenance & Cleanup

### Auto-Cleanup Old Files

Add a **final HTTP Request** node at the end of the workflow:

| Setting | Value |
|---------|-------|
| **Method** | POST |
| **URL** | `http://localhost:8000/cleanup` |

**Body (JSON)**:
```json
{
  "max_age_minutes": 1440
}
```

This deletes video/audio files older than 24 hours to save disk space.

### Error Handling

Wrap the entire workflow in n8n's **Error Trigger** workflow:
1. Create a separate **Error Workflow**
2. In that workflow, use an **Error Trigger** node → **HTTP Request** (Twilio) to send yourself a WhatsApp message with the error details
3. Link this error workflow in your main workflow's settings (Settings → Error Workflow)

---

## 📋 Part 8 — Quick Checklist

| # | Step | Status |
|---|------|--------|
| 1 | VPS ready (Ubuntu, 4GB+ RAM) | ✅ |
| 2 | Install FFmpeg + Python 3.11 (if not already) | ☐ |
| 3 | n8n running via npm (use pm2 for persistence) | ✅ |
| 4 | Set up HTTPS reverse proxy (Caddy) | ☐ |
| 5 | Clone project + install Python deps on VM (+ `fastapi uvicorn`) | ☐ |
| 6 | Create `api_server.py` and start with pm2/systemd | ☐ |
| 7 | Modify `video.py` to read cookies from file | ☐ |
| 8 | Create Twilio account + configure WhatsApp sandbox | ☐ |
| 9 | Set Twilio webhook URL to n8n endpoint | ☐ |
| 10 | Create n8n Variables (Settings → Variables) | ☐ |
| 11 | Build all 8 n8n nodes (Webhook → Twilio Reply) | ☐ |
| 12 | Register TikTok Developer App + get access token | ☐ |
| 13 | Test end-to-end: Send WhatsApp msg → Get TikTok upload | ☐ |
| 14 | Set up error workflow for failure alerts | ☐ |
| 15 | Activate workflow in n8n (toggle ON) | ☐ |

---

## 🎯 Final Notes

- **Services running on VM**: You'll have **3 processes** running: (1) **n8n** via npm/pm2, (2) **FastAPI** via uvicorn/pm2, (3) **Caddy** for HTTPS.
- **Cost Estimation**: OpenRouter (free tier), ElevenLabs (~$5/mo for Creator), Twilio WhatsApp (~$0.005/msg), VPS (~$5-15/mo), TikTok API (free). **Total: ~$15-25/month**.
- **Scaling**: For multiple users, add a queue system. Each WhatsApp message triggers one workflow execution. n8n handles concurrency natively.
- **Upgrading Models**: Swap `openrouter/free` for `anthropic/claude-3-sonnet` or `openai/gpt-4o` in the LLM node for better prompt quality (costs ~$0.01 per generation).
- **Music Library**: Upload your `.mp3` lofi tracks to `/opt/content-automation/music/` on the VM. The pipeline randomly selects one per video.
