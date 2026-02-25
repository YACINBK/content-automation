import requests
import json
import os
import argparse
import time
import subprocess
from typing import Dict, List, Optional
import math
import sys

# Support for local .env files
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Setup MetaAI Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'metaai-api'))
sys.path.insert(0, os.path.join(BASE_DIR, 'metaai-api', 'src'))

class VoiceboxStoryEngine:
    def __init__(self, config_path: str, work_dir: Optional[str] = None):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.settings = self.config.get("settings", {})
        
        # 1. Base URL & Profile (Defaults to ENV or common local port)
        self.base_url = os.getenv("VOICEBOX_BASE_URL", self.settings.get("base_url", "http://127.0.0.1:17493"))
        self.profile_id = os.getenv("DEFAULT_VOICE_ID", self.settings.get("voice_profile_id", ""))
        
        self.project_name = self.config.get("project_name", f"story_{int(time.time())}")
        
        # 2. Meta AI Cookies (Security: Prioritize .env over hardcoded JSON)
        env_cookies = os.getenv("META_COOKIES")
        self.cookies = json.loads(env_cookies) if env_cookies else self.settings.get("meta_cookies", {})
        
        # 3. Intelligent FFmpeg Detection
        self.ffmpeg_path = os.getenv("FFMPEG_PATH", self.settings.get("ffmpeg_path", "ffmpeg"))
        
        self.gothic_grade = self.config.get("gothic_grade", {})
        self.bg_music = self.settings.get("background_music")
        
        # State tracking
        self.story_id = None
        self.total_duration_ms = 0
        self.work_dir = work_dir or f"production_{self.project_name}_{int(time.time())}"
        
    def _check_env(self):
        """Verifies server, ffmpeg, and cookies before starting."""
        print(f"🔍 Environment Check...")
        
        # Check Voicebox Server
        try:
            r = requests.get(f"{self.base_url}/health", timeout=5)
            r.raise_for_status()
            print(f"   ✅ Voicebox API: Online")
        except Exception as e:
            print(f"   ❌ Voicebox API: Offline ({e})")
            return False
            
        # Check FFmpeg
        try:
            subprocess.run([self.ffmpeg_path, "-version"], capture_output=True, check=True)
            print(f"   ✅ FFmpeg: Found")
        except:
            print(f"   ❌ FFmpeg: Not found. Set FFMPEG_PATH or install to system path.")
            return False
            
        # Check Cookies
        if not self.cookies:
            print(f"   ⚠️  Warning: No Meta AI cookies found. Visual generation will fail.")
            
        return True

    def run_pipeline(self):
        if not self._check_env():
            print("🛑 Pipeline stopped due to environment issues.")
            exit(1)
            
        os.makedirs(self.work_dir, exist_ok=True)
        print(f"📁 Project Directory: {self.work_dir}")

        self.find_or_create_story()
        self.generate_audio_blueprint()
        n_scenes, scene_dur = self.calculate_visual_blueprint()
        clips = self.generate_visuals(n_scenes, scene_dur)
        self.assemble_final_reel(clips)

    def find_or_create_story(self):
        """Always creates a fresh story by deleting existing ones with the same name."""
        r = requests.get(f"{self.base_url}/stories")
        if r.status_code == 200:
            for s in r.json():
                if s['name'] == self.project_name:
                    print(f"   🧹 Cleaning up existing story: {s['id']}")
                    requests.delete(f"{self.base_url}/stories/{s['id']}").raise_for_status()
        
        payload = {"name": self.project_name, "description": self.config.get("description", "")}
        r = requests.post(f"{self.base_url}/stories", json=payload)
        r.raise_for_status()
        self.story_id = r.json()['id']
        print(f"   🎬 Fresh Story Created: {self.story_id}")

    def generate_audio_blueprint(self):
        """Generates all audio capsules and creates a sequential timeline."""
        audio_path = os.path.join(self.work_dir, "master_narration.wav")
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 100000:
            print(f"🎙️ Phase 1: Reusing valid master_narration.wav")
            return

        print(f"🎙️ Phase 1: Sequential Audio Blueprinting...")
        current_time_ms = 0
        gap_ms = self.settings.get("default_gap_ms", 300)

        for scene in self.config['scenes']:
            print(f"   🗣️ Generating: \"{scene['text'][:50]}...\"")
            gen_payload = {
                "text": scene['text'],
                "profile_id": self.profile_id,
                "temperature": self.settings.get("temperature", 1.1)
            }
            r = requests.post(f"{self.base_url}/generate", json=gen_payload)
            if r.status_code != 200:
                print(f"   ❌ Generation failed ({r.status_code}): {r.text}")
                continue
                
            res = r.json()
            gen_id = res.get("id") or res.get("generation_id")
            if not gen_id:
                print(f"   ❌ Unexpected API response: {res}")
                continue

            item_payload = {
                "generation_id": gen_id,
                "start_time_ms": current_time_ms,
                "track": 0
            }
            requests.post(f"{self.base_url}/stories/{self.story_id}/items", json=item_payload).raise_for_status()
            
            duration_ms = int(res.get('duration', 0) * 1000)
            current_time_ms += duration_ms + gap_ms
            
        self.total_duration_ms = current_time_ms
        print(f"   📊 Audio Built: {self.total_duration_ms/1000:.2f}s total duration.")

    def calculate_visual_blueprint(self):
        """Calculates N scenes and Duration D based on total audio T."""
        print(f"📐 Phase 2: Dynamic Timeline Calculation...")
        
        if self.total_duration_ms == 0:
            audio_path = os.path.join(self.work_dir, "master_narration.wav")
            if os.path.exists(audio_path):
                ffprobe_path = self.ffmpeg_path.replace("ffmpeg", "ffprobe")
                cmd = [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
                res = subprocess.run(cmd, capture_output=True, text=True)
                self.total_duration_ms = int(float(res.stdout.strip()) * 1000)

        T = self.total_duration_ms / 1000.0
        N = math.ceil(T / 5.0)
        D = T / N
        print(f"   🎬 Formula: {T:.1f}s / {N} scenes = {D:.2f}s per clip.")
        return N, D

    def generate_visuals(self, n_scenes: int, scene_dur: float):
        """Generates the required number of video clips or reuses existing."""
        print(f"🎬 Phase 3: Visual Generation Management...")
        
        clips = []
        for i in range(n_scenes):
            clip_path = os.path.join(self.work_dir, f"clip_{i:02d}.mp4")
            if os.path.exists(clip_path) and os.path.getsize(clip_path) > 10000:
                print(f"   ⏩ Reusing existing: {os.path.basename(clip_path)}")
                clips.append(clip_path)
                continue

            from metaai_api import MetaAI
            ai = MetaAI(cookies=self.cookies)
            visual_prompts = self.config.get("visual_prompts", [])
            anchor = self.config.get("anchor_block", "")
            idx = i % len(visual_prompts) if visual_prompts else 0
            prompt = f"{visual_prompts[idx]}, {anchor}"
            print(f"   🖼️ Generating Scene {i+1}/{n_scenes}...")
            
            res = ai.generate_video_new(prompt)
            if res and res.get("success") and res.get("video_urls"):
                r = requests.get(res["video_urls"][0])
                with open(clip_path, "wb") as f:
                    f.write(r.content)
                clips.append(clip_path)
            else:
                print(f"   ❌ Failed to generate scene {i+1}")
        
        return clips

    def assemble_final_reel(self, clips: List[str]):
        """Grading, Trimming, Concat, and Music Muxing."""
        print(f"🔗 Phase 4: Final Assembly & Aesthetic Sync...")
        
        audio_path = os.path.join(self.work_dir, "master_narration.wav")
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 100000:
            print(f"   💾 Exporting Master Audio from Story {self.story_id}...")
            r = requests.get(f"{self.base_url}/stories/{self.story_id}/export-audio")
            with open(audio_path, "wb") as f:
                f.write(r.content)
        else:
            print(f"   ⏩ Reusing existing master_narration.wav")

        T = self.total_duration_ms / 1000.0
        N = len(clips)
        D = T / N
        
        processed_clips = []
        for i, clip in enumerate(clips):
            base = f"sync_{i:02d}.mp4"
            if self.gothic_grade:
                base = f"grade_{i:02d}.mp4"
            
            out_clip = os.path.join(self.work_dir, base)
            vf_chain = f"trim=0:{D},setpts=PTS-STARTPTS"
            cmd = [self.ffmpeg_path, "-y", "-i", clip]
            
            if self.gothic_grade:
                g = self.gothic_grade
                grade_vf = (
                    f"eq=saturation={g.get('saturation', 1.0)}:brightness={g.get('brightness', 0.0)}:contrast={g.get('contrast', 1.0)},"
                    f"colorbalance=rs={g.get('crimson_rs', 0)}:gs={g.get('crimson_gs', 0)}:bs={g.get('crimson_bs', 0)}:rm={g.get('crimson_rm', 0)}:gm={g.get('crimson_gm', 0)}:bm={g.get('crimson_bm', 0)},"
                    f"noise=alls={g.get('grain_strength', 0)}:allf=t+u,"
                )
                vf_chain = grade_vf + vf_chain
            
            cmd += ["-vf", vf_chain, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", out_clip]
            subprocess.run(cmd, capture_output=True)
            processed_clips.append(out_clip)

        concat_file = os.path.join(self.work_dir, "concat.txt")
        with open(concat_file, "w") as f:
            for c in processed_clips:
                f.write(f"file '{os.path.abspath(c).replace('\\', '/')}'\n")
        
        silent_video = os.path.join(self.work_dir, "final_silent.mp4")
        subprocess.run([
            self.ffmpeg_path, "-y", "-f", "concat", "-safe", "0",
            "-i", concat_file, "-c", "copy", silent_video
        ], capture_output=True)

        final_output = f"{self.project_name}_master_aesthetic.mp4"
        if self.bg_music and os.path.exists(self.bg_music):
            print(f"   🎵 Mixing background music: {os.path.basename(self.bg_music)}")
            cmd = [
                self.ffmpeg_path, "-y", "-i", silent_video, "-i", audio_path, "-i", self.bg_music,
                "-filter_complex", "[2:a]volume=0.15[m];[1:a][m]amix=inputs=2:duration=first[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                final_output
            ]
        else:
            cmd = [
                self.ffmpeg_path, "-y", "-i", silent_video, "-i", audio_path,
                "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                "-shortest", final_output
            ]
            
        subprocess.run(cmd, capture_output=True)
        print(f"✨ Production Complete: {final_output}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--work-dir", default=None)
    args = parser.parse_args()

    engine = VoiceboxStoryEngine(args.config, work_dir=args.work_dir)
    engine.run_pipeline()

if __name__ == "__main__":
    main()
