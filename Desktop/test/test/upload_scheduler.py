"""
upload_scheduler.py — Dark Productivity YouTube Shorts Upload Scheduler

Behavior:
- Runs as a persistent daemon.
- Each day, uploads up to DAILY_LIMIT videos from the captioned queue.
- Distributes uploads across the 3 statistically best Shorts windows per day.
- Uses the LLM to generate niche-specific, up-to-date SEO metadata per video.
- Cleans local files after successful upload.
- Logs everything to upload_log.json.

YouTube Shorts best upload times (based on 2025 data, audience: 18-35 EN):
  - 08:00 (morning scroll peak)
  - 12:30 (lunch break peak)
  - 19:30 (evening prime time)

Daily upload limit: YouTube allows ~100/day but unverified/new channels risk being
flagged for spam — safe target is 3 Shorts/day for new channels, scalable to 6/day
after first 50-100 subscribers.
"""

import os
import re
import json
import shutil
import schedule
import time
import datetime
from dotenv import load_dotenv
from youtube_uploader import authenticate_youtube, upload_short
from llm_handler import LLMHandler

load_dotenv(override=True)

# --- CONFIG ---
ONEDRIVE_DIR     = os.getenv("ONEDRIVE_PATH", r"C:\Users\YACIN\OneDrive\DarkProductivity")
CAPTIONED_DIR    = "niche_output_captioned"
NICHE_OUTPUT_DIR = "niche_output"
CONFIGS_DIR      = "configs"
UPLOAD_LOG       = "upload_log.json"
DAILY_LIMIT      = int(os.getenv("DAILY_UPLOAD_LIMIT", "3"))  # Configurable — safe default

# Upload windows (24h format, local time)
UPLOAD_WINDOWS = ["08:00", "12:30", "19:30"]

# Global state
_upload_queue = []
_uploads_today = 0
_current_day = None
_yt_service = None
_llm = LLMHandler()


def load_upload_log():
    if os.path.exists(UPLOAD_LOG):
        with open(UPLOAD_LOG, "r") as f:
            return json.load(f)
    return {}


def save_upload_log(log):
    with open(UPLOAD_LOG, "w") as f:
        json.dump(log, f, indent=2)


def get_project_name(filename):
    return re.sub(r"_Captioned\.mp4$", "", filename)


def build_seo_metadata(project_name, config_path):
    """
    Uses the LLM to generate platform-native, niche-targeted SEO metadata.
    This applies current best practices for YouTube Shorts discoverability.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    script_lines = config.get("narrative_script", [])
    script_text = " ".join(
        re.sub(r"\[.*?\]", lambda m: m.group(0).strip("[]"), l)
        for l in script_lines
    )

    prompt = f"""You are a YouTube Shorts SEO expert in 2026.
Generate metadata for a Short about this concept: "{project_name.replace("_", " ")}"

The script excerpt is:
\"\"\"{script_text[:300]}...\"\"\"

Return ONLY a valid JSON object with these exact keys:
{{
  "title": "...",         # Max 60 chars. Start with a hook word. Include main keyword naturally. NO clickbait.
  "description": "...",  # 150-200 chars. First line is the hook. Include CTA. End with 3-5 hashtags including #Shorts.
  "tags": ["...", ...]   # Array of 10-15 strings. Mix: 3 broad (psychology, motivation), 5 mid-tail (dopamine detox, focus tips), 3 niche (dark productivity, brain hack).
}}

