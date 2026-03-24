"""
FastAPI wrapper for the Lofi Video Pipeline.
Exposes the Python scripts as HTTP endpoints so n8n can call them.

Run with: uvicorn api_server:app --host 0.0.0.0 --port 8000
"""

import os
import sys
import glob
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Lofi Pipeline API")

# -------------------------------------------------------------------
# Request Models
# -------------------------------------------------------------------
class VideoRequest(BaseModel):
    prompt: str

class CleanupRequest(BaseModel):
    max_age_minutes: int = 1440  # 24 hours

# -------------------------------------------------------------------
# Endpoint 1: Generate Video via Meta AI
# -------------------------------------------------------------------
@app.post("/generate-video")
def generate_video(req: VideoRequest):
    """Runs video.py with the given prompt. Returns path to generated video."""
    try:
        # Run video.py
        cmd = [
            sys.executable, "video.py",
            "--prompt", req.prompt
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout
            cwd=os.getcwd()
        )

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"video.py failed: {result.stderr}"
            )

        # Find the latest generated video in outputs/
        output_glob = os.path.join("outputs", "*.mp4")
        videos = sorted(
            glob.glob(output_glob),
            key=os.path.getmtime,
            reverse=True
        )

        if not videos:
            raise HTTPException(status_code=404, detail="No video files generated in outputs/")

        # The newest video is likely the one we just made
        latest_video = os.path.abspath(videos[0])

        return {
            "status": "success",
            "video_path": latest_video,
            "stdout": result.stdout
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Video generation timed out (5 min)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------------
# Endpoint 2: Music Fusion + Ping-Pong Loop (UPDATED: Accepts Upload)
# -------------------------------------------------------------------
@app.post("/fuse-video")
async def fuse_video(
    video_path: str = Form(...),
    output_name: str = Form("final_output.mp4"),
    voice_file: UploadFile = File(None)
):
    """
    Runs addMusic.py.
    Accepts 'video_path' (string) and optional 'voice_file' (upload).
    Saves the uploaded voice file locally before processing.
    """
    
    # Create final_videos directory
    final_dir = "final_videos"
    os.makedirs(final_dir, exist_ok=True)
    output_path = os.path.join(final_dir, output_name)
    
    # Handle Voice File Upload
    voice_path_local = None
    if voice_file:
        # Save uploaded file to current directory (or /tmp)
        # Using a timestamp to avoid collisions
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"voice_upload_{ts}.mp3"
        voice_path_local = os.path.abspath(filename)
        
        try:
            with open(voice_path_local, "wb") as buffer:
                shutil.copyfileobj(voice_file.file, buffer)
        except Exception as e:
             raise HTTPException(status_code=500, detail=f"Failed to save voice file: {e}")

    try:
        cmd = [
            sys.executable, "addMusic.py",
            "--video", video_path,
            "--music", "music",
            "--output", output_path
        ]
        if voice_path_local:
            cmd.extend(["--voice", voice_path_local])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=os.getcwd()
        )

        # Cleanup uploaded voice file
        if voice_path_local and os.path.exists(voice_path_local):
            os.remove(voice_path_local)

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"addMusic.py failed: {result.stderr}"
            )

        return {
            "status": "success",
            "final_video_path": os.path.abspath(output_path),
            "stdout": result.stdout
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Fusion timed out (5 min)")
    except Exception as e:
        # Try cleanup on error
        if voice_path_local and os.path.exists(voice_path_local):
            os.remove(voice_path_local)
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------------
# Endpoint 3: Download final video
# -------------------------------------------------------------------
@app.get("/download/{filename}")
def download_video(filename: str):
    """Returns the final video file as a downloadable response."""
    filepath = os.path.join("final_videos", filename)
    if not os.path.exists(filepath):
        filepath = os.path.join("outputs", filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="File not found")
            
    return FileResponse(filepath, media_type="video/mp4", filename=filename)

# -------------------------------------------------------------------
# Endpoint 4: Cleanup
# -------------------------------------------------------------------
@app.post("/cleanup")
def cleanup(req: CleanupRequest):
    """Deletes video/audio files older than max_age_minutes."""
    import time
    now = time.time()
    cutoff = now - (req.max_age_minutes * 60)
    deleted = []

    patterns = [
        os.path.join("outputs", "*.mp4"),
        os.path.join("final_videos", "*.mp4"),
        "voice_*.mp3"
    ]

    for pattern in patterns:
        for f in glob.glob(pattern):
            try:
                if os.path.getmtime(f) < cutoff:
                    os.remove(f)
                    deleted.append(f)
            except:
                pass

    return {"status": "success", "deleted_count": len(deleted), "deleted": deleted}

# -------------------------------------------------------------------
# Health check
# -------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
