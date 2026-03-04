# TikTok Uploader Pipeline 🚀

Standalone pipeline that downloads videos from Google Drive and schedules them to TikTok, generating **unique AI-powered captions and hashtags** for each video using its metadata.

## File Structure

```
tiktok_uploader/
├── tiktok_scheduler.py      # Main entry point — run this
├── drive_client.py          # Google Drive: list & download files
├── caption_generator.py     # OpenRouter LLM: generates captions & hashtags
├── schedule_state.json      # Auto-generated — tracks scheduled videos
├── credentials.json         # Copy from your content pipeline
├── token.json               # Auto-generated on first auth
├── requirements.txt         # Python dependencies
├── .env                     # Your config (copy from .env.example)
└── README.md                # This file
```

## How it works

For each `.mp4` in your Drive folder, the pipeline:
1. Loads its `_metadata.json` counterpart (e.g. `custom_poem_20260302_021132_metadata.json`)
2. Sends the metadata to **OpenRouter LLM** → generates a tailored caption + hashtags
3. Downloads the video locally
4. Schedules it to TikTok at **10:00 AM** or **6:00 PM**
5. Records the video ID so it's never double-posted
6. Deletes the local copy

**Schedule: 2 videos/day → 30 videos = 15 days.**

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure `.env`
```bash
cp .env.example .env
```
Fill in:
- `TIKTOK_ACCOUNT_NAME` — your TikTok handle (without @)
- `DRIVE_VIDEOS_FOLDER_ID` — the ID from the Drive URL
- `OPENROUTER_API_KEY` — get free key at [openrouter.ai/keys](https://openrouter.ai/keys)

### 3. Copy credentials
Copy `credentials.json` from your content pipeline into this folder.

### 4. First run — TikTok login
```bash
python tiktok_scheduler.py
```
> **Important**: On the very first run, a Chrome browser will open and prompt you to log in to TikTok. Do this once — cookies are then cached for all future headless runs.

## TikTok's 10-day scheduling limit

TikTok only allows scheduling up to 10 days in advance. For batches > 10 videos (= 5 days), the script will log skipped videos and tell you to re-run in a few days. Your schedule state is always preserved.

## Re-running safely

You can run this script at any time. It will **only process videos not yet in `schedule_state.json`** — already-scheduled videos are never touched.