Current YouTube Shorts SEO rules:
- Use conversational language that matches how people search.
- Title must not exceed 60 chars for thumbnail display.
- First hashtag must be #Shorts.
- Tags should include variations: singular, plural, with/without spaces.
- Capitalize key terms in tags for readability."""

    messages = [{"role": "user", "content": prompt}]
    raw = _llm._call_llm(messages)

    try:
        # Extract JSON from response
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            title = data.get("title", project_name.replace("_", " ").title())[:100]
            description = data.get("description", "")
            tags = data.get("tags", ["psychology", "mindset", "shorts"])
            print(f"   🎯 LLM SEO generated: {title}")
            return title, description, tags
    except Exception as e:
        print(f"   ⚠️  SEO generation failed ({e}), using fallback metadata.")

    # Fallback
    title = f"POV: {project_name.replace('_', ' ').title()} #Shorts"[:100]
    description = f"{script_lines[-1] if script_lines else ''}\n\n#Shorts #psychology #dopamine #mindset"
    tags = ["psychology", "dopamine", "mindset", "productivity", "dark productivity",
            "focus", "motivation", "shorts", project_name.replace("_", " ")]
    return title, description, tags


def sync_to_onedrive(file_path):
    os.makedirs(ONEDRIVE_DIR, exist_ok=True)
    dest = os.path.join(ONEDRIVE_DIR, os.path.basename(file_path))
    if not os.path.exists(dest):
        shutil.move(file_path, dest)
        print(f"   ☁️  Synced to OneDrive: {dest}")
    else:
        print(f"   ☁️  Already in OneDrive: {dest}")
    return dest


def cleanup_production_folder(project_name):
    prod_folder = os.path.join(NICHE_OUTPUT_DIR, f"production_{project_name}")
    if os.path.exists(prod_folder):
        shutil.rmtree(prod_folder)
        print(f"   🗑️  Cleaned: {prod_folder}")


def refresh_queue():
    """Rebuilds the upload queue from the captioned directory, excluding already-uploaded videos."""
    global _upload_queue
    log = load_upload_log()
    if not os.path.exists(CAPTIONED_DIR):
        _upload_queue = []
        return

    _upload_queue = sorted([
        f for f in os.listdir(CAPTIONED_DIR)
        if f.endswith("_Captioned.mp4")
        and get_project_name(f) not in log
    ])
    print(f"📋 Queue refreshed: {len(_upload_queue)} video(s) pending.")


def reset_daily_counter():
    """Called at midnight to reset the daily upload counter."""
    global _uploads_today, _current_day
    _uploads_today = 0
    _current_day = datetime.date.today()
    refresh_queue()
    print(f"\n🔄 Daily counter reset. New day: {_current_day}. Queue: {len(_upload_queue)} videos.\n")


def upload_next():
    """Uploads the next video in the queue if the daily limit hasn't been hit."""
    global _uploads_today, _upload_queue

    if _uploads_today >= DAILY_LIMIT:
        print(f"⏸️  Daily limit of {DAILY_LIMIT} reached. Waiting for next day.")
        return

    if not _upload_queue:
        refresh_queue()
        if not _upload_queue:
            print("✅ No videos pending in queue.")
            return

    filename = _upload_queue[0]
    project_name = get_project_name(filename)
    local_path = os.path.join(CAPTIONED_DIR, filename)
    config_path = os.path.join(CONFIGS_DIR, f"{project_name}.json")

    if not os.path.exists(local_path):
        print(f"⚠️  File not found locally (may already be in OneDrive): {local_path}")
        local_path = os.path.join(ONEDRIVE_DIR, filename)

    if not os.path.exists(config_path):
        print(f"⚠️  No config found for {project_name}, skipping.")
        _upload_queue.pop(0)
        return

    print(f"\n--- 📹 Uploading: {project_name} ({_uploads_today + 1}/{DAILY_LIMIT} today) ---")

    # 1. OneDrive sync
    onedrive_path = sync_to_onedrive(local_path)

    # 2. Generate SEO metadata via LLM
    title, description, tags = build_seo_metadata(project_name, config_path)

    # 3. Upload to YouTube (private — review before publishing)
    try:
        video_id = upload_short(_yt_service, onedrive_path, title, description, tags, privacy="private")
    except Exception as e:
        print(f"   ❌ Upload failed: {e}")
        return

    # 4. Log, clean up, and advance queue
    log = load_upload_log()
    log[project_name] = {
        "youtube_id": video_id,
        "uploaded_at": datetime.datetime.now().isoformat(),
        "title": title,
        "onedrive_path": onedrive_path
    }
    save_upload_log(log)

    cleanup_production_folder(project_name)
    _upload_queue.pop(0)

    print(f"   ✅ Done. {DAILY_LIMIT - _uploads_today} upload slot(s) remaining today.\n")


def start():
    global _yt_service

    print("=" * 60)
    print("🗓️  DARK PRODUCTIVITY — YOUTUBE UPLOAD SCHEDULER")
    print(f"   Daily Limit : {DAILY_LIMIT} videos/day")
    print(f"   Upload Times: {', '.join(UPLOAD_WINDOWS)}")
    print(f"   OneDrive    : {ONEDRIVE_DIR}")
    print("=" * 60)

    # Authenticate once at startup
    _yt_service = authenticate_youtube()
    print("✅ YouTube authenticated.\n")

    # Initial queue load
    reset_daily_counter()

    # Schedule uploads at the 3 optimal daily windows
    for window in UPLOAD_WINDOWS:
        schedule.every().day.at(window).do(upload_next)
        print(f"🕐 Scheduled upload at {window}")

    # Midnight reset
    schedule.every().day.at("00:01").do(reset_daily_counter)
    print("🔄 Daily counter resets at 00:01\n")

    print("🟢 Scheduler is running. Press Ctrl+C to stop.\n")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    start()
