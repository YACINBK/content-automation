import os
os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
import re
import json
import whisper
from moviepy.editor import (
    VideoFileClip, TextClip, CompositeVideoClip,
    ImageClip, ColorClip, AudioFileClip, CompositeAudioClip
)

# --- VISUAL ASSET FILENAMES (edit here if you rename files) ---
ASSET_VIGNETTE   = "vignette.png"
ASSET_FILM_DUST  = "grunge-textured-transparent-background_53876-194736.png"
ASSET_CRT        = "glitch-overlay-vhs-static-noise-grain-texture-signal-error-dark-gray-black-fuzzy-grain-artifacts-analog-distortion-effect-rough-abstract-background_279525-11939.png"
ASSET_CAM_FRAME  = "vertical-camera-frame-video-screen-with-rec-viewfinder-display-movie-recording-surveillance_789916-9275-removebg-preview.png"

def _load_overlay(sfx_dir, filename, duration, w, h, opacity):
    """
    Safe overlay loader — loads PNG via PIL in uint8 space to avoid MoviePy's
    float64 memory blowout when stacking multiple ImageClips.
    Returns None (with a warning) if the file is missing or fails to load.
    """
    import numpy as np
    from PIL import Image

    path = os.path.join(sfx_dir, filename)
    if not os.path.exists(path):
        print(f"   [OVERLAY] WARNING: Asset not found, skipping: {filename}")
        return None
    try:
        # Open in RGBA to preserve any built-in transparency
        img = Image.open(path).convert("RGBA").resize((w, h), Image.LANCZOS)

        # Apply opacity by scaling the alpha channel (stays in uint8 — no float64 blowup)
        r, g, b, a = img.split()
        a = a.point(lambda px: int(px * opacity))
        img = Image.merge("RGBA", (r, g, b, a))

        arr = np.array(img)  # shape: (h, w, 4), dtype uint8
        clip = (ImageClip(arr, ismask=False)
                .set_duration(duration)
                .set_position(('left', 'top')))
        return clip
    except Exception as e:
        print(f"   [OVERLAY] ERROR loading {filename}: {e}")
        return None

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

    config_file = os.path.join(os.getenv("NICHE_CONFIGS_DIR", "configs"), f"{project_name}.json")
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

    sfx_dir = os.path.join(os.path.dirname(__file__), "sfx")

    # V6.3: High-Fidelity Metadata Extraction (Log Sync) - HARDENED
    script = config_data.get("narrative_script", [])
    first_line = str(script[0]) if script else "Anomaly Log 999."
    log_match = re.search(r'Log\s*(\d+)', first_line)
    log_num = log_match.group(1) if log_match else "999"
    
    # Fallback to config title for subject name, but clean it up
    title = str(config_data.get("title", "UNKNOWN SUBJECT"))
    subject_match = re.search(r':\s*([^\']+)', title)
    subject_name = subject_match.group(1).strip().upper() if subject_match else title.upper()

    toxic_words_list = extract_toxic_words_from_config(config_file)
    print(f"Toxic words detected: {toxic_words_list}")
    primary_threat = str(toxic_words_list[0]).upper() if toxic_words_list else "SYSTEM"

    # 2. Load Whisper and extract word-level timestamps
    print("Running local Whisper AI for timestamp extraction...")
    model = whisper.load_model("base")
    result = model.transcribe(master_video, word_timestamps=True)

    # 3. Setup MoviePy Video
    # V6.4: Reverting to 'Pure Blueprint' aesthetic - removing aggressive protocols
    video_clip = VideoFileClip(master_video)
    
    # We still read the outcome for the final seal
    outcome = str(config_data.get("anomaly_outcome", "STABILIZED")).upper()
    
    w, h = video_clip.size
    duration = video_clip.duration
    y_pos = int(h * 0.82)  # 82% down the screen, safe from TikTok UI
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
    print("Applying V6.1: Refined Dossier Hook Banner (Scene 1)...")
    
    # V6.2: Reduced height (18%) for a more professional, cinematic profile
    censor_height = int(h * 0.18) 
    # V5.2: Semi-transparent dark overlay for a more premium "Found Footage" look
    censor_bar = ColorClip(size=(w, censor_height), color=[10, 10, 10]) \
        .set_start(0).set_end(3.0) \
        .set_opacity(0.85) \
        .set_position(('center', 'top'))
    
    # Add a thin clinical separator line at the bottom of the banner
    separator = ColorClip(size=(w, 2), color=[57, 255, 20]) \
        .set_start(0).set_end(3.0) \
        .set_position(('center', censor_height))
    
    subtitle_clips.extend([censor_bar, separator])

    # Calculate dynamic font sizes based purely on width to prevent overflow
    fz_small = int(w * 0.030)
    fz_med = int(w * 0.040)
    fz_hook = int(w * 0.035)

    # Calculate dynamic Y-spacing evenly distributing lines across the censor bar
    y_step = censor_height / 6

    # NOTE: REC indicator is now handled by the camera frame PNG overlay (has built-in red dot)
    # No text-based blinker needed here.

    # Clinical Metadata UI - Perfectly Centered
    # V6.2: Dynamic extraction from NEW JSON fields
    meta_subject = config_data.get("subject_name", subject_name).upper()
    meta_hook = config_data.get("hook_threat", primary_threat).upper()

    meta_text1 = TextClip(f"LOG_REFERENCE: {log_num}", fontsize=fz_small, font='Courier', color='white') \
        .set_position(('center', int(y_step * 1.5))).set_start(0).set_end(3.0)
    
    meta_text2 = TextClip(f"SUBJECT_PROFILE: {meta_subject}", fontsize=fz_med, font='Courier-Bold', color='#FFFFFF') \
        .set_position(('center', int(y_step * 2.5))).set_start(0).set_end(3.0)
    
    meta_text3 = TextClip("CONTAINMENT_STATUS: COMPROMISED", fontsize=fz_small, font='Courier', color='#FFCC00') \
        .set_position(('center', int(y_step * 3.5))).set_start(0).set_end(3.0)
    
    subtitle_clips.extend([meta_text1, meta_text2, meta_text3])
 
    # High-Impact Aesthetic Hook - Strobing Neon Warning
    hook_text = f" [ CRITICAL THREAT: {meta_hook} ] "
    for i in range(4):
        start_flash = 0.8 + (i * 0.5)
        hook_clip = TextClip(hook_text, fontsize=fz_hook, font='Courier-Bold', color='#1A1A1A', bg_color='#39FF14') \
            .set_position(('center', int(y_step * 4.8))).set_start(start_flash).set_end(start_flash + 0.3)
        subtitle_clips.append(hook_clip)

    # [V5-2] Subliminal CONTAINMENT BREACH flash — 1 frame at exactly t=12s
    print("Applying V5: Subliminal CONTAINMENT BREACH flash (t=12s)...")
    if duration > 12.04:
        subliminal_bg = ColorClip(size=(w, h), color=[255, 0, 0]).set_opacity(0.8) \
            .set_start(12.0).set_end(12.04) \
            .set_position(('left', 'top'))
        subliminal_text = TextClip(
            "CONTAINMENT BREACH",
            fontsize=fz_hook, font='Courier-Bold', color='white'
        ).set_position('center').set_start(12.0).set_end(12.04)
        subtitle_clips.extend([subliminal_bg, subliminal_text])

    # [V6.5] Chrono-Clinical Visual Overlays
    # Z-ORDER (bottom to top): Vignette → Film Dust → CRT Scanlines → Camera Frame UI
    # These are loaded BEFORE subtitle_clips so they render BENEATH all text.
    print("Applying V6.5: Chrono-Clinical Visual Overlay Stack...")

    overlay_clips = []

    # Layer 1: Vignette (darkens edges, draws focus to center)
    vignette = _load_overlay(sfx_dir, ASSET_VIGNETTE, duration, w, h, opacity=0.40)
    if vignette:
        overlay_clips.append(vignette)
        print("   [OVERLAY] Vignette loaded at 40% opacity.")

    # Layer 2: Film Dust / Grunge (adds physical archival texture)
    film_dust = _load_overlay(sfx_dir, ASSET_FILM_DUST, duration, w, h, opacity=0.20)
    if film_dust:
        overlay_clips.append(film_dust)
        print("   [OVERLAY] Film Dust loaded at 20% opacity.")

    # Layer 3: CRT / VHS Scanlines (monitor distortion effect)
    crt = _load_overlay(sfx_dir, ASSET_CRT, duration, w, h, opacity=0.12)
    if crt:
        overlay_clips.append(crt)
        print("   [OVERLAY] CRT Scanlines loaded at 12% opacity.")

    # Layer 4: Camera Frame UI (viewfinder crosshair + built-in REC dot indicator)
    cam_frame = _load_overlay(sfx_dir, ASSET_CAM_FRAME, duration, w, h, opacity=0.55)
    if cam_frame:
        overlay_clips.append(cam_frame)
        print("   [OVERLAY] Camera Frame UI loaded at 55% opacity.")

    # Subtle Forensic Watermarks (go into subtitle_clips so they sit above overlays)
    watermark1 = TextClip("INTERNAL USE ONLY / CLASSIFIED", fontsize=20, font='Courier', color='white') \
        .set_opacity(0.08).set_position((int(w*0.05), int(h*0.95))).set_duration(duration)
    watermark2 = TextClip(f"LOG_ID: {log_num}", fontsize=20, font='Courier', color='white') \
        .set_opacity(0.08).set_position((int(w*0.75), int(h*0.95))).set_duration(duration)
    subtitle_clips.extend([watermark1, watermark2])

    # 5. Chrono-Clinical Audio Strategy (V5.7) — Multi-Layer Nervous System Manipulation
    print("Applying V5.7: Chrono-Clinical Audio Architecture...")
    from pydub import AudioSegment
    
    # Extract voiceover from video (already high-passed in audio_fx_engine)
    temp_voice = os.path.join(concept_folder_path, "temp_voice.wav")
    video_clip.audio.write_audiofile(temp_voice, fps=44100, nbytes=2, codec='pcm_s16le', verbose=False, logger=None)
    
    master_voice = AudioSegment.from_file(temp_voice)
    total_ms = len(master_voice)
    
    # Layer 1: The Foundation (Drone + Hiss)
    print("   [Layer 1] Foundation: Drone + Hiss (-20dB)...")
    drone = AudioSegment.from_file(os.path.join(sfx_dir, "sub_bass_drone.mp3")) - 20
    hiss = AudioSegment.from_file(os.path.join(sfx_dir, "hiss.mp3")) - 20
    foundation = drone.overlay(hiss)
    # Loop foundation to full duration
    foundation = (foundation * ((total_ms // len(foundation)) + 2))[:total_ms]
    
    # Layer 2: The Escalation Pulse (EKG 0-12s)
    print("   [Layer 2] Escalation: EKG (-12dB, Cuts at 12s)...")
    ekg = AudioSegment.from_file(os.path.join(sfx_dir, "ekg.mp3")) - 12
    ekg_loop = (ekg * ((12000 // len(ekg)) + 2))[:12000]
    ekg_loop = ekg_loop.fade_out(20) # Sharp but clean cut
    
    # Layer 3: The Micro-Stimuli Strikes (Geiger Click)
    print("   [Layer 3] Micro-Stimuli: Geiger Clicks (-15dB)...")
    # V6.4: Softened click intensity to prevent overwhelming the voice
    click_sfx = AudioSegment.from_file(os.path.join(sfx_dir, "click.mp3")) - 15
    
    # Layer 4: The 12-Second "Void" (Zap)
    print("   [Layer 4] The Void: Zap (-20dB at 12s)...")
    # V6.3 Fix: Softened to -20dB to prevent masking the voice
    zap = AudioSegment.from_file(os.path.join(sfx_dir, "glitch.mp3")) - 20
    
    # Layer 5: The Override (Typing 20s-End)
    print("   [Layer 5] The Override: Typing (-10dB at 20s+)...")
    typing_sfx = AudioSegment.from_file(os.path.join(sfx_dir, "typing.mp3")) - 10
    typing_loop = (typing_sfx * (((total_ms - 20000) // len(typing_sfx)) + 2))[:total_ms - 20000]
    
    # Master Assembly
    master_mix = foundation
    master_mix = master_mix.overlay(ekg_loop, position=0)
    master_mix = master_mix.overlay(zap, position=12000)
    if total_ms > 20000:
        master_mix = master_mix.overlay(typing_loop, position=20000)
        
    # Inject Geiger Strikes at [bracketed] words
    strike_count = 0
    for word_ts in all_word_timestamps:
        if word_ts['word'] in toxic_words_list:
            pos = int(word_ts['start'] * 1000)
            master_mix = master_mix.overlay(click_sfx, position=pos)
            strike_count += 1
    print(f"   [FX] Injected {strike_count} Geiger-Strikes.")

    # Final Layer: Overlay master voice (loudest)
    final_master_audio = master_mix.overlay(master_voice)
    
    # Export and attach
    final_audio_path = os.path.join(concept_folder_path, "chrono_clinical_master.wav")
    final_master_audio.export(final_audio_path, format="wav")
    
    final_audio = AudioFileClip(final_audio_path)
    
    # V6.2 End Polish: Professional Archive Closure "The Seal"
    linger_duration = 1.6
    final_total_duration = duration + linger_duration
    
    print(f"Applying V6.2: Final Dossier Closure Stamp (The Seal)...")
    
    # Black background clip for the end of the video
    black_bg = ColorClip(size=(w, h), color=[0, 0, 0]).set_duration(linger_duration).set_start(duration)
    
    # V6.2: "The Seal" - Centered, multi-line status report with a neon border
    seal_y = int(h * 0.45)
    seal_width = int(w * 0.85)
    seal_height = 140
    
    seal_bg = ColorClip(size=(seal_width, seal_height), color=[10, 10, 10]).set_opacity(0.95) \
        .set_start(duration).set_end(final_total_duration).set_position('center')
    
    # Decorative neon separators for the seal
    seal_border_top = ColorClip(size=(seal_width, 2), color=[57, 255, 20]) \
        .set_start(duration).set_end(final_total_duration).set_position(('center', seal_y - int(seal_height/2)))
    
    seal_border_bot = ColorClip(size=(seal_width, 2), color=[57, 255, 20]) \
        .set_start(duration).set_end(final_total_duration).set_position(('center', seal_y + int(seal_height/2)))
    
    # V6.3: Dynamic Outcome from JSON
    # outcome variable is defined at the top of the function now
    seal_content = f"LOG_ID: {log_num} / STATUS: SEALED\nANOMALY_DISPATCH: {outcome}"
    
    seal_text = TextClip(seal_content, fontsize=int(w*0.04), font='Courier-Bold', color='#39FF14', align='center') \
        .set_start(duration + 0.2).set_end(final_total_duration).set_position('center')
    
    # Add a cinematic 0.1s white "Static Flash" or "CRT Pop" at transition
    flash = ColorClip(size=(w, h), color=[255, 255, 255]).set_opacity(0.35) \
        .set_start(duration).set_end(duration + 0.08).set_position('center')
    
    subtitle_clips.extend([black_bg, seal_bg, seal_border_top, seal_border_bot, seal_text, flash])

    # Re-calculate final audio with the linger
    # (Since pydub was used, we need to make sure the foundation loop covers final_total_duration)
    # We already have final_master_audio. We can just append 1.5s of drone-only or silence.
    print(f"   [Layer 6] Master Audio: Fading out over linger period...")
    foundation_tail = (foundation * 2)[:int(linger_duration * 1000)].fade_out(int(linger_duration * 1000))
    final_master_audio = final_master_audio + foundation_tail
    
    # Export final master audio again with linger
    final_audio_path = os.path.join(concept_folder_path, "chrono_clinical_master_linger.wav")
    final_master_audio.export(final_audio_path, format="wav")
    final_audio = AudioFileClip(final_audio_path)

    # 6. Save Whisper timestamps for archival/factory_floor (optional but good practice)
    timestamps_path = os.path.join(concept_folder_path, "whisper_timestamps.json")
    with open(timestamps_path, "w", encoding="utf-8") as f:
        json.dump({
            "words": all_word_timestamps,
            "toxic_words": toxic_words_list
        }, f, indent=2)

    # 7. Composite and Export
    # STRICT Z-ORDER: base → overlays (vignette/dust/crt/cam) → subtitles/UI text
    try:
        final_video = CompositeVideoClip([video_clip] + overlay_clips + subtitle_clips)
        final_video = final_video.set_duration(final_total_duration)
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
    except Exception as e:
        print(f"CRITICAL ERROR in {project_name} rendering: {e}")
        import traceback
        traceback.print_exc()
    finally:
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