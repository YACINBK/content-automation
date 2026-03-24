import os
os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
import re
import json
import whisper
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

def extract_toxic_words_from_config(config_path):
    """Reads the JSON config and extracts words wrapped in [brackets]."""
    if not os.path.exists(config_path):
        return ["pov"] # Default

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

    # 1. Get the Toxic Words List from JSON config
    toxic_words_list = extract_toxic_words_from_config(config_file)
    print(f"Toxic words detected: {toxic_words_list}")

    # 2. Load Whisper and extract word-level timestamps
    print("Running local Whisper AI for timestamp extraction...")
    model = whisper.load_model("base") # Use 'small' or 'medium' if you want higher accuracy
    
    # word_timestamps=True is the golden ticket here
    result = model.transcribe(master_video, word_timestamps=True)
    
    # 3. Setup MoviePy Video
    video_clip = VideoFileClip(master_video)
    w, h = video_clip.size
    y_pos = int(h * 0.82) # 82% down the screen, safe from TikTok UI
    
    subtitle_clips = []
    
    # 4. Generate the Typewriter Captions
    print("Burning retro-clinical captions onto video...")
    total_segments = len(result['segments'])
    
    for i, segment in enumerate(result['segments']):
        # CTA = last 2 segments (roughly 4-7 seconds). 'bio' keyword check was causing false positives.
        is_cta = (i >= total_segments - 2)
        
        for word_info in segment.get('words', []):
            raw_word = word_info['word'].strip()
            clean_word = re.sub(r'[^\w\s]', '', raw_word.lower())
            
            # Color logic:
            # Last segment (CTA) → Gold
            # Toxic/POV word      → Neon Green
            # Everything else     → Clinical Beige
            if is_cta:
                text_color = '#FFD700'
            elif clean_word in toxic_words_list:
                text_color = '#39FF14'
            else:
                text_color = '#F5F5DC'
            
            start_t = word_info['start']
            end_t = word_info['end']
            
            # Shadow layer — offset 4px down for depth
            shadow = TextClip(raw_word, fontsize=45, font='Courier-Bold', color='black')\
                     .set_position(('center', y_pos + 4)).set_start(start_t).set_end(end_t)
            
            # Main text — stroke for contrast on white/off-white backgrounds
            main_text = TextClip(raw_word, fontsize=45, font='Courier-Bold', color=text_color,
                                 stroke_color='black', stroke_width=1.5)\
                        .set_position(('center', y_pos)).set_start(start_t).set_end(end_t)
            
            subtitle_clips.extend([shadow, main_text])
            
    # 5. Composite and Export
    final_video = CompositeVideoClip([video_clip] + subtitle_clips)
    
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
    # Removed rmtree to allow archiving the non-captioned master reels if desired

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    # Inject FFmpeg path from .env into the OS PATH so whisper doesn't crash
    ffmpeg_exe = os.getenv("FFMPEG_PATH", "")
    if ffmpeg_exe and os.path.exists(ffmpeg_exe):
        ffmpeg_dir = os.path.dirname(ffmpeg_exe)
        os.environ["PATH"] += os.pathsep + ffmpeg_dir
        print(f"Injected FFmpeg to PATH: {ffmpeg_dir}")

    # Define your directories based on the new pipeline
    WORKSPACE_DIR = "niche_output"
    DRIVE_DIR = "niche_output_captioned"
    
    os.makedirs(DRIVE_DIR, exist_ok=True)
    
    # Loop through every production folder in the output directory
    if os.path.exists(WORKSPACE_DIR):
        for folder_name in os.listdir(WORKSPACE_DIR):
            if folder_name.startswith("production_"):
                folder_path = os.path.join(WORKSPACE_DIR, folder_name)
                if os.path.isdir(folder_path):
                    process_concept_folder(folder_path, DRIVE_DIR)
                    
        print("ALL AVAILABLE MASTER REELS HAVE BEEN CAPTIONED.")
    else:
        print(f"Directory {WORKSPACE_DIR} not found.")