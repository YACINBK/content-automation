import os
os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
import re
import json
import whisper
from moviepy.editor import (
    VideoFileClip, TextClip, CompositeVideoClip,
    ImageClip, ColorClip, AudioFileClip, CompositeAudioClip
)

def extract_toxic_words_from_config(config_path):
    """Reads the JSON config and extracts words wrapped in [brackets]."""
    if not os.path.exists(config_path):
        return ["pov"]  # Default

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    narrative_script = config.get("narrative_script", [])
    image_prompts = config.get("image_prompts", [])

    # Combine everything to catch brackets placed anywhere by the LLM
    combined_text = " ".join(narrative_script + image_prompts).lower()

    # Find all words in brackets and strip punctuation
    toxic_words = re.findall(r'\[(.*?)\]', combined_text)

    # Clean up multi-word bracketed terms (e.g., "[weaponized algorithm]" -> ["weaponized", "algorithm"])
    toxic_words_clean = []
    for phrase in toxic_words:
        cleaned = re.sub(r'[^\w\s]', '', phrase.strip())
        toxic_words_clean.extend(cleaned.split())

    # Implicitly add "pov" to always be highlighted
    if "pov" not in toxic_words_clean:
        toxic_words_clean.append("pov")

    return toxic_words_clean


def process_concept_folder(concept_folder_path, output_drive_path):
    print(f"--- Processing {concept_folder_path} ---")

    folder_name = os.path.basename(concept_folder_path)
    # Extract project name (e.g., 'production_nasa_launch_failure' -> 'nasa_launch_failure')
    project_name = folder_name.replace("production_", "")

    config_file = os.path.join("configs", f"{project_name}.json")
    master_video = os.path.join(concept_folder_path, f"{project_name}_master_aesthetic.mp4")

    if not os.path.exists(master_video):
        print(f"Skipping {project_name}: Missing {project_name}_master_aesthetic.mp4")
        return

    final_output_path = os.path.join(output_drive_path, f"{project_name}_Captioned.mp4")
    if os.path.exists(final_output_path):
        print(f"Skipping {project_name}: Captioned video already exists at {final_output_path}")
        return

    # 1. Load config to parse hook metadata & toxic words
    try:
        with open(config_file, "r") as f:
            config_data = json.load(f)
    except Exception as e:
        config_data = {}
        print(f"Warning: Could not load {config_file} for metadata.")

    title = config_data.get("title", "Anomaly Log 999: UNKNOWN SUBJECT")
    log_match = re.search(r'Log\s*(\d+)', title)
    log_num = log_match.group(1) if log_match else "999"
    
    subject_match = re.search(r':\s*([^\']+)', title)
    subject_name = subject_match.group(1).strip().upper() if subject_match else "UNKNOWN SUBJECT"

    toxic_words_list = extract_toxic_words_from_config(config_file)
    print(f"Toxic words detected: {toxic_words_list}")
    primary_threat = toxic_words_list[0].upper() if toxic_words_list else "SYSTEM"

    # 2. Load Whisper and extract word-level timestamps
    print("Running local Whisper AI for timestamp extraction...")
    model = whisper.load_model("base")
    result = model.transcribe(master_video, word_timestamps=True)

    # 3. Setup MoviePy Video
    video_clip = VideoFileClip(master_video)
    w, h = video_clip.size
    duration = video_clip.duration
    y_pos = int(h * 0.82)  # 82% down the screen, safe from TikTok UI

    subtitle_clips = []
    all_word_timestamps = []  # Collect for audio FX engine use

    # 4. Generate the Typewriter Captions
    print("Burning retro-clinical captions onto video...")
    total_segments = len(result['segments'])

    for i, segment in enumerate(result['segments']):
        # CTA = last 2 segments (roughly 4-7 seconds)
        is_cta = (i >= total_segments - 2)

        for word_info in segment.get('words', []):
            raw_word = word_info['word'].strip()
            clean_word = re.sub(r'[^\w\s]', '', raw_word.lower())

            # Collect timestamps for the audio FX engine
            all_word_timestamps.append({
                "word": clean_word,
                "start": word_info['start'],
                "end": word_info['end']
            })

            # Color logic:
            # Last 2 segments (CTA) → Gold
            # Toxic/POV word        → Neon Green (boosted stroke in V5)
            # Everything else       → Clinical Beige
            if is_cta:
                text_color = '#FFD700'
                sw = 1.5
            elif clean_word in toxic_words_list:
                text_color = '#39FF14'
                sw = 2.5  # V5: Boosted neon green stroke
            else:
                text_color = '#F5F5DC'
                sw = 1.5

            start_t = word_info['start']
            end_t = word_info['end']

            # Shadow layer
            shadow = TextClip(raw_word, fontsize=45, font='Courier-Bold', color='black') \
                .set_position(('center', y_pos + 4)).set_start(start_t).set_end(end_t)

            # Main text
            main_text = TextClip(raw_word, fontsize=45, font='Courier-Bold',
                                 color=text_color, stroke_color='black', stroke_width=sw) \
                .set_position(('center', y_pos)).set_start(start_t).set_end(end_t)

            subtitle_clips.extend([shadow, main_text])

    # --- V5 MICRO-STIMULI ---

    # [V5-1] Scene 1 Dossier Banner — Clinical metadata + Controversial Flashing Text
    print("Applying V5: Dossier Hook Banner (Scene 1)...")
    
    # Mathematical scaling to universally fit ANY video resolution Meta AI spits out
    censor_height = int(h * 0.32)
    censor_bar = ColorClip(size=(w, censor_height), color=[0, 0, 0]) \
        .set_start(0).set_end(3.0) \
        .set_position(('center', 'top'))
    subtitle_clips.append(censor_bar)

    # Calculate dynamic font sizes based purely on width to prevent overflow
    fz_small = int(w * 0.030)
    fz_med = int(w * 0.040)
    fz_hook = int(w * 0.035)

    # Calculate dynamic Y-spacing evenly distributing lines across the censor bar
    y_step = censor_height / 6

    # Blinking [REC] indicator (Centered at top)
    for i in range(6):
        if i % 2 == 0:
            rec_dot = TextClip("[REC]", fontsize=fz_small, font='Courier-Bold', color='red') \
                .set_position(('center', int(y_step * 0.7))).set_start(i * 0.5).set_end((i + 1) * 0.5)
            subtitle_clips.append(rec_dot)

    # Clinical Metadata UI - Perfectly Centered
    meta_text1 = TextClip(f"ANOMALY LOG: {log_num}", fontsize=fz_small, font='Courier', color='white') \
        .set_position(('center', int(y_step * 1.8))).set_start(0).set_end(3.0)
    
    meta_text2 = TextClip(f"SUBJECT: {subject_name}", fontsize=fz_med, font='Courier-Bold', color='#CCCCCC') \
        .set_position(('center', int(y_step * 2.8))).set_start(0).set_end(3.0)
    
    meta_text3 = TextClip("NEURO-STATUS: CRITICAL FAILURE", fontsize=fz_small, font='Courier', color='#FF4444') \
        .set_position(('center', int(y_step * 3.8))).set_start(0).set_end(3.0)
    
    subtitle_clips.extend([meta_text1, meta_text2, meta_text3])

    # Controversial / Viral Hook Flash (Centered)
    hook_text = f"[WARNING: {primary_threat} OVERRIDE]"
    hook_clip = TextClip(hook_text, fontsize=fz_hook, font='Courier-Bold', color='#1A1A1A', bg_color='#39FF14') \
        .set_position(('center', int(y_step * 5.0))).set_start(0.8).set_end(2.8)
    subtitle_clips.append(hook_clip)

    # [V5-2] Subliminal SYSTEM FAILURE flash — 1 frame at exactly t=12s
    print("Applying V5: Subliminal SYSTEM FAILURE flash (t=12s)...")
    if duration > 12.04:
        subliminal_bg = ColorClip(size=(w, h), color=[0, 0, 0]) \
            .set_start(12.0).set_end(12.04) \
            .set_position(('left', 'top'))
        subliminal_text = TextClip(
            "SYSTEM FAILURE",
            fontsize=72, font='Courier-Bold', color='white'
        ).set_position('center').set_start(12.0).set_end(12.04)
        subtitle_clips.extend([subliminal_bg, subliminal_text])

    # [V5-3] CRT Overlay — Semi-transparent scanline texture over entire video
    crt_path = os.path.join(os.path.dirname(__file__), "sfx", "crt_overlay.png")
    if os.path.exists(crt_path):
        print("Applying V5: CRT scanline overlay...")
        crt = ImageClip(crt_path) \
            .set_duration(duration) \
            .set_opacity(0.15) \
            .set_position(('left', 'top'))
        # Resize to match video dimensions if needed
        if crt.size != (w, h):
            crt = crt.resize((w, h))
        subtitle_clips.append(crt)
    else:
        print("Skipping CRT overlay: sfx/crt_overlay.png not found")

    # 5. Composite Final Audio FX (Drone, Heartbeat, Bracket Strikes)
    print("Applying V5: Continuous Audio FX (Drone, Heartbeat, Bracket Strikes)...")
    from moviepy.audio.fx.all import volumex, audio_loop
    
    # Base extracted audio track
    base_audio = video_clip.audio
    audio_layers = [base_audio]
    
    sfx_dir = os.path.join(os.path.dirname(__file__), "sfx")
    
    drone_path = os.path.join(sfx_dir, "sub_bass_drone.mp3")
    if os.path.exists(drone_path):
        drone = AudioFileClip(drone_path).fx(volumex, 0.25).fx(audio_loop, duration=duration)
        audio_layers.append(drone)
        
    heart_path = os.path.join(sfx_dir, "heartbeat_monitor.mp3")
    if os.path.exists(heart_path):
        heart = AudioFileClip(heart_path).fx(volumex, 0.12).fx(audio_loop, duration=duration)
        audio_layers.append(heart)
        
    click_path = os.path.join(sfx_dir, "click.mp3")
    if os.path.exists(click_path):
        toxic_set = set(w.lower().strip() for w in toxic_words_list)
        for word_info in all_word_timestamps:
            raw_word = word_info.get("word", "").strip().lower()
            clean = re.sub(r'[^\w]', '', raw_word)
            if clean in toxic_set:
                start_t = word_info['start']
                click = AudioFileClip(click_path).fx(volumex, 0.70).set_start(start_t)
                audio_layers.append(click)
                
    final_audio = CompositeAudioClip(audio_layers)

    # 6. Save Whisper timestamps for archival/factory_floor (optional but good practice)
    timestamps_path = os.path.join(concept_folder_path, "whisper_timestamps.json")
    with open(timestamps_path, "w", encoding="utf-8") as f:
        json.dump({
            "words": all_word_timestamps,
            "toxic_words": toxic_words_list
        }, f, indent=2)

    # 7. Composite and Export
    final_video = CompositeVideoClip([video_clip] + subtitle_clips)
    final_video = final_video.set_audio(final_audio)

    final_video.write_videofile(
        final_output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="fast"
    )

    print(f"Success! Saved to {final_output_path}.")
    video_clip.close()
    final_video.close()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(override=True)

    # Inject FFmpeg path from .env into the OS PATH so whisper doesn't crash
    ffmpeg_exe = os.getenv("FFMPEG_PATH", "")
    if ffmpeg_exe and os.path.exists(ffmpeg_exe):
        ffmpeg_dir = os.path.dirname(ffmpeg_exe)
        os.environ["PATH"] += os.pathsep + ffmpeg_dir
        print(f"Injected FFmpeg to PATH: {ffmpeg_dir}")

    WORKSPACE_DIR = "niche_output"
    DRIVE_DIR = "niche_output_captioned"

    os.makedirs(DRIVE_DIR, exist_ok=True)

    if os.path.exists(WORKSPACE_DIR):
        for folder_name in os.listdir(WORKSPACE_DIR):
            if folder_name.startswith("production_"):
                folder_path = os.path.join(WORKSPACE_DIR, folder_name)
                if os.path.isdir(folder_path):
                    process_concept_folder(folder_path, DRIVE_DIR)

        print("ALL AVAILABLE MASTER REELS HAVE BEEN CAPTIONED.")
    else:
        print(f"Directory {WORKSPACE_DIR} not found.")