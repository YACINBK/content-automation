import os
os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
import re
import json
import whisper
from moviepy.editor import (
    VideoFileClip, TextClip, CompositeVideoClip,
    ImageClip, ColorClip, AudioFileClip, CompositeAudioClip
)

# --- PROFILE SETTINGS ---
# Reads environment variables injected per-niche by run.py
VISUAL_PROFILE   = os.getenv("VISUAL_PROFILE", "none").strip().lower()
NICHE_ASSETS_DIR = os.getenv("NICHE_ASSETS_DIR", "")
SFX_DIR          = os.path.join(os.path.dirname(__file__), "sfx")

# --- VISUAL ASSET FILENAMES ---
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

    # Strategy Puzzle Pieces
    hook_name = os.getenv("META_HOOK_NAME", "Log")
    
    script = config_data.get("narrative_script", [])
    first_line = str(script[0]) if script else f"{hook_name} 999."
    
    # Extract number (e.g. 'Log 123' or 'Record 123')
    num_match = re.search(rf'{hook_name}\s*(\d+)', first_line, re.I)
    hook_num = num_match.group(1) if num_match else config_data.get("hook_num", "999")
    
    # Fallback to config title for subject name, but clean it up
    title = str(config_data.get("title", "UNKNOWN SUBJECT"))
    subject_match = re.search(r':\s*([^\']+)', title)
    subject_name = subject_match.group(1).strip().upper() if subject_match else title.upper()

    toxic_words_list = extract_toxic_words_from_config(config_file)
    print(f"Toxic words detected: {toxic_words_list}")
    primary_threat = str(toxic_words_list[0]).upper() if toxic_words_list else "SYSTEM"

    # 2. Load Whisper and extract word-level timestamps
    print("Running local faster-whisper AI for high-speed timestamp extraction...")
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8") # Update to cuda/float16 if GPU is available
    segments, info = model.transcribe(master_video, word_timestamps=True)

    # 3. Setup MoviePy Video
    # V6.4: Reverting to 'Pure Blueprint' aesthetic - removing aggressive protocols
    video_clip = VideoFileClip(master_video)
    
    w, h = video_clip.size
    duration = video_clip.duration
    y_pos = int(h * 0.82)
    
    # We read the status from JSON (generated by the new modular LLM)
    outcome = str(config_data.get("status", "STABILIZED")).upper()

    subtitle_clips = []
    all_word_timestamps = []  # Collect for audio FX engine use

    # 4. Generate the Typewriter Captions
    print("Burning retro-clinical captions onto video...")

    for segment in segments:
        for word_info in segment.words:
            raw_word = word_info.word.strip()
            clean_word = re.sub(r'[^\w\s]', '', raw_word.lower())

            # Collect timestamps for the audio FX engine
            all_word_timestamps.append({
                "word": clean_word,
                "start": word_info.start,
                "end": word_info.end
            })

            # 4. COLOR ROUTER: THEME-DRIVEN UNIVERSAL RULES
            # Universal Rule: [brackets] highlight words. Profile governs font/colors.
            if VISUAL_PROFILE == "chrono-clinical":
                fnt = 'Courier-Bold'
                fz  = 45
                color_toxic = '#39FF14' # Neon Green
                color_cta   = '#FFD700' # Gold
                color_base  = '#F5F5DC' # Clinical Beige
            elif VISUAL_PROFILE == "brutalist":
                fnt = 'Arial-Black' # A heavy sans-serif. Update to Inter/Archivo Black if installed system-wide
                fz  = 65          # Larger heavy font
                color_toxic = '#D4AF37' # Soft Gold (Power Word Trigger)
                color_cta   = '#FFFFFF' 
                color_base  = '#FFFFFF' # Pure White
                y_pos = int(h * 0.45)   # Centered y_pos=0.45 as requested
            else:
                # Default clean profile: Elegant/Modern look
                fnt = 'Arial-Bold'
                fz  = 55
                color_toxic = '#FFCC00' # Impact Yellow
                color_cta   = '#00FF00' # Success Green
                color_base  = '#FFFFFF' # Pure White

            if clean_word in toxic_words_list:
                text_color = color_toxic
                sw = 2.5 if VISUAL_PROFILE == "chrono-clinical" else 2.0
                fz_active = int(fz * 1.2) # Active Word Scaling (1.2x) for power words
            else:
                text_color = color_base
                sw = 1.5
                fz_active = int(fz * 1.2) # Apply 1.2x scale to ALL active words as requested for the global caption logic

            start_t = word_info.start
            end_t = word_info.end

            # Shadow layer (Universal for readability)
            shadow = TextClip(raw_word, fontsize=fz_active, font=fnt, color='black') \
                .set_position(('center', y_pos + 4)).set_start(start_t).set_end(end_t)

            # Main text
            # Brutalist specific: Add a pseudo-glow using an extra stroke layer if it's a power word
            if VISUAL_PROFILE == "brutalist" and clean_word in toxic_words_list:
                glow = TextClip(raw_word, fontsize=fz_active, font=fnt,
                                color=text_color, stroke_color='#D4AF37', stroke_width=6) \
                    .set_position(('center', y_pos)).set_start(start_t).set_end(end_t).set_opacity(0.4)
                subtitle_clips.append(glow)

            main_text = TextClip(raw_word, fontsize=fz_active, font=fnt,
                                 color=text_color, stroke_color='black', stroke_width=sw) \
                .set_position(('center', y_pos)).set_start(start_t).set_end(end_t)

            subtitle_clips.extend([shadow, main_text])

    # --- VISUAL PROFILE ROUTER ---
    # Only inject specific overlays and banners if the profile matches
    overlay_clips = []

    if VISUAL_PROFILE == "chrono-clinical":
        # [V5-1] Scene 1 Dossier Banner
        print("Applying V6.1: Refined Dossier Hook Banner (Scene 1)...")
        censor_height = int(h * 0.18) 
        censor_bar = ColorClip(size=(w, censor_height), color=[10, 10, 10]).set_start(0).set_end(3.0).set_opacity(0.85).set_position(('center', 'top'))
        separator  = ColorClip(size=(w, 2), color=[57, 255, 20]).set_start(0).set_end(3.0).set_position(('center', censor_height))
        subtitle_clips.extend([censor_bar, separator])

        fz_small = int(w * 0.030)
        fz_med   = int(w * 0.040)
        fz_hook  = int(w * 0.035)
        y_step   = censor_height / 6

        meta_subject = config_data.get("subject_name", subject_name).upper()
        meta_hook    = config_data.get("hook_threat", primary_threat).upper()

        meta_text1 = TextClip(f"{hook_name.upper()}_REFERENCE: {hook_num}", fontsize=fz_small, font='Courier', color='white').set_position(('center', int(y_step * 1.5))).set_start(0).set_end(3.0)
        meta_text2 = TextClip(f"SUBJECT_PROFILE: {meta_subject}", fontsize=fz_med, font='Courier-Bold', color='#FFFFFF').set_position(('center', int(y_step * 2.5))).set_start(0).set_end(3.0)
        meta_text3 = TextClip("CONTAINMENT_STATUS: COMPROMISED", fontsize=fz_small, font='Courier', color='#FFCC00').set_position(('center', int(y_step * 3.5))).set_start(0).set_end(3.0)
        subtitle_clips.extend([meta_text1, meta_text2, meta_text3])

        hook_text = f" [ CRITICAL THREAT: {meta_hook} ] "
        for i in range(4):
            start_flash = 0.8 + (i * 0.5)
            hook_clip = TextClip(hook_text, fontsize=fz_hook, font='Courier-Bold', color='#1A1A1A', bg_color='#39FF14').set_position(('center', int(y_step * 4.8))).set_start(start_flash).set_end(start_flash + 0.3)
            subtitle_clips.append(hook_clip)

        if duration > 12.04:
            subl_bg = ColorClip(size=(w, h), color=[255, 0, 0]).set_opacity(0.8).set_start(12.0).set_end(12.04).set_position(('left', 'top'))
            subl_tx = TextClip("CONTAINMENT BREACH", fontsize=fz_hook, font='Courier-Bold', color='white').set_position('center').set_start(12.0).set_end(12.04)
            subtitle_clips.extend([subl_bg, subl_tx])

        # Layers: Vignette → Film Dust → CRT Scanlines → Camera Frame UI
        print("Applying Chrono-Clinical Visual Overlays...")
        vignette = _load_overlay(SFX_DIR, ASSET_VIGNETTE, duration, w, h, opacity=0.40)
        if vignette: overlay_clips.append(vignette)
        film_dust = _load_overlay(SFX_DIR, ASSET_FILM_DUST, duration, w, h, opacity=0.20)
        if film_dust: overlay_clips.append(film_dust)
        crt = _load_overlay(SFX_DIR, ASSET_CRT, duration, w, h, opacity=0.12)
        if crt: overlay_clips.append(crt)
        cam_frame = _load_overlay(SFX_DIR, ASSET_CAM_FRAME, duration, w, h, opacity=0.55)
        if cam_frame: overlay_clips.append(cam_frame)

        watermark1 = TextClip(f"INTERNAL USE ONLY / {hook_name.upper()}", fontsize=20, font='Courier', color='white').set_opacity(0.08).set_position((int(w*0.05), int(h*0.95))).set_duration(duration)
        watermark2 = TextClip(f"RE_ID: {hook_num}", fontsize=20, font='Courier', color='white').set_opacity(0.08).set_position((int(w*0.75), int(h*0.95))).set_duration(duration)
        subtitle_clips.extend([watermark1, watermark2])
    
    elif VISUAL_PROFILE != "none":
        print(f"Warning: Unknown VISUAL_PROFILE '{VISUAL_PROFILE}'. Skipping overlays.")
    else:
        print("VISUAL_PROFILE is 'none'. Rendering clean high-fidelity video.")

    # --- DYNAMIC AUDIO ROUTER ---
    # Universal Rules: Strike SFX (local strike.mp3 or fallback) + BGM (bgm.mp3 if found)
    print("Applying Dynamic Audio Engine...")
    from pydub import AudioSegment
    
    # Load Voiceover
    temp_voice = os.path.join(concept_folder_path, "temp_voice.wav")
    video_clip.audio.write_audiofile(temp_voice, fps=44100, nbytes=2, codec='pcm_s16le', verbose=False, logger=None)
    master_voice = AudioSegment.from_file(temp_voice)
    total_ms = len(master_voice)
    
    # 1. UNIVERSAL BGM SYSTEM: Look for niche/assets/bgm.mp3
    bgm_path = os.path.join(NICHE_ASSETS_DIR, "bgm.mp3")
    if os.path.exists(bgm_path):
        print(f"   [AUDIO] Found niche BGM: {os.path.basename(bgm_path)}")
        niche_bgm = AudioSegment.from_file(bgm_path) - 15 # Mix BGM at -15dB
        master_mix = (niche_bgm * ((total_ms // len(niche_bgm)) + 2))[:total_ms]
    else:
        print("   [AUDIO] No niche BGM found. Using silent base.")
        master_mix = AudioSegment.silent(duration=total_ms)

    # 2. UNIVERSAL STRIKE SYSTEM: Look for niche/assets/strike.mp3, fallback to root/sfx/click.mp3
    custom_strike = os.path.join(NICHE_ASSETS_DIR, "strike.mp3")
    fallback_strike = os.path.join(SFX_DIR, "click.mp3")
    strike_path = custom_strike if os.path.exists(custom_strike) else fallback_strike
    strike_sfx = AudioSegment.from_file(strike_path) - 15
    print(f"   [AUDIO] Strike SFX source: {os.path.basename(strike_path)}")

    # 3. PROFILE WRAPPERS: Inject niche-exclusive soundscapes
    if VISUAL_PROFILE == "chrono-clinical":
        print("   [AUDIO] Injecting Chrono-Clinical SFX Stack (Fdn, EKG, Zap, Typing)...")
        drone = AudioSegment.from_file(os.path.join(SFX_DIR, "sub_bass_drone.mp3")) - 20
        hiss = AudioSegment.from_file(os.path.join(SFX_DIR, "hiss.mp3")) - 20
        fdn = (drone.overlay(hiss) * ((total_ms // 1000) + 2))[:total_ms]
        master_mix = master_mix.overlay(fdn)

        # Layers: EKG (0-12s), Zap (12s), Typing (20s+)
        ekg = AudioSegment.from_file(os.path.join(SFX_DIR, "ekg.mp3")) - 12
        master_mix = master_mix.overlay((ekg * 5)[:12000].fade_out(20), position=0)
        zap = AudioSegment.from_file(os.path.join(SFX_DIR, "glitch.mp3")) - 20
        master_mix = master_mix.overlay(zap, position=12000)
        if total_ms > 20000:
            typ = AudioSegment.from_file(os.path.join(SFX_DIR, "typing.mp3")) - 10
            master_mix = master_mix.overlay((typ * 10)[:total_ms - 20000], position=20000)
    
    # 4. INJECT STRIKES: Universal rule for ALL niches
    strike_count = 0
    for word_ts in all_word_timestamps:
        if word_ts['word'] in toxic_words_list:
            pos = int(word_ts['start'] * 1000)
            master_mix = master_mix.overlay(strike_sfx, position=pos)
            strike_count += 1
    print(f"   [AUDIO] Injected {strike_count} Universal Strikes.")

    # Final Layer: Overlay master voice (loudest)
    final_master_audio = master_mix.overlay(master_voice)
    
    # Export and attach
    final_audio_path = os.path.join(concept_folder_path, "master_mixed_audio_base.wav")
    final_master_audio.export(final_audio_path, format="wav")
    
    final_audio = AudioFileClip(final_audio_path)
    
    if VISUAL_PROFILE == "chrono-clinical":
        linger_duration = 1.6
        final_total_duration = duration + linger_duration
        print(f"Applying Archive Closure Stamp (The Seal)...")
        
        black_bg = ColorClip(size=(w, h), color=[0, 0, 0]).set_duration(linger_duration).set_start(duration)
        seal_y = int(h * 0.45)
        seal_width = int(w * 0.85)
        seal_height = 140
        seal_bg = ColorClip(size=(seal_width, seal_height), color=[10, 10, 10]).set_opacity(0.95).set_start(duration).set_end(final_total_duration).set_position('center')
        
        seal_border_top = ColorClip(size=(seal_width, 2), color=[57, 255, 20]).set_start(duration).set_end(final_total_duration).set_position(('center', seal_y - int(seal_height/2)))
        seal_border_bot = ColorClip(size=(seal_width, 2), color=[57, 255, 20]).set_start(duration).set_end(final_total_duration).set_position(('center', seal_y + int(seal_height/2)))
        
        seal_content = f"{hook_name.upper()}_ID: {hook_num} / STATUS: SEALED\nDISPATCH: {outcome}"
        seal_text = TextClip(seal_content, fontsize=int(w*0.04), font='Courier-Bold', color='#39FF14', align='center').set_start(duration + 0.2).set_end(final_total_duration).set_position('center')
        flash = ColorClip(size=(w, h), color=[255, 255, 255]).set_opacity(0.35).set_start(duration).set_end(duration + 0.08).set_position('center')
        
        subtitle_clips.extend([black_bg, seal_bg, seal_border_top, seal_border_bot, seal_text, flash])
    else:
        # Standard Clean Closure
        linger_duration = 0.5
        final_total_duration = duration + linger_duration
        black_bg = ColorClip(size=(w, h), color=[0, 0, 0]).set_duration(linger_duration).set_start(duration)
        subtitle_clips.append(black_bg)
    

    # Re-calculate final audio with the linger
    # (Since pydub was used, we need to make sure the foundation loop covers final_total_duration)
    # We already have final_master_audio. We can just append 1.5s of drone-only or silence.
    print(f"   [Layer 6] Master Audio: Fading out over linger period...")
    if "niche_bgm" in locals():
        foundation_tail = (niche_bgm * 2)[:int(linger_duration * 1000)].fade_out(int(linger_duration * 1000))
    else:
        foundation_tail = AudioSegment.silent(duration=int(linger_duration * 1000))
        
    final_master_audio = final_master_audio + foundation_tail
    
    # Export final master audio again with linger
    final_audio_path = os.path.join(concept_folder_path, "master_mixed_audio.wav")
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
            preset="fast",
            logger=None
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