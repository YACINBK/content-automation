import os
import json
import asyncio
import argparse
import requests
import subprocess
import time
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

class VoiceboxStoryEngine:
    def __init__(self, config_path, force=False):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Extract project name from the filename perfectly matching our pipeline
        base = os.path.basename(config_path)
        self.project_name = os.path.splitext(base)[0]
        # Use a persistent directory based on project name to enable resuming
        self.output_dir = os.path.join("niche_output", f"production_{self.project_name}")
        os.makedirs(self.output_dir, exist_ok=True)
        self.force = force
        
        self.story_id = None
        self.scenes = []
        self.voicebox_url = os.getenv("VOICEBOX_BASE_URL", "http://127.0.0.1:17493")
        self.ffmpeg_path = os.getenv("FFMPEG_PATH", "ffmpeg")

    async def run(self):
        print(f"🎬 Starting Production: {self.project_name}")
        print(f"📂 Output Directory: {self.output_dir}")
        if not self.force:
            print("🔄 Resume Mode Active: Will skip already generated components.")
        
        # 1. Audio Phase
        print("\n🎙️ Phase 1: Sequential Audio Blueprinting...")
        narrative = self.config.get("narrative_script", [])
        audio_files = []
        for i, text in enumerate(narrative):
            filename = os.path.join(self.output_dir, f"audio_{i:02d}.wav")
            
            # Resume Check
            if not self.force and os.path.exists(filename) and os.path.getsize(filename) > 0:
                print(f"   ⏩ Skipping Scene {i+1} Audio: Already exists ({filename})")
                audio_files.append(filename)
                continue
                
            print(f"   🗣️ Generating: \"{text[:40]}...\"")
            
            # Strip brackets reserved for toxic caption styling so TTS doesn't say them
            clean_text_for_tts = text.replace('[', '').replace(']', '')
            
            # Call Voicebox API
            payload = {
                "text": clean_text_for_tts,
                "profile_id": self.config.get("profile_id", "24fd0649-9d0f-450c-8749-d79301a1cb72")
            }
            r = requests.post(f"{self.voicebox_url}/generate", json=payload)
            if r.status_code == 200:
                data = r.json()
                gen_id = data.get("id") or data.get("generation_id")
                
                if gen_id:
                    audio_resp = requests.get(f"{self.voicebox_url}/audio/{gen_id}")
                    if audio_resp.status_code == 200:
                        with open(filename, "wb") as f:
                            f.write(audio_resp.content)
                        audio_files.append(filename)
                    else:
                        print(f"❌ Error downloading audio {gen_id}: {audio_resp.status_code}")
                        return
                else:
                    print(f"❌ Error getting ID from Voicebox Response: {data}")
                    return
            else:
                print(f"❌ Error generating audio for scene {i}: {r.status_code}")
                return

        # 2. Visual Phase (Direct T2V via Scrapling/Playwright)
        print("\n📹 Phase 2: High-Impact Visual Rendering...")
        visual_files = []
        visual_prompts = self.config.get("visual_prompts") or self.config.get("image_prompts", [])
        anchor = self.config.get("anchor_block", "")
        
        for i, prompt_core in enumerate(visual_prompts):
            output_clip = os.path.join(self.output_dir, f"clip_{i:02d}.mp4")
            
            # Resume Check
            if not self.force and os.path.exists(output_clip) and os.path.getsize(output_clip) > 0:
                print(f"   ⏩ Skipping Scene {i+1} Video: Already exists ({output_clip})")
                visual_files.append(output_clip)
                continue
                
            # --- LLM PROMPT ENHANCEMENT (THE "BRAIN" UPGRADE) ---
            from llm_handler import LLMHandler
            llm = LLMHandler()
            
            print(f"   🧠 LLM Mastering Scene {i+1} prompt...")
            full_concept = f"{prompt_core} {anchor}"
            # Ensure the prompt follows all Master Rules
            master_prompt = llm.generate_video_prompt(full_concept)
            if not master_prompt:
                print("   ⚠️ LLM failed to Master-ize. Using raw prompt as fallback.")
                master_prompt = f"Imagine a video of {full_concept}"
            
            print(f"   🎞️ Rendering Scene {i+1}/{len(visual_prompts)}...")
            print(f"   📝 Master Prompt: {master_prompt[:120]}...")
            
            cmd = [sys.executable, "meta_scrapling_video.py", "--prompt", master_prompt, "--output", output_clip]
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.wait()
            
            if os.path.exists(output_clip):
                visual_files.append(output_clip)
            else:
                print(f"❌ Error: Clip {i} was not generated.")
                return

        # 3. Dynamic Sync & Muxing
        print("\n⚙️ Phase 3: Hardware Muxing & Pinpoint Synchronization...")
        synced_clips = []
        for i, (audio, video) in enumerate(zip(audio_files, visual_files)):
            synced_clip = os.path.join(self.output_dir, f"sync_{i:02d}.mp4")
            
            # Resume Check
            if not self.force and os.path.exists(synced_clip) and os.path.getsize(synced_clip) > 0:
                print(f"   ⏩ Skipping Scene {i+1} Muxing: Already exists ({synced_clip})")
                synced_clips.append(synced_clip)
                continue
                
            print(f"   🎬 Muxing scene {i+1}...")
            mux_cmd = [
                self.ffmpeg_path, "-y",
                "-stream_loop", "-1",
                "-i", video,
                "-i", audio,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                synced_clip
            ]
            subprocess.run(mux_cmd, check=True, capture_output=True)
            synced_clips.append(synced_clip)

        # 4. Final Concatenation
        print("\n🔗 Phase 4: Final Master Reel Assembly...")
        concat_file = os.path.join(self.output_dir, "concat.txt")
        with open(concat_file, "w") as f:
            for clip in synced_clips:
                # Critical Windows FFmpeg fix: Replace backslashes with forward slashes
                safe_path = os.path.abspath(clip).replace('\\', '/')
                f.write(f"file '{safe_path}'\n")
        
        # --- MODULARITY FIX ---
        master_output = os.path.join(self.output_dir, f"{self.project_name}_master_aesthetic.mp4")
        
        final_cmd = [
            self.ffmpeg_path, "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            master_output
        ]
        subprocess.run(final_cmd, check=True)
        print(f"\n✅ PRODUCTION COMPLETE: {master_output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to production config JSON")
    parser.add_argument("--force", action="store_true", help="Force regenerate all components, ignoring cache")
    args = parser.parse_args()
    engine = VoiceboxStoryEngine(args.config, force=args.force)
    asyncio.run(engine.run())
