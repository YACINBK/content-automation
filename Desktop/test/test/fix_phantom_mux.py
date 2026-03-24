import os
import json
import requests
import subprocess
import argparse

def fix_mux():
    # 1. Setup paths
    out_dir = "production_phantom_vibration_1773940776"
    config_path = "configs/phantom_vibration.json"
    voicebox_url = "http://127.0.0.1:17493"
    ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
    
    with open(config_path, 'r') as f:
        config = json.load(f)
        
    narrative = config.get("narrative_script", [])
    profile_id = config.get("profile_id", "24fd0649-9d0f-450c-8749-d79301a1cb72")
    
    print("🎙️ Re-generating audio correctly...")
    audio_files = []
    
    for i, text in enumerate(narrative):
        print(f"   🗣️ text {i}: '{text[:40]}...'")
        audio_file = os.path.join(out_dir, f"audio_{i:02d}.wav")
        
        # Call Generate
        payload = {"text": text, "profile_id": profile_id}
        r = requests.post(f"{voicebox_url}/generate", json=payload)
        r.raise_for_status()
        
        data = r.json()
        gen_id = data.get("id") or data.get("generation_id")
        
        if not gen_id:
            print(f"❌ Could not find ID in response: {data}")
            return
            
        # Download Audio Binary
        print(f"   📥 Downloading audio {gen_id}...")
        audio_resp = requests.get(f"{voicebox_url}/audio/{gen_id}")
        audio_resp.raise_for_status()
        
        with open(audio_file, "wb") as f:
            f.write(audio_resp.content)
            
        audio_files.append(audio_file)
        print(f"   ✅ Saved {audio_file} ({os.path.getsize(audio_file)} bytes)")

    # 2. Mux Existing Clips
    print("⚙️ Phase 3: Hardware Muxing & Pinpoint Synchronization...")
    visual_files = [os.path.join(out_dir, f"clip_{i:02d}.mp4") for i in range(len(narrative))]
    synced_clips = []
    
    for i, (audio, video) in enumerate(zip(audio_files, visual_files)):
        if not os.path.exists(video):
            print(f"❌ Missing video clip: {video}")
            return
            
        synced_clip = os.path.join(out_dir, f"sync_{i:02d}.mp4")
        mux_cmd = [
            ffmpeg_path, "-y",
            "-i", video,
            "-i", audio,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            synced_clip
        ]
        print(f"   🎬 Muxing scene {i}...")
        subprocess.run(mux_cmd, check=True)
        synced_clips.append(synced_clip)

    # 3. Final Concatenation
    print("🔗 Phase 4: Final Master Reel Assembly...")
    concat_file = os.path.join(out_dir, "concat.txt")
    with open(concat_file, "w") as f:
        for clip in synced_clips:
            f.write(f"file '{os.path.abspath(clip)}'\n")
    
    master_output = "phantom_vibration_master_aesthetic.mp4"
    final_cmd = [
        ffmpeg_path, "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        master_output
    ]
    subprocess.run(final_cmd, check=True)
    print(f"✅ PRODUCTION COMPLETE: {master_output}")

if __name__ == "__main__":
    fix_mux()
