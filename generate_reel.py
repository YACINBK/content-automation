"""
Cinematic Slideshow Orchestrator ("Poetic Reels")
=================================================

This script implements the "Line-by-Line" generation pipeline.
1.  **Script Generation**: Uses LLM to generate 6-8 "Life Lesson" segments (Quote + Image Prompt).
2.  **Audio Synthesis**: Generates individual audio lines via ElevenLabs (George).
3.  **Visual Synthesis**: Generates vertical (9:16) images via Meta AI for each line.
4.  **Cinematic Assembly**: Fuses audio and images with long cross-fades and Ken Burns effects using MoviePy.

Usage:
    python generate_reel.py --topic "The Beauty of Unspoken Love" --style minimalist_dark
"""
import argparse
import json
import os
import requests
import time
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or "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"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY") or "sk_d6d698103758535d04ed14661a60afe58e18d2b112130d63"
VOICE_ID_GEORGE = "JBFqnCBsd6RMkjVDRZzb"  # George's ID

# Style Presets
STYLES = {
    "minimalist_dark": {
        "visual_prompt": "Mid-shot, wide angle, distant subject, grainy film texture, heavy silhouette, minimalist character, dark atmosphere, golden hour lighting, muted tones, 8k resolution, cinematic composition",
        "ken_burns_speed": 1.1,  # Gentle zoom
        "crossfade_duration": 3.0  # Seconds
    },
    "oil_painting": {
        "visual_prompt": "Mid-shot, wide angle, distant subject, living oil painting, heavy brushstrokes, chiaroscuro lighting, classical composition, canvas texture, museum quality, subtle motion",
        "ken_burns_speed": 1.05, # Very slow zoom for paintings
        "crossfade_duration": 3.5
    },
    "nostalgic_oil": {
        "visual_prompt": "early 20th century oil painting, mid-shot, wide angle, soft warm lighting, textured oil paint effect, muted earth tones, classical European illustration, nostalgic mood, detailed brush strokes, museum painting style",
        "ken_burns_speed": 1.05,
        "crossfade_duration": 3.5
    }
}

SYSTEM_PROMPT = """
You are a Poetic Cinematographer and Philosopher.
Your goal is to create a "Cinematic Reel" composed of 6-8 distinct segments.
Each segment represents a single line of a deep, philosophical quote.
For each line, you must describe a METAPHORICAL visual that illustrates the emotion, NOT a literal depiction.

**Visual Constraints (CRITICAL):**
1.  **NO Close-ups**: All images must be Mid-Shots or Wide Shots.
2.  **Metaphorical Diversity**: Change the subject/setting for each line to match the metaphor (e.g., Line 1: Couple on cliff -> Line 2: Birds in storm -> Line 3: Lonely lighthouse).
3.  **Atmosphere**: Maintain a consistent MOOD (Melancholic, Romantic, Dark) throughout.

**Output Format**:
Return ONLY a raw JSON list of objects. Do not include markdown formatting.
[
    {
        "line": "Love is not a shout into the void...",
        "image_prompt": "A solitary lighthouse standing firm against crashing dark waves at twilight"
    },
    ...
]
"""


# Import Poetry Database
try:
    import poetry_database
except ImportError:
    print("⚠️ poetry_database.py not found. Poetry features disabled.")
    poetry_database = None

def format_poem_to_script(poem):
    """Converts a poem from database to the script format expected by the pipeline."""
    script = []
    print(f"📜 Selected Poem: '{poem['title']}' by {poem['author']} ({poem.get('year', 'Unknown')})")
    
    for i, line in enumerate(poem["lines"]):
        # Use pre-defined visual prompt if available, otherwise fallback to line text
        visual_prompt = poem["visual_prompts"][i] if i < len(poem["visual_prompts"]) else f"Metaphoral imagery for: {line}"
        
        script.append({
            "line": line,
            "image_prompt": visual_prompt
        })
    return script

