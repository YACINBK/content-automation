"""
Lofi Video Automation Pipeline - Prompt Generator & Orchestrator
================================================================

This script acts as the "Brain" of the automation pipeline. It performs three main roles:
1. LLM Interaction: Communicates with OpenRouter (using Llama/other models) to generate 
   viral-optimized, loop-friendly video prompts and YouTube metadata (Title, Tags, Description).
2. Video Generation: Triggers 'video.py' to generate the raw video files based on the LLM prompt.
3. Music Fusion: Triggers 'addMusic.py' to overlay random Lofi music and apply ping-pong looping.

Workflow:
Topic -> LLM -> Prompt/Metadata -> video.py -> Raw Videos -> addMusic.py -> Final Music Videos

Created for viral YouTube Shorts/TikTok automation.
"""

import os
import json
import logging
import requests
import subprocess
import argparse
import glob
import re
import sys
from datetime import datetime
from pathlib import Path

from voice_engine import VoiceEngine

# Setup logging with a professional format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ==================================================================================
# CONFIGURATION SECTION
# ==================================================================================
# API Configuration: OpenRouter is used for LLM interaction.
# Use environment variable 'OPENROUTER_API_KEY' for better security.
API_KEY = os.getenv("OPENROUTER_API_KEY") or "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"

# Base URL for OpenRouter API.
BASE_URL = "https://openrouter.ai/api/v1/chat/completions" 

# Model Selection: 'openrouter/free' allows for testing without costs.
# For higher quality, consider 'openai/gpt-4o' or 'anthropic/claude-3-sonnet'.
MODEL_NAME = "openrouter/free" 

# Directory Configuration
MUSIC_FOLDER = "music"          # Folder containing source .mp3/.wav files
FINAL_VIDEOS_FOLDER = "final_videos" # Folder where music-infused videos are saved

# ==================================================================================
# SYSTEM PROMPT - THE CORE LOGIC
# ==================================================================================
# This prompt is meticulously engineered to enforce:
# 1. 2D Anime/Studio Ghibli aesthetic (avoiding photorealism).
# 2. Fixed camera stability (essential for seamless ping-pong loops).
# 3. Cyclical motion (steam, rain, swaying) to make loops invisible.
# 4. viral, TikTok-ready narration pitches.
# 5. JSON-only output for machine readability.
SYSTEM_PROMPT = """You are an expert Lofi video content creator specializing in viral 2D Anime-style YouTube Shorts and TikToks.

CORE DIRECTIVE 1: VARIETY AND UNIQUENESS.
DO NOT repeat the same scene structure. Each prompt must be a fresh interpretation of the TOPIC. 

CORE DIRECTIVE 2: FIXED CAMERA STABILITY.
THE CAMERA MUST BE FIXED. No pans, rotations, or zooms. 

CORE DIRECTIVE 3: INVISIBLE PING-PONG LOOPS.
Focus on objects with SYMMETRICAL or CYCLICAL motion (steam, rain, flickering).

CORE DIRECTIVE 4: 2D ILLUSTRATIVE AESTHETIC.
MUST BE 2D anime/illustration style (Studio Ghibli / 90s retro anime). NO photorealism.

CORE DIRECTIVE 5: DEEP & IMMERSIVE NARRATION (PREMIUM).
Generate a "narrative_pitch" that is:
- **Hook & Depth**: Start with a scroll-stopping hook, then dive into a deeper, philosophical, or emotionally resonant observation.
- **Poetic & Wise**: Use rich, evocative language that feels like a shared secret or a late-night reflection.
- **Length**: Exactly 3-5 powerful sentences (around 40-60 words).
- **Atmospheric Pacing**: Use ellipses (...) frequently for weight and immersive pauses (e.g., "The world is loud... but here... in this corner of the night... there is only the rain.").
- **Vibe-Matched**: Perfectly aligns with the visual mood (e.g., melancholy, hope, nostalgia).

OUTPUT FORMAT (JSON ONLY):
{
    "video_prompt": "Detailed 2D ANIME prompt ending with: hand-drawn texture, lofi vibe, non-photorealistic, infinite loop.",
    "narrative_pitch": "The viral hook/narration text for the voice-over.",
    "title": "2-4 word catchy title.",
    "tags": ["lofi", "anime", "aesthetic", "shorts", "tiktok"],
    "description": "Brief mood-setting description."
}
"""

