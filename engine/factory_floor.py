import os
import sys
import glob
import json
import asyncio
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

# Import our custom engines
from llm_handler import LLMHandler
from meta_scrapling_video import run_automation
from master_caption_engine import process_concept_folder
from audio_fx_engine import process_audio as apply_audio_fx

load_dotenv(override=True)

# --- CONFIGURATION ---
# Strip any accidental surrounding quotes that dotenv sometimes adds on Windows
VOICEBOX_URL = os.getenv("VOICEBOX_BASE_URL", "http://127.0.0.1:17493").strip("'").strip('"')
FFMPEG_PATH  = os.getenv("FFMPEG_PATH", "ffmpeg").strip("'").strip('"')
# Niche-injectable paths: run.py sets these at runtime. Legacy fallbacks keep direct execution working.
CONFIGS_DIR  = os.getenv("NICHE_CONFIGS_DIR",   "configs")
WORKSPACE_DIR = os.getenv("NICHE_WORKSPACE_DIR", "niche_output")
DRIVE_DIR    = os.getenv("NICHE_CAPTIONED_DIR",  "niche_output_captioned")
# How many concepts to produce per factory run. Upload scheduler drips them 3/day independently.
DAILY_PRODUCTION_LIMIT = int(os.getenv("DAILY_PRODUCTION_LIMIT", "4"))

# Important: Inject FFmpeg into system path so Whisper can find it when imported
if FFMPEG_PATH and os.path.exists(FFMPEG_PATH):
    ffmpeg_dir = os.path.dirname(FFMPEG_PATH)
    if ffmpeg_dir not in os.environ["PATH"]:
        os.environ["PATH"] += os.pathsep + ffmpeg_dir
        print(f"[{os.path.basename(__file__)}] Injected FFmpeg to PATH: {ffmpeg_dir}")

# Concurrency Limits (Extreme Resilience V6.5.3)
# To avoid Meta AI anti-bot timeouts and concurrency drops, EVERYTHING is purely sequential.
# Reliability > Speed
MAX_AUDIO_WORKERS = 1
MAX_VISUAL_WORKERS = 1
MAX_MUX_WORKERS = 1
MAX_CONCAT_WORKERS = 1

os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(DRIVE_DIR, exist_ok=True)

# --- QUEUES & STATE ---
audio_queue = asyncio.Queue()
visual_queue = asyncio.Queue()
mux_queue = asyncio.Queue()
concat_queue = asyncio.Queue()

# Thread-safe LLM handler
llm_handler = LLMHandler()

# Global tracking dictionary
# { project_name: { "total_scenes": 5, "scenes": { idx: {"audio": bool, "visual": bool, "muxed": bool} }, "muxed_count": int } }
tracker = {}
tracker_lock = asyncio.Lock()


# --- WORKERS ---

async def audio_worker(worker_id):
    while True:
        task = await audio_queue.get()
        try:
            if task is None:
                break
                
            project_name, scene_idx, cfg = task
            output_dir = os.path.join(WORKSPACE_DIR, f"production_{project_name}")
            os.makedirs(output_dir, exist_ok=True)
            
            output_file = os.path.join(output_dir, f"audio_{scene_idx:02d}.wav")
            
            narrative = cfg.get("narrative_script", [])
            text = narrative[scene_idx]
            audio_ready = False
            
            # Resume Check
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                print(f"[A-W{worker_id}] SKIPPING {project_name} S{scene_idx+1} Audio: Already exists")
                audio_ready = True
            else:
                print(f"[A-W{worker_id}] GENERATING {project_name} S{scene_idx+1}: {text[:30]}...")
                clean_text = text.replace('[', '').replace(']', '')
                payload = {
                    "text": clean_text,
                    "profile_id": os.getenv("VOICEBOX_PROFILE_ID", cfg.get("profile_id", "66cee046-6d00-4055-9cfe-4fe9ca8637c9"))
                }
                
                # V6.5.1: Robust Retry Loop for API Stability
                import time
                max_retries = 3
                success = False
                for attempt in range(max_retries):
                    try:
                        loop = asyncio.get_running_loop()
                        # V6.5.2: Increased timeout to 60s (server takes ~17s under normal load)
                        r = await loop.run_in_executor(None, lambda: requests.post(f"{VOICEBOX_URL}/generate", json=payload, timeout=60))
                        
                        if r.status_code == 200:
                            data = r.json()
                            gen_id = data.get("id") or data.get("generation_id")
                            if gen_id:
                                a_resp = await loop.run_in_executor(None, lambda: requests.get(f"{VOICEBOX_URL}/audio/{gen_id}", timeout=30))
                                if a_resp.status_code == 200:
                                    with open(output_file, "wb") as f:
                                        f.write(a_resp.content)
                                    success = True
                                    audio_ready = True
                                    break
                    except Exception as try_err:
                        print(f"[A-W{worker_id}] Attempt {attempt+1} failed: {try_err}")
                    
                    print(f"[A-W{worker_id}] Retrying {project_name} S{scene_idx+1} in 2s...")
                    await asyncio.sleep(2)
                
                if not success:
                    print(f"[A-W{worker_id}] ❌ FATAL: Failed {project_name} S{scene_idx+1} after 3 attempts")

            # V5: Run Audio FX Engine on the raw TTS file (intercom filter + background layers)
            if audio_ready and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                try:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, lambda: apply_audio_fx(output_file))
                except Exception as fx_err:
                    print(f"[A-W{worker_id}] WARNING: Audio FX failed (using raw): {fx_err}")

            async with tracker_lock:
                tracker[project_name]["scenes"][scene_idx]["audio"] = audio_ready and os.path.exists(output_file) and os.path.getsize(output_file) > 0
                if tracker[project_name]["scenes"][scene_idx]["audio"] and tracker[project_name]["scenes"][scene_idx]["visual"]:
                    mux_queue.put_nowait((project_name, scene_idx, cfg))

        except Exception as e:
            print(f"[A-W{worker_id}] ERROR: {e}")
        finally:
            audio_queue.task_done()


