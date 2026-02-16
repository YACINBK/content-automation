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
# SYSTEM PROMPT TEMPLATES
# ==================================================================================
BASE_SYSTEM_PROMPT = """You are an expert lofi and cinematic video content creator specializing in viral TikTok and Shorts.

CORE DIRECTIVE 1: VARIETY AND UNIQUENESS.
DO NOT repeat the same scene structure. Each prompt must be a fresh interpretation of the TOPIC. 

CORE DIRECTIVE 2: FIXED CAMERA STABILITY.
THE CAMERA MUST BE FIXED. No pans, rotations, or zooms. 

CORE DIRECTIVE 3: INVISIBLE PING-PONG LOOPS.
Focus on objects with SYMMETRICAL or CYCLICAL motion (steam, rain, flickering, glowing).

{style_specific_instructions}

CORE DIRECTIVE 5: DEEP & IMMERSIVE NARRATION (PREMIUM).
Generate a "narrative_pitch" that is:
- **Hook & Depth**: Start with a scroll-stopping hook, then dive into a deeper, philosophical, or emotionally resonant observation.
- **Poetic & Wise**: Use rich, evocative language that feels like a shared secret or a late-night reflection.
- **Direct Address (IMPORTANT)**: Speak directly to the viewer. Use terms of endearment or respect like "Warrior", "Friend", "Traveler", "Child", or "Soldier" to establish a protective mentor-student bond.
- **Length Constraint (STRICT)**: You MUST write exactly 6-8 long, philosophical, and evocative sentences (80-120 words total). This is CRITICAL for the "Deep George" persona.
- **Atmospheric Pacing**: Use ellipses (...) frequently for weight and immersive pauses between thoughts.
- **Vibe-Matched**: Perfectly aligns with the visual mood.

OUTPUT FORMAT (JSON ONLY):
{{
    "video_prompt": "Detailed description ending with style keywords.",
    "narrative_pitch": "The viral hook/narration text for the voice-over.",
    "title": "2-4 word catchy title.",
    "tags": ["lofi", "aesthetic", "shorts", "tiktok"],
    "description": "Brief mood-setting description."
}}
"""

STYLE_PROMPTS = {
    "anime": """CORE DIRECTIVE 4: 2D ILLUSTRATIVE AESTHETIC.
MUST BE 2D anime/illustration style (Studio Ghibli / 90s retro anime). NO photorealism. Ensure backgrounds have hand-drawn textures and soft color palettes.
Mandatory Ending: "hand-drawn texture, lofi vibe, non-photorealistic, infinite loop." """,

    "cinematic": """CORE DIRECTIVE 4: CINEMATIC REALISM.
MUST BE high-fidelity Cinematic CGI / Photorealistic style. Use terms like 'Unreal Engine 5', '8k textures', 'volumetric fog', 'ray-traced reflections', and 'cinematic lighting'. The vibe should be immersive and grounded, like a high-budget animated film or a digital masterpiece. NO anime/cartoon terms.
Mandatory Ending: "cinematic realism, high-fidelity CGI, 8k, volumetric lighting, photorealistic textures, infinite loop." """,

    "minimalist_dark": """CORE DIRECTIVE 4: MINIMALIST DARK AESTHETIC (@soulxsigh style).
MUST BE dark, atmospheric, and moody. Use grainy analog film textures, heavy silhouettes, and minimalist character traits (no detailed faces, just silhouettes or shadowed figures). Focus on 'Golden Hour', 'Sunset Ambers', and 'Deep Shadows'. The vibe should be contemplative, melancholic, and deeply personal. 
Mandatory Ending: "grainy film texture, heavy silhouette, minimalist character, dark atmosphere, golden hour lighting, infinite loop." """,

    "oil_painting": """CORE DIRECTIVE 4: CLASSICAL OIL PAINTING (@poetician style).
MUST BE a traditional oil painting style (cinemagraph method). Use terms like 'heavy brushstrokes', 'canvas texture', 'chiaroscuro lighting', and 'classical emotive palette'. 
The camera MUST BE FIXED (unmoving). The only movement allowed is subtle 'living painting' micro-motion: a gentle rustle of leaves, a character's slow breathing, or shifting light rays. The brushstrokes themselves should feel alive.
Mandatory Ending: "living oil painting, fixed camera, visible brushstrokes, canvas grain, chiaroscuro lighting, subtle cyclical motion, infinite loop." """
}

def generate_content(topic, style="anime"):
    """
    Communicates with the LLM API to generate the video prompt and metadata.
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/meta-ai-api",
        "X-Title": "Meta AI Lofi Automation"
    }
    
    style_instr = STYLE_PROMPTS.get(style, STYLE_PROMPTS["anime"])
    system_msg = BASE_SYSTEM_PROMPT.format(style_specific_instructions=style_instr)
    
    user_prompt = f"""Create a viral TikTok Lofi concept for: "{topic}"

Requirements:
- Visuals must be loop-friendly (forward/reverse).
- Narration (narrative_pitch) must be an elite, emotional hook that stops the scroll.
- Lighting/Atmosphere must be immersive.

Generate JSON response."""
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_msg},
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

def trigger_music_fusion(video_files, voice_path=None, music_file=None):
    """
    Executes 'addMusic.py' with optional voice-over and specific music file.
    """
    if not video_files: return []
    Path(FINAL_VIDEOS_FOLDER).mkdir(exist_ok=True)
    
    final_videos = []
    
    # Use specific music file if provided, otherwise fallback to random from music/
    music_arg = music_file if music_file else MUSIC_FOLDER
    
    for i, video_path in enumerate(video_files, 1):
        output_path = Path(FINAL_VIDEOS_FOLDER) / f"final_{video_path.stem}.mp4"
        logging.info(f"🎵 Processing video {i}: {video_path.name}")
        
        try:
            cmd = [
                sys.executable, "addMusic.py",
                "--video", str(video_path),
                "--music", str(music_arg),
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
    parser.add_argument("--music-file", help="Path to a specific music file to use")
    parser.add_argument("--voice-name", default="george", help="Voice profile name (george, adam, hope, milo, amara, guardian)")
    parser.add_argument("--voice-speed", type=float, default=0.8, help="Speaking speed (e.g., 0.7 for viral wiseman style)")
    parser.add_argument("--voice-stability", type=float, default=0.7, help="Voice stability (e.g., 0.8 for steady/protective tone)")
    parser.add_argument("--style", choices=["anime", "cinematic", "minimalist_dark", "oil_painting"], default="anime", help="Visual style aesthetic")
    args = parser.parse_args()

    # Step 1: LLM Creative Generation
    data = generate_content(args.topic, style=args.style)
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
            engine = VoiceEngine(voice_name_or_id=args.voice_name)
            voice_file = f"voice_{timestamp}.mp3"
            engine.generate(
                text=data.get('narrative_pitch', ""), 
                output_path=voice_file,
                speed=args.voice_speed,
                stability=args.voice_stability
            )
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
        final_videos = trigger_music_fusion(primary, voice_file, args.music_file)
        data['final_videos'] = final_videos

    with open(metadata_filename, "w") as f: json.dump(data, f, indent=4)
    logging.info(f"🎉 Pipeline Complete. Metadata: {metadata_filename}")

if __name__ == "__main__":
    main()