def generate_script(topic):
    """Generates the JSON script via LLM."""
    print(f"🧠 Brainstorming poetic segments for: '{topic}'...")
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "google/gemini-2.0-flash-001", # Fast and good at JSON
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Topic: {topic}\nStyle: Dark, Cinematic, Emotional."}
        ]
    }
    
    # Retry logic for LLM
    for attempt in range(3):
        try:
            print(f"   Attempt {attempt+1}/3...")
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:-3]
            if content.endswith("```"):
                content = content[:-3]
            
            script = json.loads(content)
            print(f"✨ Generated {len(script)} segments.")
            return script
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
            time.sleep(2)
    
    print("❌ LLM Generation Failed after 3 attempts.")
    return None

def generate_audio_segment(text, index):
    """Generates audio for a single line."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID_GEORGE}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    print(f"DEBUG: Using API Key: {ELEVENLABS_API_KEY[:5]}...{ELEVENLABS_API_KEY[-5:]}")
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.7, "similarity_boost": 0.8} # George Optimized
    }
    
    filename = f"temp_audio_{index}.mp3"
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        with open(filename, "wb") as f:
            f.write(response.content)
        print(f"   🎙️ Audio {index} generated: {filename}")
        return filename
    except Exception as e:
        print(f"   ❌ Audio Gen Failed: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Cinematic Slideshow Generator")
    parser.add_argument("--topic", required=True, help="Theme of the reel or 'random_poem'")
    parser.add_argument("--style", default="nostalgic_oil", choices=STYLES.keys(), help="Visual style")
    parser.add_argument("--dry-run", action="store_true", help="Generate script only, skip media gen")
    parser.add_argument("--poet", help="Specific poet to select from (shakespeare, rumi, etc.)")
    args = parser.parse_args()

    # 1. Generate Script (LLM or Poetry Database)
    script = None
    
    # Check if poetry is requested via --poet or specific topic keywords
    use_poetry = False
    if args.poet:
        use_poetry = True
    elif args.topic.lower() in ["poetry", "random_poem", "poem"]:
        use_poetry = True
        
    if use_poetry and poetry_database:
        print(f"📚 Searching Poetry Database (Poet: {args.poet or 'Any'})...")
        poem = poetry_database.get_random_poem(args.poet)
        if poem:
            script = format_poem_to_script(poem)
        else:
            print(f"⚠️ No poems found for poet: {args.poet}. Falling back to LLM.")
            
    # Fallback to LLM if no script yet
    if not script:
        script = generate_script(args.topic)
        
    if not script:
        return

    # Validate Script
    style_prompt = STYLES[args.style]["visual_prompt"]
    for i, segment in enumerate(script, 1):
        segment["full_prompt"] = f"{segment['image_prompt']}, {style_prompt}"

    if args.dry_run:
        print("\n📜 Generated Script (Dry Run):")
        for i, segment in enumerate(script, 1):
            print(f"  [{i}] Line: \"{segment['line']}\"")
            print(f"      Visual: {segment['image_prompt']}")
        print("\n✅ Dry Run Complete.")
        return

    print("\n🚀 Starting Media Generation Phase...")
    
    # Import Image Gen here to avoid overhead in dry-run
    from metaai_api import MetaAI
    cookies = {
        "datr": "AP2NaQK7olTjm_TvBSXPqHhB",
        "abra_sess": "FqyV5szPn9YDFioYDjg3Vm5VN0J3c2pyb1FBFvb%2F75gNAA%3D%3D==",
        "ecto_1_sess": "36ba8935-2b8b-4f84-a08a-a6bc715dc5b4.v1%3AxGMSNaL_f8zDMDnDjb4ZnfXo-slIfe-XvQ2zAAhLqmDSTPUTdSzypQK3k5OX_IvXF48O1Mwd8HWbfPNY1J5bemG5oFbQuueRRUNZi_X9Hhyj5lNr5Z3r5kywzUhkBapJU_cQXjd8NloSMMhZft_0xmaVmYjuS1qs1JTAhARB5jPTgOopwoEtKyLJdRsKV-NA0FGSWsP-awwSztQ95e1c6t1Yuw7IKZ90L5YuloL3oJeRl_Qt615KP4nYGG4UakFERlTeUKlcDnQDsV9HP9nq8TGWDrXhU8uiSwXASDCPgLdZcj8MSenhHPmOSed0i8xPqfq1Z5g96pxzfqEfgivIXAGT4j6YxQ2KA4CNrNKv7rJ0M2H_qb7BtBnPUiUkvMkItgaidmixEEljTMkrADsDK9QKVpw3fvaXYeQGvgjhfpCUogugI-hy4jiiRAOYDNCdc84254id8UxUVWKqfpO480qoduVUkfTrwovMv8vUp4w06JfRNEoqD1HiDrm3%3AhNRxYHbVcmsG3aF_%3AnsWRU_UH8mQkg2J0nsDmog.QHdEll4bupl8SrOkGzCdkk3H0IGAeCFm3cMu3IcZ7Tg"
    }
    ai = MetaAI(cookies=cookies)

    media_segments = []

    for i, segment in enumerate(script, 1):
        print(f"\n🎬 Processing Segment {i}/{len(script)}...")
        
        # Audio
        audio_file = f"temp_audio_{i}.mp3"
        if not os.path.exists(audio_file):
            audio_file = generate_audio_segment(segment["line"], i)
        else:
            print(f"   ⏩ Audio {i} exists, skipping gen.")
            
        if not audio_file: continue
        
        # Image
        img_file = f"temp_image_{i}.jpg"
        if os.path.exists(img_file):
             print(f"   ⏩ Image {i} exists, skipping gen.")
             media_segments.append({
                "audio": audio_file,
                "image": img_file,
                "text": segment["line"]
             })
             continue

        print(f"   🎨 Generating Image: {segment['image_prompt'][:50]}...")
        try:
            resp = ai.generate_image_new(segment["full_prompt"], orientation="VERTICAL")
            if resp["success"] and resp.get("image_urls"):
                img_url = resp["image_urls"][0]
                img_file = f"temp_image_{i}.jpg"
                
                # Download
                r = requests.get(img_url)
                with open(img_file, "wb") as f:
                    f.write(r.content)
                print(f"   ✅ Image Saved: {img_file}")
                
                media_segments.append({
                    "audio": audio_file,
                    "image": img_file,
                    "text": segment["line"]
                })
            else:
                print("   ❌ Image Gen Failed (Meta AI Error)")
        except Exception as e:
             print(f"   ❌ Image Gen Logic Error: {e}")

    if not media_segments:
        print("❌ No valid segments generated.")
        return

    # Assembly Logic (MoviePy)
    # Ensure FFmpeg is found
    os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, vfx
    
    final_clips = []
    
    
    # We need to crossfade. 
    # Strategy: Sequential clips, but we set the start time of next clip earlier.
    # MoviePy's concatenate_videoclips with padding=-X works best for simple crossfades.
    
    # USER REQUEST: Remove fusion/transitions. Use 0.0 for hard cuts.
    cf_duration = 0.0 # STYLES[args.style]["crossfade_duration"]
    
    for i, seg in enumerate(media_segments):
        audio = AudioFileClip(seg["audio"])
        duration = audio.duration + 0.5 # Reduced padding for tighter cuts
        
        # Ensure image lasts long enough for crossfades
        # If it's not the first or last, it needs overlap on both sides?
        # Actually, simpler: Image Duration = Audio Duration + Fade Out Time
        
        # MoviePy Concatenate with padding=-3 means they overlap by 3s.
        # So clip duration must be Audio + 3s.
        img_duration = duration + cf_duration
        
        clip = ImageClip(seg["image"]).with_duration(img_duration).with_audio(audio)
        
        # Apply Ken Burns (Zoom In)
        # Resize from 1.0 to 1.1 over duration
        # v2 uses 'resized' instead of 'resize' and lambda transformations need detailed handling
        # simpler zoom for v2: use vfx.Resize ?? No, let's keep it simple for now to avoid complexity errors.
        # clip = clip.resized(lambda t: 1.0 + (0.05 * t / img_duration)) 
        
        # Fade In/Out - DISABLED
        # if i > 0:
        #     clip = clip.with_effects([vfx.CrossFadeIn(cf_duration)])
        
        final_clips.append(clip)
        
    final_video = concatenate_videoclips(final_clips, method="compose", padding=0)
    
    output_filename = f"final_reel_{int(time.time())}.mp4"
    final_video.write_videofile(output_filename, fps=24, codec="libx264", audio_codec="aac")
    print(f"🎉 Reel Generated: {output_filename}")

if __name__ == "__main__":
    main()