async def visual_worker(worker_id):
    while True:
        task = await visual_queue.get()
        try:
            if task is None:
                break
                
            project_name, scene_idx, cfg = task
            output_dir = os.path.join(WORKSPACE_DIR, f"production_{project_name}")
            os.makedirs(output_dir, exist_ok=True)
            
            output_file = os.path.join(output_dir, f"clip_{scene_idx:02d}.mp4")
            
            prompts = cfg.get("visual_prompts") or cfg.get("image_prompts", [])
            if scene_idx >= len(prompts):
                print(f"[V-W{worker_id}] ERROR: Missing visual prompt for {project_name} S{scene_idx+1}. Skipping scene.")
                continue
            prompt_core = prompts[scene_idx]
            anchor = cfg.get("anchor_block", "")
            
            # Resume Check
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                print(f"[V-W{worker_id}] SKIPPING {project_name} S{scene_idx+1} Video: Already exists")
            else:
                print(f"[V-W{worker_id}] LLM Meta-Mastering {project_name} S{scene_idx+1}...")
                full_concept = f"{prompt_core} {anchor}"
                
                # Async LLM Call
                loop = asyncio.get_running_loop()
                master_prompt = await loop.run_in_executor(None, llm_handler.generate_video_prompt, full_concept)
                if not master_prompt:
                    master_prompt = f"Imagine a video of {full_concept}"
                    
                print(f"[V-W{worker_id}] Video Rendering {project_name} S{scene_idx+1} on Meta AI...")
                
                # Single-instance automation call to protect account (concurrency handled by queue pools)
                # HEADLESS = FALSE so the user can see and debug the Meta AI session tab interactively
                success = await run_automation(master_prompt, output_file, headless=False)
                if not success:
                    print(f"[V-W{worker_id}] ERROR: Failed to generate video for {project_name} S{scene_idx+1}")

            # If file exists now, update tracker
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                async with tracker_lock:
                    tracker[project_name]["scenes"][scene_idx]["visual"] = True
                    if tracker[project_name]["scenes"][scene_idx]["audio"]:
                        mux_queue.put_nowait((project_name, scene_idx, cfg))

        except Exception as e:
            print(f"[V-W{worker_id}] ERROR: {e}")
        finally:
            visual_queue.task_done()


