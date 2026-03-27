"""
Batch Scheduler & Cloud Archiver
- Pushes videos directly to YouTube with 'publishAt' targeting US high-RPM slots.
- Synchronously pushes final Mp4 to Google Drive via native API.
- Generates a full zip/folder master copy in OneDrive.
- Safely cleans up the local production environment ONLY upon 100% remote success.
"""

import os
import re
import json
import shutil
import datetime
from dotenv import load_dotenv

# Import our custom engines
from youtube_uploader import authenticate_youtube, upload_short
from drive_uploader import authenticate_drive, upload_to_drive, get_or_create_folder
from llm_handler import LLMHandler

load_dotenv(override=True)

# --- CONFIG ---
ONEDRIVE_DIR     = r"D:\OneDrive - Ministere de l'Enseignement Superieur et de la Recherche Scientifique\DarkProductivity"
CAPTIONED_DIR    = "niche_output_captioned"
NICHE_OUTPUT_DIR = "niche_output"
CONFIGS_DIR      = "configs"
UPLOAD_LOG       = "upload_log.json"

# US Peak RPM Slots (UTC)
# - 13:00 UTC = 09:00 AM EDT (Morning Commute)
# - 17:30 UTC = 01:30 PM EDT (Lunch Break)
# - 01:30 UTC = 09:30 PM EDT (Evening Prime Time)
UTC_SLOTS = [
    (13, 0),
    (17, 30),
    (1, 30)
]

_llm = LLMHandler()

