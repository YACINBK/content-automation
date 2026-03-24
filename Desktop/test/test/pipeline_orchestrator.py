import os
import re
import json
import shutil
import datetime
from dotenv import load_dotenv
from youtube_uploader import authenticate_youtube, upload_short, build_metadata

load_dotenv(override=True)

# --- PATHS FROM .env ---
ONEDRIVE_DIR = os.getenv("ONEDRIVE_PATH", r"C:\Users\YACIN\OneDrive\DarkProductivity")
CAPTIONED_DIR = "niche_output_captioned"
NICHE_OUTPUT_DIR = "niche_output"
CONFIGS_DIR = "configs"
UPLOAD_LOG = "upload_log.json"

def load_upload_log():
    if os.path.exists(UPLOAD_LOG):
        with open(UPLOAD_LOG, 'r') as f:
            return json.load(f)
    return {}

def save_upload_log(log):
    with open(UPLOAD_LOG, 'w') as f:
        json.dump(log, f, indent=2)

def get_project_name(filename):
    """Extracts the project name from 'nasa_launch_failure_Captioned.mp4'."""
    return re.sub(r'_Captioned\.mp4$', '', filename)

def sync_to_onedrive(file_path, project_name):
    """Moves the captioned video to the OneDrive folder for cloud sync."""
    os.makedirs(ONEDRIVE_DIR, exist_ok=True)
    dest = os.path.join(ONEDRIVE_DIR, os.path.basename(file_path))
    if os.path.exists(dest):
        print(f"   ☁️  Already in OneDrive: {dest}")
        return dest
    shutil.move(file_path, dest)
    print(f"   ☁️  Moved to OneDrive: {dest}")
    return dest

def cleanup_production_folder(project_name):
    """Deletes the niche_output/production_<project_name>/ folder."""
    prod_folder = os.path.join(NICHE_OUTPUT_DIR, f"production_{project_name}")
    if os.path.exists(prod_folder):
        shutil.rmtree(prod_folder)
        print(f"   🗑️  Deleted production folder: {prod_folder}")
    else:
        print(f"   ℹ️  No production folder found for {project_name} (already cleaned?)")

def run():
    print("=" * 60)
    print("🚀 DARK PRODUCTIVITY — PIPELINE ORCHESTRATOR")
    print("=" * 60)

    if not os.path.exists(CAPTIONED_DIR):
        print(f"❌ Captioned folder not found: {CAPTIONED_DIR}")
        return

    upload_log = load_upload_log()
    yt_service = authenticate_youtube()
    
    # Find all captioned videos
    videos = sorted([
        f for f in os.listdir(CAPTIONED_DIR)
        if f.endswith("_Captioned.mp4")
    ])

    if not videos:
        print("✅ No new captioned videos to process.")
        return

    print(f"📂 Found {len(videos)} captioned video(s) to process.\n")

    for filename in videos:
        project_name = get_project_name(filename)
        print(f"--- 📹 Processing: {project_name} ---")

        # Skip if already uploaded
        if project_name in upload_log:
            print(f"   ⏩ Already uploaded (YouTube ID: {upload_log[project_name]['youtube_id']}). Skipping.\n")
            continue

        local_path = os.path.join(CAPTIONED_DIR, filename)
        config_path = os.path.join(CONFIGS_DIR, f"{project_name}.json")

        if not os.path.exists(config_path):
            print(f"   ⚠️  No config found at {config_path}. Skipping.\n")
            continue

        # Step 1: Sync to OneDrive (moves the file there)
        onedrive_path = sync_to_onedrive(local_path, project_name)

        # Step 2: Upload to YouTube from the OneDrive location
        title, description, tags = build_metadata(project_name, config_path)
        try:
            video_id = upload_short(yt_service, onedrive_path, title, description, tags, privacy='private')
        except Exception as e:
            print(f"   ❌ Upload failed: {e}\n")
            continue

        # Step 3: Log the upload
        upload_log[project_name] = {
            "youtube_id": video_id,
            "uploaded_at": datetime.datetime.now().isoformat(),
            "onedrive_path": onedrive_path
        }
        save_upload_log(upload_log)
        print(f"   📝 Logged in {UPLOAD_LOG}")

        # Step 4: Clean up production folder (intermediate video parts)
        cleanup_production_folder(project_name)

        print(f"   ✅ {project_name} complete!\n")

    print("=" * 60)
    print("🏁 All videos processed.")
    print(f"📊 Upload log saved to {UPLOAD_LOG}")
    print("=" * 60)

if __name__ == "__main__":
    run()