async def mux_worker(worker_id):
    while True:
        task = await mux_queue.get()
        try:
            if task is None:
                break
                
            project_name, scene_idx, cfg = task
            output_dir = os.path.join(WORKSPACE_DIR, f"production_{project_name}")
            
            # V5: Use the FX-processed audio if it exists, fall back to raw
            raw_audio_file = os.path.join(output_dir, f"audio_{scene_idx:02d}.wav")
            processed_audio = raw_audio_file.replace(".wav", "_processed.wav")
            audio_file = processed_audio if os.path.exists(processed_audio) and os.path.getsize(processed_audio) > 0 else raw_audio_file
            video_file = os.path.join(output_dir, f"clip_{scene_idx:02d}.mp4")
            synced_file = os.path.join(output_dir, f"sync_{scene_idx:02d}.mp4")
            mux_success = False

            if not (os.path.exists(video_file) and os.path.getsize(video_file) > 0):
                print(f"[M-W{worker_id}] ERROR: Missing video for {project_name} S{scene_idx+1}.")
                continue
            if not (os.path.exists(audio_file) and os.path.getsize(audio_file) > 0):
                print(f"[M-W{worker_id}] ERROR: Missing audio for {project_name} S{scene_idx+1}.")
                continue
            
            # Resume Check
            if os.path.exists(synced_file) and os.path.getsize(synced_file) > 0:
                print(f"[M-W{worker_id}] SKIPPING {project_name} S{scene_idx+1} Muxing: Already exists")
                mux_success = True
            else:
                print(f"[M-W{worker_id}] MUXING {project_name} S{scene_idx+1}...")
                mux_cmd = [
                    FFMPEG_PATH, "-y",
                    "-stream_loop", "-1",
                    "-i", video_file,
                    "-i", audio_file,
                    "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k",
                    "-shortest",
                    synced_file
                ]
                proc = await asyncio.create_subprocess_exec(*mux_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                await proc.wait()
                mux_success = proc.returncode == 0 and os.path.exists(synced_file) and os.path.getsize(synced_file) > 0
                if not mux_success:
                    print(f"[M-W{worker_id}] ERROR: FFmpeg mux failed for {project_name} S{scene_idx+1} (code={proc.returncode}).")

            # Update master tracker
            async with tracker_lock:
                if mux_success and not tracker[project_name]["scenes"][scene_idx]["muxed"]:
                    tracker[project_name]["scenes"][scene_idx]["muxed"] = True
                    tracker[project_name]["muxed_count"] += 1
                    if tracker[project_name]["muxed_count"] == tracker[project_name]["total_scenes"]:
                        concat_queue.put_nowait((project_name, cfg))

        except Exception as e:
            print(f"[M-W{worker_id}] ERROR: {e}")
        finally:
            mux_queue.task_done()


async def concat_worker(worker_id):
    while True:
        task = await concat_queue.get()
        try:
            if task is None:
                break
                
            project_name, cfg = task
            output_dir = os.path.join(WORKSPACE_DIR, f"production_{project_name}")
            concat_manifest = os.path.join(output_dir, "concat.txt")
            master_file_path = os.path.join(output_dir, f"{project_name}_master_aesthetic.mp4")
            
            # Compile manifest
            total_scenes = tracker[project_name]["total_scenes"]
            with open(concat_manifest, "w") as f:
                for i in range(total_scenes):
                    synced_clip = os.path.join(output_dir, f"sync_{i:02d}.mp4")
                    safe_path = os.path.abspath(synced_clip).replace('\\', '/')
                    f.write(f"file '{safe_path}'\n")
                    
            print(f"[C-W{worker_id}] Assembling Master Reel: {project_name}...")
            
            concat_cmd = [
                FFMPEG_PATH, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_manifest,
                "-c", "copy",
                master_file_path
            ]
            proc = await asyncio.create_subprocess_exec(*concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            await proc.wait()
            
            if os.path.exists(master_file_path):
                print(f"[C-W{worker_id}] SUCCESS: Master Reel Assembled: {project_name}")
                print(f"[C-W{worker_id}] Auto-Triggering Whisper Caption Engine...")
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, lambda: process_concept_folder(output_dir, DRIVE_DIR))
            else:
                print(f"[C-W{worker_id}] ERROR: Failed to assemble {project_name}")

        except Exception as e:
            print(f"[C-W{worker_id}] ERROR: {e}")
        finally:
            concat_queue.task_done()


# --- ORCHESTRATOR ---

async def main():
    print("=====================================================")
    print(f"{os.getenv('NICHE_NAME', 'UNIVERSAL').upper()} :: PARALLEL FACTORY FLOOR")
    print("=====================================================")
    
    # NEW: Voicebox Warm-Up Protocol
    print("⏳ [WARM-UP] Pinging Voicebox to load 1.7B Model into VRAM... (This may take up to 3 minutes)")
    try:
        warmup_payload = {"text": "Initializing.", "profile_id": os.getenv("VOICEBOX_PROFILE_ID", "66cee046-6d00-4055-9cfe-4fe9ca8637c9")}
        requests.post(f"{VOICEBOX_URL}/generate", json=warmup_payload, timeout=600)
        print("✅ [WARM-UP] Voicebox Model is active and ready.")
    except Exception as e:
        print(f"⚠️  [WARM-UP] Non-fatal issue during warm-up: {e}. Workers will proceed using standard timeouts.")
    
    # Read exact concepts from concepts.txt so we ignore old mismatched JSON files
    sys.path.append(os.getcwd())
    try:
        from concept_patcher import parse_concepts
        concept_file_path = os.getenv("NICHE_CONCEPTS_FILE", "concepts.txt")
        concepts = parse_concepts() # parse_concepts handles the env var natively
        active_slugs = [c[0] for c in concepts]
        config_files = [os.path.join(CONFIGS_DIR, f"{slug}.json") for slug in active_slugs]
        config_files = [cf for cf in config_files if os.path.exists(cf)]
        if not config_files:
            print(f"No active configs found matching {concept_file_path} in {CONFIGS_DIR}/")
            return
    except Exception as e:
        print(f"Warning: Failed to parse concepts.txt, falling back to all configs: {e}")
        config_files = glob.glob(os.path.join(CONFIGS_DIR, "*.json"))
        # Exclude the example template
        config_files = [c for c in config_files if Path(c).stem != "example_concept"]
        if not config_files:
            print("No configs found in configs/ directory.")
            return

    # Skip configs that are already fully captioned (no need to re-render)
    pending = []
    for cf in sorted(config_files):
        name = Path(cf).stem
        captioned = os.path.join(DRIVE_DIR, f"{name}_Captioned.mp4")
        if os.path.exists(captioned):
            print(f"[SKIP] Already captioned: {name}")
        else:
            pending.append(cf)

    config_files = pending[:DAILY_PRODUCTION_LIMIT]
    if not config_files:
        print("All configs are already captioned. Nothing to do.")
        return
    print(f"Throttling production to {len(config_files)} projects (limit: {DAILY_PRODUCTION_LIMIT}).")

    # Initialize tracker and inject tasks
    for config_path in config_files:
        project_name = Path(config_path).stem
        with open(config_path, "r", encoding='utf-8') as f:
            cfg = json.load(f)
            
        narrative = cfg.get("narrative_script", [])
        visual_prompts = cfg.get("visual_prompts") or cfg.get("image_prompts", [])
        total_scenes = min(len(narrative), len(visual_prompts))

        if len(narrative) != len(visual_prompts):
            print(
                f"[WARN] Scene count mismatch in {project_name}: "
                f"narrative={len(narrative)}, visuals={len(visual_prompts)}. "
                f"Using {total_scenes} paired scenes."
            )
        
        if total_scenes == 0:
            continue
            
        tracker[project_name] = {
            "total_scenes": total_scenes,
            "scenes": {i: {"audio": False, "visual": False, "muxed": False} for i in range(total_scenes)},
            "muxed_count": 0
        }
        
        # Dispatch Initial Pipeline Tasks
        for i in range(total_scenes):
            audio_queue.put_nowait((project_name, i, cfg))
            visual_queue.put_nowait((project_name, i, cfg))
            
    # Start Workers
    audio_workers = [asyncio.create_task(audio_worker(i)) for i in range(MAX_AUDIO_WORKERS)]
    visual_workers = [asyncio.create_task(visual_worker(i)) for i in range(MAX_VISUAL_WORKERS)]
    mux_workers = [asyncio.create_task(mux_worker(i)) for i in range(MAX_MUX_WORKERS)]
    concat_workers = [asyncio.create_task(concat_worker(i)) for i in range(MAX_CONCAT_WORKERS)]

    # Wait for all queues to empty
    await audio_queue.join()
    await visual_queue.join()
    await mux_queue.join()
    await concat_queue.join()
    
    # Send termination signals
    for _ in audio_workers: audio_queue.put_nowait(None)
    for _ in visual_workers: visual_queue.put_nowait(None)
    for _ in mux_workers: mux_queue.put_nowait(None)
    for _ in concat_workers: concat_queue.put_nowait(None)
    
    await asyncio.gather(*audio_workers, *visual_workers, *mux_workers, *concat_workers)
    
    print("=====================================================")
    print("FACTORY BATCH REPORT")
    print("=====================================================")
    success_count = 0
    for name in tracker.keys():
        captioned = os.path.join(DRIVE_DIR, f"{name}_Captioned.mp4")
        if os.path.exists(captioned):
            print(f"✅ SUCCESS : {name}")
            success_count += 1
        else:
            print(f"❌ INCOMPLETE: {name} (Scenes failed due to Meta AI drops)")
    
    print("=====================================================")
    if success_count == len(tracker):
        print("ALL MASTER REELS CAPTIONED SUCCESSFULLY.")
    else:
        print(f"ATTENTION: {len(tracker) - success_count} concept(s) failed completion.")
        print("Run `python factory_floor.py` again to resume processing missing scenes.")
        print("=====================================================")

if __name__ == "__main__":
    asyncio.run(main())