def load_upload_log():
    if os.path.exists(UPLOAD_LOG):
        with open(UPLOAD_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_upload_log(log):
    with open(UPLOAD_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

def get_next_publish_time(log_data):
    """
    Calculates the exact chronological ISO 8601 string for the NEXT available 
    US Prime Time slot by looking at the latest future date in the log.
    """
    now = datetime.datetime.utcnow()
    last_dt = now

    # Find the absolute latest publishAt date already scheduled
    if log_data:
        future_dates = []
        for v in log_data.values():
            if "publishAt" in v:
                try:
                    pstr = v["publishAt"]
                    dt = datetime.datetime.fromisoformat(pstr.replace("Z", "+00:00"))
                    dt = dt.replace(tzinfo=None)
                    future_dates.append(dt)
                except: pass
        if future_dates:
            latest_future = max(future_dates)
            if latest_future > last_dt:
                last_dt = latest_future

    base_date = last_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    candidates = []
    # Project slots over the next 48 hours to find the immediate next one
    for day_offset in range(3):
        for h, m in UTC_SLOTS:
            candidate = base_date + datetime.timedelta(days=day_offset, hours=h, minutes=m)
            # Has to be strictly AFTER the last scheduled video AND after right now
            if candidate > last_dt and candidate > now:
                candidates.append(candidate)
                
    candidates.sort()
    next_time = candidates[0]
    # YouTube strictly requires format: 'YYYY-MM-DDThh:mm:ss.sZ'
    return next_time.strftime('%Y-%m-%dT%H:%M:%S.0Z')

def build_seo_metadata(project_name, config_path):
    # Retrieve base configuration
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    script_lines = config.get("narrative_script", [])
    script_text = " ".join(
        re.sub(r"\[.*?\]", lambda m: m.group(0).strip("[]"), l)
        for l in script_lines
    )

    base_title = project_name.replace("_", " ").title()

    prompt = f"""You are an anomaly data extractor for the Dark Productivity project.
Scan this video script:
\"\"\"{script_text[:400]}...\"\"\"

Return ONLY valid JSON with exactly these keys:
{{
  "subject_name": "...", 
  "anomaly_code": "...", 
  "niche_tags": ["...", "...", "..."]
}}
- 'subject_name' should be 1-3 words (e.g. 'The Pharaoh' or 'The Astronaut').
- 'anomaly_code' must be a random 3-digit number.
- 'niche_tags' must be 3 specific single-word tags related to the video content (no # symbols)."""

    messages = [{"role": "user", "content": prompt}]
    raw = _llm._call_llm(messages)

    # Defaults in case of LLM parse failure
    subject_name = base_title
    anomaly_code = "404"
    niche_tags = ["shorts", "mindset", "hustle"]

    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            subject_name = data.get("subject_name", subject_name)
            anomaly_code = data.get("anomaly_code", anomaly_code)
            niche_tags = data.get("niche_tags", niche_tags)
            print(f"   🎯 Parsed Variables: {subject_name} | {anomaly_code}")
    except Exception as e:
        print(f"   ⚠️  Variable extraction failed ({e}), using defaults.")

    # 100% Deterministic Formatting
    title = f"{base_title} - Anomaly Log {anomaly_code}"[:100]
    
    description = (
        f"SUBJECT: {subject_name}\n"
        f"STATUS: System failure. Biological decay detected.\n\n"
        f"#dopaminedetox #focus #simulation #psychology #history #brainrot"
    )

    tags = ["dopaminedetox", "focus", "simulation", "psychology", "history", "brainrot", "dark productivity"] + niche_tags
    
    return title, description, tags[:14]

def archive_and_clean(project_name, local_video, config_path):
    """
    Safely packages the entire component library to OneDrive, then deletes local files.
    """
    print(f"   ☁️  Archiving full production suite to OneDrive...")
    onedrive_target = os.path.join(ONEDRIVE_DIR, project_name)
    os.makedirs(onedrive_target, exist_ok=True)

    # 1. Package Config
    if os.path.exists(config_path):
        shutil.copy2(config_path, os.path.join(onedrive_target, f"{project_name}_config.json"))

    # 2. Package Production Folder (Audio, Clips, Subtitles)
    prod_folder = os.path.join(NICHE_OUTPUT_DIR, f"production_{project_name}")
    if os.path.exists(prod_folder):
        dest_prod = os.path.join(onedrive_target, f"production_{project_name}")
        if os.path.exists(dest_prod):
            shutil.rmtree(dest_prod)
        shutil.copytree(prod_folder, dest_prod)

    # 3. Package Final Reel
    shutil.copy2(local_video, os.path.join(onedrive_target, os.path.basename(local_video)))

    # --- PROFESSIONAL DESTRUCTIVE CLEANUP ---
    # Since we only reach this phase if YT & GDrive APIs succeeded, we can safely wipe.
    print(f"   🧹 Soft cleaning local machine storage...")
    if os.path.exists(config_path): os.remove(config_path)
    if os.path.exists(prod_folder): shutil.rmtree(prod_folder)
    if os.path.exists(local_video): os.remove(local_video)
    print(f"   ✅ Local disk footprint completely erased for {project_name}.")

def execute_batch():
    print("=" * 60)
    print("🚀 DARK PRODUCTIVITY AUTOMATED DISTRIBUTOR")
    print("=" * 60)
    
    # Strict path safeguard as requested
    if not os.path.exists(ONEDRIVE_DIR):
        print(f"❌ FATAL ERROR: Manual OneDrive directory not found at:")
        print(f"   {ONEDRIVE_DIR}")
        print("Please ensure the drive is mounted and the directory exists before proceeding.")
        return

    # Authentication Phase
    try:
        yt_service = authenticate_youtube()
        drive_service = authenticate_drive()
        niche_folder_id = get_or_create_folder(drive_service, "Niche")
        print("✅ Authorized with Google APIs (YouTube + Drive).")
    except Exception as e:
        print(f"❌ Failed to authenticate APIs: {e}")
        print("Please check your client_secrets.json and run again.")
        return

    log = load_upload_log()
    pending_files = [
        f for f in os.listdir(CAPTIONED_DIR) 
        if f.endswith("_Captioned.mp4") and re.sub(r"_Captioned\.mp4$", "", f) not in log
    ]

    if not pending_files:
        print("\n✅ Zero pending videos detected in the captioned directory. Standing by.")
        return

    # Professional Quota Safeguard
    # YouTube flags bursts of uploads from API clients as spam. We cap safe limits.
    MAX_BATCH_UPLOADS = 6
    
    print(f"\n📦 INVENTORY REPORT: Detected {len(pending_files)} videos physically ready for distribution in `{CAPTIONED_DIR}`.")
    
    if len(pending_files) > MAX_BATCH_UPLOADS:
        print(f"   ⚠️  API SAFEGUARD ENGAGED: To protect your YouTube Channel from spam-flags and API rate limits,")
        print(f"      this distributor engine is strictly capped at {MAX_BATCH_UPLOADS} uploads per session.")
        print(f"   ⏳ The remaining {len(pending_files) - MAX_BATCH_UPLOADS} videos will remain untouched. Run the script again tomorrow to process them.")
        pending_files = pending_files[:MAX_BATCH_UPLOADS]
    else:
        print("   ✅ Status: Within safe API payload limits (0-6). Distributing the entire batch.")

    for filename in sorted(pending_files):
        project_name = re.sub(r"_Captioned\.mp4$", "", filename)
        local_video = os.path.join(CAPTIONED_DIR, filename)
        config_path = os.path.join(CONFIGS_DIR, f"{project_name}.json")

        if not os.path.exists(config_path):
            print(f"⚠️  Missing {config_path}. Cannot generate metadata. Skipping.")
            continue

        print(f"\n▶️ Processing: {project_name}")
        
        # Calculate exactly when this should hit the US algorithm
        publish_at_str = get_next_publish_time(log)
        print(f"   ⏰ Targeted US Release Window: {publish_at_str}")

        # Generate intelligent SEO
        title, desc, tags = build_seo_metadata(project_name, config_path)

        # EXECUTION: The 3-way Cloud Backup
        try:
            # 1. YouTube Server Push
            print(f"   📡 Transmitting to YouTube servers...")
            yt_id = upload_short(yt_service, local_video, title, desc, tags, publish_at=publish_at_str)

            # 2. Google Drive Core Backup
            drive_id = upload_to_drive(drive_service, local_video, folder_id=niche_folder_id)

            # 3. Comprehensive Local Archiving & Cleanup
            archive_and_clean(project_name, local_video, config_path)

            # Finalize Success in Ledger
            log[project_name] = {
                "youtube_id": yt_id,
                "drive_id": drive_id,
                "publishAt": publish_at_str,
                "title": title
            }
            save_upload_log(log)

        except Exception as e:
            print(f"   ❌ FATAL ERROR transmitting {project_name}: {e}")
            print("   ⚠️  Transmission halted to preserve data integrity.")
            continue

    print("\n" + "=" * 60)
    print("🏁 DISTRIBUTOR BATCH COMPLETE.")
    print("=" * 60)

if __name__ == "__main__":
    execute_batch()
