import os
import subprocess
import json
from faster_whisper import WhisperModel

FFMPEG_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"
FFPROBE_PATH = r"C:\ffmpeg\bin\ffprobe.exe"

scenes = [
    {"id": "1", "script": "The world is a relentless stream of digital noise. It is designed to fragment your focus."},
    {"id": "2", "script": "But your mind is an ancient operating system. It requires a silent foundation to run at peak capacity."},
    {"id": "3", "script": "Stop consuming the chaos. Start constructing your boundaries. Deep work is an act of war."},
    {"id": "4", "script": "Clarity is not found in the search bar. It is architected in the quiet moments between the data."},
    {"id": "5", "script": "Reclaim your hardware. Be the architect of your own silence."}
]

def format_ass_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int(round((seconds - int(seconds)) * 100))
    if centisecs == 100:
        centisecs = 99
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

def generate_tts(text, out_path):
    print(f"[*] Generating Voiceover for: {out_path}")
    # Using a deep, stoic-sounding voice for "Architect of Mind"
    voice = "en-US-SteffanNeural"
    subprocess.run(["edge-tts", "--voice", voice, "--text", text, "--write-media", out_path], check=True)

def transcribe(audio_path, model):
    print(f"[*] Transcribing: {audio_path}")
    segments, info = model.transcribe(audio_path, word_timestamps=True)
    words = []
    for segment in segments:
        for word in segment.words:
            words.append({"start": word.start, "end": word.end, "text": word.word})
    return words

def create_ass(words, ass_path):
    print(f"[*] Creating ASS Subtitles: {ass_path}")
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Brutalist,Courier New,85,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,0,2,80,80,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(ass_path, "w", encoding="utf-8-sig") as f:
        f.write(header)
        for w in words:
            s_time = format_ass_time(w['start'])
            e_time = format_ass_time(w['end'])
            # Clean text
            clean_text = w['text'].strip()
            f.write(f"Dialogue: 0,{s_time},{e_time},Brutalist,,0,0,0,,{clean_text}\\N\n")

def get_audio_duration(audio_path):
    result = subprocess.run([
        FFPROBE_PATH, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_path
    ], capture_output=True, text=True)
    return float(result.stdout.strip())

def process_scene(scene):
    sid = scene["id"]
    script = scene["script"]
    
    vid_path = f"{sid}.mp4"
    audio_path = f"vo_{sid}.mp3"
    ass_path = f"sub_{sid}.ass"
    out_path = f"final_{sid}.mp4"
    
    # 1. Generate Voiceover
    if not os.path.exists(audio_path):
        generate_tts(script, audio_path)
    
    # 2. Transcribe & get word timestamps
    if not os.path.exists(ass_path):
        words = transcribe(audio_path, whisper_model)
        create_ass(words, ass_path)
        
    # 3. Process video: scale 16:9, trim to audio length, merge audio, burn subtitles
    audio_duration = get_audio_duration(audio_path)
    safe_ass_path = ass_path.replace('\\', '/')
    
    print(f"[*] Processing Video & Burning ASS: {out_path}")
    cmd = [
        FFMPEG_PATH, "-y",
        "-i", vid_path,
        "-i", audio_path,
        "-t", str(audio_duration),
        "-vf", f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,ass='{safe_ass_path}'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        out_path
    ]
    
    subprocess.run(cmd, check=True)
    return out_path

if __name__ == "__main__":
    print("[*] Loading Faster-Whisper Model...")
    whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    
    final_files = []
    for s in scenes:
        try:
            out_file = process_scene(s)
            final_files.append(out_file)
        except Exception as e:
            print(f"[X] Failed on scene {s['id']}: {e}")
            
    # Concat all scenes
    if len(final_files) == 5:
        print("[*] Concatenating final video...")
        with open("concat_list.txt", "w") as f:
            for ff in final_files:
                f.write(f"file '{ff}'\n")
                
        concat_cmd = [
            FFMPEG_PATH, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", "concat_list.txt",
            "-c", "copy",
            "experimental_master_16x9.mp4"
        ]
        subprocess.run(concat_cmd, check=True)
        print("[OK] Finished! Created experimental_master_16x9.mp4")
