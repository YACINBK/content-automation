"""
Lofi Video Post-Processor: Music Overlay & Looping
=================================================

This utility handles the final stage of the video creation process:
1. Audio Selection: Picks a random track from a specified directory or uses a specific file.
2. Ping-Pong Looping: Automatically repeats the input video to match the audio duration.
   It uses a "Ping-Pong" (Forward -> Reverse) pattern to ensure seamless visual transitions.
3. Export: Merges the audio and looped video into a final high-quality .mp4 file.

Dependencies:
- moviepy
- FFmpeg (required by moviepy)
"""

import math
import os
import random
import argparse
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx, CompositeAudioClip

# Ensure FFmpeg is in the path for MoviePy
os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

def get_music_file(music_path):
    """
    Retrieves a valid music file path based on user input.
    """
    if os.path.isfile(music_path):
        return music_path
    elif os.path.isdir(music_path):
        valid_extensions = ('.mp3', '.wav', '.m4a', '.flac', '.ogg')
        files = [f for f in os.listdir(music_path) if f.lower().endswith(valid_extensions)]
        if not files:
            raise ValueError(f"No music files found in directory: {music_path}")
        
        selected_file = random.choice(files)
        print(f"Selected random music file: {selected_file}")
        return os.path.join(music_path, selected_file)
    else:
        raise ValueError(f"Music path not found: {music_path}")

def main():
    """
    Main execution flow for adding music and looping videos.
    """
    parser = argparse.ArgumentParser(description="Add background music to a video with ping-pong looping.")
    parser.add_argument("--video", required=True, help="Path to input video file (source clip)")
    parser.add_argument("--music", required=True, help="Path to music file or directory (audio source)")
    parser.add_argument("--voice", help="Path to optional voice-over audio file")
    parser.add_argument("--output", default="result.mp4", help="Path for the final processed video")
    
    args = parser.parse_args()
    
    try:
        video_path = args.video
        music_path = get_music_file(args.music)
        voice_path = args.voice
        out_path = args.output
    except Exception as e:
        print(f"Error setup: {e}")
        return

    print(f"Processing Pipeline Starting:")
    print(f"  Source Video: {video_path}")
    print(f"  Source Music: {music_path}")
    if voice_path:
        print(f"  Source Voice: {voice_path}")
    print(f"  Target File:  {out_path}")

    # STEP 1: Load and analyze the music track
    try:
        music = AudioFileClip(music_path)
        target_dur = music.duration
        print(f"  Music Duration: {target_dur:.2f}s")
    except Exception as e:
        print(f"Error loading music: {e}")
        return

    # STEP 2: Handle Voice-Over & Ducking
    final_audio = None
    if voice_path and os.path.exists(voice_path):
        print(f"🎙️ Mixing Voice-Over from: {voice_path}")
        voice = AudioFileClip(voice_path)
        
        # Reduce music volume to 20% to make voice clear
        music_background = music.with_volume_scaled(0.2)
        
        # Overlay voice on top of the softened music
        # CompositeAudioClip in v2 needs explicit duration often
        final_audio = CompositeAudioClip([music_background, voice.with_start(0)])
        final_audio = final_audio.with_duration(target_dur)
        
        print(f"✅ Audio Ducking Applied: Music (0.2) + Voice (1.0)")
    else:
        final_audio = music

    # STEP 3: Load the base video clip
    try:
        clip = VideoFileClip(video_path)
        print(f"  Base Video Duration: {clip.duration:.2f}s")
    except Exception as e:
        print(f"Error loading video: {e}")
        return

    # STEP 4: Calculate loop count
    n = math.ceil(target_dur / clip.duration)
    print(f"  Looping video {n} times using Ping-Pong logic...")

    # STEP 5: Build the "Ping-Pong" clip sequence
    segments = []
    for i in range(n):
        if i % 2 == 0:
            segment = clip
        else:
            segment = clip.with_effects([vfx.TimeMirror()]) 

        segments.append(segment)

    # STEP 6: Concatenate and attach audio
    try:
        looped = concatenate_videoclips(segments, method="chain").subclipped(0, target_dur)
        final_clip = looped.with_audio(final_audio)

        # STEP 7: Write final file
        final_clip.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=clip.fps)
        print(f"\n🎉 Successfully created: {out_path}")
        
    except Exception as e:
        print(f"Error during video processing or export: {e}")

if __name__ == "__main__":
    main()
