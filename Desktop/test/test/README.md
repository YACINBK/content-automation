# Dark Productivity Content Engine (V6.5)

The ultimate, autonomous content generation and distribution pipeline. 
This engine uses AI to write scripts, extract raw speech via Voicebox TTS, render high-quality Meta AI visuals, composite everything into a clinical "Dark Productivity" aesthetic via FFmpeg, and securely distribute it to a 3-tier cloud archiver (YouTube scheduled slots, native Google Drive uploads, and OneDrive ZIP backups).

Everything is orchestrated locally and seamlessly across infinite niches.

---

## 🏗 System Architecture (The Niche Profile System)

The architecture is built on absolute separation of data and engine logic. This means you can create as many unique content categories (Niches) as you want without ever duplicating or editing any core `.py` scripts.

All core scripts live in the root directory:
- `factory_floor.py` (The Video Renderer)
- `master_caption_engine.py` (The FFmpeg Compositor)
- `upload_scheduler.py` (The Distributor)

All data lives securely isolated inside the `niches/` folder:
- `niches/dark_productivity/`
- `niches/stoicism/`
- `niches/history_facts/`

You control the entire pipeline through a single entry point: **`run.py`**.

---

## 🚀 Quick Start Guide

### Step 1: Start the Voicebox Server
Before doing anything, you **must** start the audio server in the background. Voicebox generates the TTS dialogue dynamically.
1. Open a new Terminal window.
2. Run `start_voicebox.bat`.
3. Minimize this window and leave it running in the background.

### Step 2: Initialize Your Niche Workspace
If you want to start a brand new channel/niche, run the CLI:
*(Note: A `dark_productivity` footprint has already been set up for you!)*
1. Create a folder in `niches/`: e.g. `mkdir niches/stoicism`
2. Create a `niche.env` file in that folder to dictate your branding:
```env
NICHE_NAME=Stoicism
GDRIVE_FOLDER=Niche_Stoic
ONEDRIVE_SUBFOLDER=Stoicism
```
3. Create your `concepts.txt` file in that folder. Provide your script ideas.

### Step 3: Run the Content Pipeline

You only need ONE command to control the entire factory. Just pass the name of your specific niche folder:

**1. Create JSON Script Configs from your `concepts.txt`**
```bash
python run.py --niche dark_productivity --patch
```

**2. Render the Videos (The Factory Floor)**
```bash
python run.py --niche dark_productivity --factory
```
*This will autonomously download audio from Voicebox, stream visuals from Meta AI, composite the audio/video, apply VFX, and output final `.mp4` master reels.*

**3. Distribute to the Cloud (The Uploader)**
```bash
python run.py --niche dark_productivity --upload
```
*This calculates the optimal peak algorithmic slots for US audiences, schedules the videos natively on YouTube via Data API v3, securely pushes a copy to your Google Drive (`GDRIVE_FOLDER`), zips the raw assets to your local OneDrive (`ONEDRIVE_SUBFOLDER`), and safely wipes the massive production files off your local 2TB SSD.*

**[Optional] Full End-to-End Execution**
```bash
python run.py --niche dark_productivity --all
```

---

## 🚦 Troubleshooting & Limits

### 1. "Failed to authenticate with Google APIs"
If `run.py --upload` crashes citing API limits or a 403 error, this means your Google Cloud Project lacks permissions.
1. Visit your Cloud Console.
2. Ensure you have **enabled both the Google Drive API and the YouTube Data API v3**.
3. Re-download your `client_secrets.json` and try again.

### 2. "Transmitting halted to preserve data integrity."
The system is heavily fortified. If the YouTube API rate limits your specific bot account, the script will gracefully abort *before* deleting your finished `.mp4` files. Wait 24 hours for your quota to reset and run `run.py --upload` again. The script caps distribution at **6 uploads per batch** specifically to keep you safe from algorithm ban-hammers.

### 3. "Scenes failed due to Meta AI drops"
Meta AI can sometimes rate-limit intensive web-scraping requests. The factory processes completely asynchronously — if a clip fails, the `factory_floor.py` engine will catch it, generate an `INCOMPLETE` ledger report, and continue rendering everything else. Just run `--factory` again. It will skip everything that already completed and only re-try the missing clips!

---

*System designed and automated indefinitely logic by v6.5-chrono-clinical.*
