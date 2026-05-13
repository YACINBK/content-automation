"""
audio_fx_engine.py — V5 "Anomaly Log" Cinematic Audio Post-Processor

Processing chain per audio file:
1. Intercom Filter       — Bandpass (400Hz – 3000Hz) on the TTS voice
2. Background Mix        — Loop sub_bass_drone.mp3 (-12dB) + heartbeat_monitor.mp3 (-18dB)
3. Bracket Strike SFX    — Overlay click.mp3 at exact Whisper word timestamps

All SFX files must be placed in: sfx/
  sfx/sub_bass_drone.mp3
  sfx/heartbeat_monitor.mp3
  sfx/click.mp3

Usage:
  Standalone: python audio_fx_engine.py --input audio_00.wav [--timestamps timestamps.json]
  Module:     from audio_fx_engine import process_audio
"""

import os
import sys
import json
import argparse
from dotenv import load_dotenv

load_dotenv(override=True)

# Explicitly configure pydub to use the project's FFMPEG_PATH by adding it to PATH
ffmpeg_path = os.getenv("FFMPEG_PATH", "ffmpeg").strip("'").strip('"')
ffmpeg_dir = os.path.dirname(ffmpeg_path) if "ffmpeg.exe" in ffmpeg_path.lower() else ffmpeg_path
if ffmpeg_dir and os.path.isdir(ffmpeg_dir):
    os.environ["PATH"] += os.pathsep + ffmpeg_dir

from pydub import AudioSegment
from pydub.effects import high_pass_filter, low_pass_filter

AudioSegment.converter = ffmpeg_path


SFX_DIR = os.path.join(os.path.dirname(__file__), "sfx")

def _load_sfx(filename) -> AudioSegment | None:
    """Loads an SFX file, returning None gracefully if it doesn't exist."""
    path = os.path.join(SFX_DIR, filename)
    if not os.path.exists(path):
        print(f"   [FX] WARNING: SFX file not found, skipping: {path}")
        return None
    ext = os.path.splitext(filename)[1].lower().strip(".")
    return AudioSegment.from_file(path, format=ext)


def _loop_to_duration(segment: AudioSegment, target_ms: int) -> AudioSegment:
    """Loops an audio segment until it reaches the target duration."""
    if len(segment) == 0:
        return segment
    loops = (target_ms // len(segment)) + 2
    return (segment * loops)[:target_ms]


def process_audio(
    input_path: str,
    timestamps: list[dict] | None = None,
    toxic_words: list[str] | None = None
) -> str:
    """
    Post-processes a raw TTS .wav file through the V5 cinematic FX chain.
    
    Args:
        input_path:   Path to the raw TTS .wav file (e.g., audio_00.wav)
        timestamps:   Optional. List of {word, start, end} dicts from Whisper.
                      Used to place the Bracket Strike SFX exactly.
        toxic_words:  Optional. List of bracketed words (e.g., ['weaponized', 'algorithm']).
                      Matched against timestamps for strike placement.

    Returns:
        Path to the processed audio file (e.g., audio_00_processed.wav)
    """
    output_path = input_path.replace(".wav", "_processed.wav")

    # Skip if already processed (resume-safe)
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        print(f"   [FX] Skipping (already processed): {os.path.basename(output_path)}")
        return output_path

    print(f"   [FX] Processing: {os.path.basename(input_path)}")

    # --- STEP 1: Load raw TTS voice ---
    voice = AudioSegment.from_file(input_path)
    duration_ms = len(voice)

    # --- DYNAMIC VOICE FILTER ROUTER ---
    # Controlled by the niche.env file (e.g., VOICE_FILTER=intercom)
    voice_filter = os.getenv("VOICE_FILTER", "none").strip().lower()

    if voice_filter == "intercom":
        # --- PROFILE: INTERCOM (Bypass 400Hz-3000Hz + Overdrive) ---
        print(f"   [FX] Applying 'intercom' profile (400Hz–3000Hz bandpass + 4dB boost)...")
        voice = high_pass_filter(voice, cutoff=400)
        voice = low_pass_filter(voice, cutoff=3000)
        voice = voice + 4  # Boost volume to compensate for frequency loss
    elif voice_filter == "brutalist":
        # --- PROFILE: BRUTALIST (Tech-Stoicism) ---
        print(f"   [FX] Applying 'brutalist' profile (Normalization, Compression, Presence EQ, Saturation)...")
        
        # 1. High-pass filter at 100Hz to remove sub rumble
        voice = high_pass_filter(voice, cutoff=100)
        
        # 2. Normalize to -1dB
        from pydub.effects import normalize, compress_dynamic_range
        voice = normalize(voice, headroom=1.0)
        
        # 3. Compression: -20dB threshold, 4:1 ratio (pydub uses default ratios which are close to this)
        voice = compress_dynamic_range(voice, threshold=-20.0, ratio=4.0, attack=5.0, release=50.0)
        
        # 4. Presence EQ: +3dB boost around 4.5kHz (Simulated by slightly boosting highs overall via a second track or a simple high_pass trick, though pydub doesn't have a direct peaking EQ. We use a high pass layer mixed in to simulate presence)
        presence_layer = high_pass_filter(voice, cutoff=4000) - 3  # Add back highs slightly attenuated
        voice = voice.overlay(presence_layer)
        
        # 5. Saturation: Subtle analog clipping by boosting into hard limiting, then reducing volume
        voice = voice + 3  # drive
        # hard clip happens at 0dBFS in pydub naturally if exported, but we'll soft-clip using a custom lambda or just keep it simple.
        # Simple pydub hard limit
        def _clip(x):
            return max(-32768, min(32767, x))
        # Note: Pydub already hard-clips on export if above 0dB. 
        # We will normalize back to -1dB to retain the crushed wave.
        voice = normalize(voice, headroom=1.0)
        
        # Note: Reverb is complex in raw pydub without external ffmpeg filters. We will rely on the 0.6s room reverb via ffmpeg if possible, or just skip local reverb and add spatial echo. 
        # Simulated spatial reverb (6% wet, 0.6s delay)
        echo = voice - 24 # very quiet (~6% volume)
        voice = voice.overlay(echo, position=600) # 0.6s delay

    elif voice_filter != "none":
        print(f"   [FX] WARNING: Unknown VOICE_FILTER '{voice_filter}'. Bypassing filters.")
    else:
        print(f"   [FX] VOICE_FILTER is 'none'. Unaltered high-fidelity voice pass-through.")

    # --- STEP 3: Export ---
    voice.export(output_path, format="wav")
    print(f"   [FX] Processed audio exported -> {output_path}")

    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="V5 Anomaly Log Audio FX Engine")
    parser.add_argument("--input", required=True, help="Path to input .wav file")
    args = parser.parse_args()

    out = process_audio(args.input)
    print(f"Done! Output: {out}")
