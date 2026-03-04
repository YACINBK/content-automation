"""
tiktok_scheduler.py
===================
Standalone TikTok scheduling pipeline.

Flow per video:
  1. List paired (.mp4 + _metadata.json) files from a Google Drive folder
  2. Skip already-scheduled files (via schedule_state.json)
  3. Download the metadata JSON in-memory → ask OpenRouter LLM for caption + hashtags
  4. Download the .mp4 to a temp folder
  5. Schedule the upload on TikTok (10:00 and 18:00 slots, 2 per day)
  6. Record the file ID in schedule_state.json
  7. Delete the local .mp4 temp file

TikTok scheduling limit: max 10 days in advance.
For large batches, re-run the script every few days to keep filling the queue.
"""

import os
import json
import logging
import datetime
from pathlib import Path

from dotenv import load_dotenv
from drive_client import DriveClient
from caption_generator import CaptionGenerator
from tiktokautouploader import upload_tiktok

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()

TIKTOK_ACCOUNT  = os.getenv("TIKTOK_ACCOUNT_NAME", "")
DRIVE_FOLDER_ID = os.getenv("DRIVE_VIDEOS_FOLDER_ID", "")
STEALTH_MODE    = os.getenv("TIKTOK_STEALTH_MODE", "true").lower() == "true"

# Two fixed daily slots — submitted in UTC so TikTok displays at 10:00 and 18:00 (CET = UTC+1).
# tiktokautouploader sends times as-is to TikTok's UTC backend, so we subtract the
# offset between UTC and the account's display timezone (observed: UTC → CET+5 = 6h).
# To show 10:00 AM CET → submit 04:00 UTC  |  To show 6:00 PM CET → submit 12:00 UTC
DAILY_SLOTS = os.getenv("TIKTOK_DAILY_SLOTS", "04:00,12:00").split(",")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR      = Path(__file__).parent
STATE_FILE    = BASE_DIR / "schedule_state.json"
TEMP_DIR      = BASE_DIR / "temp_downloads"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------
def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"scheduled": []}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Schedule calculation
# ---------------------------------------------------------------------------
def get_slot(position: int) -> tuple[str, int, datetime.date]:
    """
    Given the 0-based position in the current batch, return:
        (time_str, day_of_month, target_date)

    position 0 → Day 1  at 10:00
    position 1 → Day 1  at 18:00
    position 2 → Day 2  at 10:00
    ...
    """
    slot_idx   = position % len(DAILY_SLOTS)
    day_offset = (position // len(DAILY_SLOTS)) + 1   # start tomorrow
    target     = datetime.date.today() + datetime.timedelta(days=day_offset)
    return DAILY_SLOTS[slot_idx], target.day, target


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    # Validate config
    if not TIKTOK_ACCOUNT:
        logger.error("❌  TIKTOK_ACCOUNT_NAME is not set in .env — aborting.")
        return
    if not DRIVE_FOLDER_ID:
        logger.error("❌  DRIVE_VIDEOS_FOLDER_ID is not set in .env — aborting.")
        return

    # Init services
    drive   = DriveClient()
    caption = CaptionGenerator()
    state   = load_state()

    already_scheduled_ids = {entry["video_id"] for entry in state["scheduled"]}

    # 1. Fetch paired files from Drive
    logger.info(f"🔍  Fetching video pairs from Drive folder: {DRIVE_FOLDER_ID}")
    pairs = drive.list_video_pairs(DRIVE_FOLDER_ID)

    if not pairs:
        logger.info("📭  No .mp4 files found in the Drive folder.")
        return

    # 2. Filter out already-scheduled
    new_pairs = [p for p in pairs if p["video_id"] not in already_scheduled_ids]

    if not new_pairs:
        logger.info("✅  All videos are already scheduled — nothing to do.")
        return

    logger.info(f"🚀  {len(new_pairs)} new video(s) to schedule.")
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Seed the slot position from total already-scheduled count so that
    # re-runs continue from the correct day/slot (not restart from Day 1).
    total_scheduled_before = len(state["scheduled"])
    batch_count = 0   # counts successfully scheduled in THIS run

    for pair in new_pairs:
        video_id   = pair["video_id"]
        video_name = pair["video_name"]
        meta_id    = pair["meta_id"]

        global_position = total_scheduled_before + batch_count
        time_str, day_val, target_date = get_slot(global_position)
        days_ahead = (target_date - datetime.date.today()).days

        # TikTok hard limit: cannot schedule more than 10 days out
        if days_ahead > 10:
            logger.warning(
                f"⏭️   Skipping '{video_name}': target date {target_date} is "
                f"{days_ahead} days away (TikTok limit = 10). "
                "Re-run this script in a few days to continue."
            )
            continue

        local_path = TEMP_DIR / video_name

        try:
            # 3. Generate caption from metadata (in-memory, no local JSON file)
            if meta_id:
                logger.info(f"📄  Loading metadata for '{video_name}'...")
                metadata = drive.download_json(meta_id)
            else:
                logger.warning(f"⚠️  No metadata found for '{video_name}', using fallback caption.")
                metadata = {}

            description, hashtags = caption.generate(metadata)

            # 4. Download the video
            logger.info(f"📥  Downloading: {video_name} ...")
            drive.download_file(video_id, str(local_path))

            # 5. Schedule on TikTok
            logger.info(
                f"📤  Scheduling '{video_name}' → {target_date} at {time_str} "
                f"| desc: \"{description[:50]}...\" | tags: {hashtags}"
            )
            upload_tiktok(
                video=str(local_path),
                description=description,
                hashtags=[f"#{t}" for t in hashtags],
                accountname=TIKTOK_ACCOUNT,
                schedule=time_str,
                day=day_val,
                stealth=STEALTH_MODE,
                headless=True,         # Set to False on first run to allow browser login
            )

            # 6. Persist state immediately after success (so a crash mid-batch doesn't re-post)
            state["scheduled"].append({
                "video_id":    video_id,
                "video_name":  video_name,
                "scheduled_at": f"{target_date} {time_str}",
                "description": description,
                "hashtags":    hashtags,
            })
            save_state(state)
            batch_count += 1
            logger.info(f"✅  Scheduled: {video_name} on {target_date} at {time_str}")

        except Exception as exc:
            logger.error(f"❌  Failed to process '{video_name}': {exc}")

        finally:
            # 7. Clean up local video file regardless of outcome
            if local_path.exists():
                local_path.unlink()
                logger.info(f"🗑️   Cleaned up local file: {video_name}")

    # Summary
    logger.info(f"🏁  Done! Scheduled {batch_count} video(s) in this run.")
    if batch_count < len(new_pairs):
        skipped = len(new_pairs) - batch_count
        logger.info(
            f"ℹ️   {skipped} video(s) were skipped (beyond the 10-day TikTok window). "
            "Re-run this script in a few days to schedule the rest."
        )


if __name__ == "__main__":
    main()
