"""
scraping_manager.py
The Scraper Orchestrator. 
Loop through niche configs, identify missing clips, and run the 
Universal AI Visual Architect negotiation via meta_scrapling_video.py.
"""
import os
import json
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure we can import local modules
sys.path.append(os.getcwd())
from llm_handler import LLMHandler
from meta_scrapling_video import run_automation

load_dotenv(override=True)

# Environment Paths
CONFIGS_DIR   = os.getenv("NICHE_CONFIGS_DIR",   "configs")
WORKSPACE_DIR = os.getenv("NICHE_WORKSPACE_DIR", "niche_output")

async def scrape_niche_clips(headless=False):
    """
    Main orchestrator loop.
    Finds all JSON files in the config dir and ensures all 5 clips per video exist.
    """
    if not os.path.exists(CONFIGS_DIR):
        print(f"[X] ERROR: Configs directory not found: {CONFIGS_DIR}")
        return

    json_files = [f for f in os.listdir(CONFIGS_DIR) if f.endswith(".json")]
    if not json_files:
        print(f"[!] No JSON configs found in {CONFIGS_DIR}. Run --patch first.")
        return

    print(f"[*] Scraper Orchestrator: Found {len(json_files)} videos to check.")
    llm = LLMHandler()

    for jf in sorted(json_files):
        config_path = os.path.join(CONFIGS_DIR, jf)
        project_name = jf.replace(".json", "")
        
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        output_dir = os.path.join(WORKSPACE_DIR, f"production_{project_name}")
        os.makedirs(output_dir, exist_ok=True)

        narrative = cfg.get("narrative_script", [])
        visual_prompts = cfg.get("visual_prompts") or cfg.get("image_prompts", [])
        anchor = cfg.get("anchor_block", "")

        print(f"\n[>] PROJECT: {project_name.upper()}")
        print(f"{'='*40}")

        for i, prompt_core in enumerate(visual_prompts):
            if i >= 5: break # Only process first 5 scenes
            
            output_file = os.path.join(output_dir, f"clip_{i:02d}.mp4")
            
            # 1. Existence Check
            if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
                print(f"   [OK] Scene {i+1}: Clip exists. Skipping.")
                continue

            # 2. Master Prompt Generation
            full_concept = f"{prompt_core} {anchor}"
            print(f"   [*] Scene {i+1}: Architect is drafting Master Prompt...")
            
            # Ensure we use the Architect persona
            loop = asyncio.get_event_loop()
            master_prompt = await loop.run_in_executor(None, llm.generate_video_prompt, full_concept)
            
            if not master_prompt:
                print(f"   [!] Architect failed. Using raw fallback.")
                master_prompt = f"Imagine a video of {full_concept}"

            # 3. Scraping & Negotiation Phase
            print(f"   [>] Scene {i+1}: Launching Headed Scraper...")
            success = await run_automation(master_prompt, output_file, headless=headless)
            
            if success:
                print(f"   [OK] Scene {i+1}: SUCCESS! Clip saved.")
            else:
                print(f"   [X] Scene {i+1}: FAILED after all negotiation attempts.")

    print(f"\n[OK] Scraper Orchestration Finished.")

if __name__ == "__main__":
    # If run directly (not via run.py), default to HEADED mode as requested.
    asyncio.run(scrape_niche_clips(headless=False))