def generate_content(topic):
    """
    Communicates with the LLM API to generate the video prompt and metadata.
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/meta-ai-api",
        "X-Title": "Meta AI Lofi Automation"
    }
    
    user_prompt = f"""Create a viral TikTok Lofi concept for: "{topic}"

Requirements:
- Visuals must be loop-friendly (forward/reverse).
- Narration (narrative_pitch) must be an elite, emotional hook that stops the scroll.
- Lighting/Atmosphere must be immersive.

Generate JSON response."""
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
    }

    logging.info(f"🚀 Sending request to LLM ({MODEL_NAME})...")
    
    try:
        response = requests.post(BASE_URL, headers=headers, json=payload, timeout=60)
        if response.status_code != 200:
            return None
            
        data = response.json()
        if 'choices' in data:
            content_str = data['choices'][0]['message']['content']
            clean_content = content_str.strip()
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            return json.loads(clean_content.strip())
        return None
    except Exception as e:
        logging.error(f"❌ LLM error: {e}")
        return None

def trigger_video_generation(prompt):
    """
    Executes 'video.py' to generate raw video clips.
    """
    logging.info("🎥 Triggering video.py...")
    outputs_dir = Path("outputs")
    existing_videos = set(outputs_dir.glob("*.mp4")) if outputs_dir.exists() else set()
    
    try:
        cmd = [sys.executable, "video.py", "--prompt", prompt]
        # Pipe directly to the terminal for real-time progress
        subprocess.run(cmd)
        new_videos = set(outputs_dir.glob("*.mp4")) - existing_videos
        return sorted(list(new_videos))
    except Exception as e:
        logging.error(f"❌ video.py error: {e}")
        return None

def trigger_music_fusion(video_files, voice_path=None):
    """
    Executes 'addMusic.py' with optional voice-over.
    """
    if not video_files: return []
    Path(FINAL_VIDEOS_FOLDER).mkdir(exist_ok=True)
    
    final_videos = []
    for i, video_path in enumerate(video_files, 1):
        output_path = Path(FINAL_VIDEOS_FOLDER) / f"final_{video_path.stem}.mp4"
        logging.info(f"🎵 Processing video {i}: {video_path.name}")
        
        try:
            cmd = [
                sys.executable, "addMusic.py",
                "--video", str(video_path),
                "--music", MUSIC_FOLDER,
                "--output", str(output_path)
            ]
            if voice_path:
                cmd.extend(["--voice", str(voice_path)])
                
            result = subprocess.run(cmd)
            if result.returncode != 0:
                logging.error(f"❌ addMusic.py failed for {video_path.name}")
                continue
                
            final_videos.append(str(output_path))
        except Exception as e:
            logging.error(f"❌ Fusion error: {e}")
            
    return final_videos

def main():
    parser = argparse.ArgumentParser(description="Lofi Automation with TikTok Narration")
    parser.add_argument("--topic", default="lofi girl raining coffee", help="Theme")
    parser.add_argument("--voice", action="store_true", help="Enable ElevenLabs Voice-Over")
    parser.add_argument("--dry-run", action="store_true", help="Metadata only")
    parser.add_argument("--skip-music", action="store_true", help="Raw videos only")
    args = parser.parse_args()

    # Step 1: LLM Creative Generation
    data = generate_content(args.topic)
    if not data: return

    logging.info(f"✨ Pitch: {data.get('narrative_pitch')}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metadata_filename = f"metadata_{timestamp}.json"
    
    if args.dry_run:
        with open(metadata_filename, "w") as f: json.dump(data, f, indent=4)
        return

    # Step 2: Voice Generation (if enabled)
    voice_file = None
    if args.voice:
        try:
            engine = VoiceEngine()
            voice_file = f"voice_{timestamp}.mp3"
            engine.generate(data.get('narrative_pitch', ""), voice_file)
            data['voice_file'] = voice_file
        except Exception as e:
            logging.error(f"🎙️ Voice-over failed: {e}")

    # Step 3: Video Generation
    video_files = trigger_video_generation(data['video_prompt'])
    if not video_files: return
    data['raw_videos'] = [str(v) for v in video_files]

    # Step 4: Fusion
    if not args.skip_music:
        primary = video_files[:1]
        final_videos = trigger_music_fusion(primary, voice_file)
        data['final_videos'] = final_videos

    with open(metadata_filename, "w") as f: json.dump(data, f, indent=4)
    logging.info(f"🎉 Pipeline Complete. Metadata: {metadata_filename}")

if __name__ == "__main__":
    main()
