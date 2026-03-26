# Chrono-Clinical Anomaly Logs — Automated Shorts Factory

An end-to-end AI video production pipeline that generates, captions, and schedules YouTube Shorts. Each video follows the "Eerie Archive" format: an ancient entity (Spartan, Vampire, T-Rex) is documented failing against a modern digital trap.

**Output:** ~30-second vertical videos with karaoke captions, Blueprint aesthetic overlays, and a 5-layer cinematic audio mix.

---

## Pipeline Overview

```
concepts.txt → LLM Script → Voicebox TTS + Meta AI Video → FFmpeg Mux
    → Blueprint Captions → niche_output_captioned/ → YouTube Scheduler
```

| Step | Script | What it does |
|------|--------|--------------|
| 1 | `factory_floor.py` | Main orchestrator — audio, video, mux, concat, caption |
| 2 | `llm_handler.py` | Generates narrative scripts + visual prompts via OpenRouter |
| 3 | `audio_fx_engine.py` | Applies intercom bandpass filter to TTS voice |
| 4 | `meta_scrapling_video.py` | Generates 5-second clips on Meta AI via browser automation |
| 5 | `master_caption_engine.py` | Adds Blueprint aesthetic, Whisper karaoke, 5-layer audio |
| 6 | `upload_scheduler.py` | Drip-posts 3 videos/day at 08:00, 12:30, 19:30 |
| 7 | `youtube_uploader.py` | YouTube Data API v3 helper |

---

## Prerequisites

### 1. System Dependencies
- **Python 3.10+** with Conda (environment: `base`)
- **FFmpeg** — place at `C:\ffmpeg\bin\ffmpeg.exe` (or update `.env`)
- **ImageMagick 7** — required by MoviePy for text overlays
- **Voicebox TTS Server** — local neural TTS ([jamiepine/voicebox](https://github.com/jamiepine/voicebox))

### 2. Python Packages

```bash
pip install -r requirements.txt
```

### 3. Configuration

Copy the example and fill in your values:

```bash
copy .env.example .env
```

Required values in `.env`:

```env
FFMPEG_PATH=C:\ffmpeg\bin\ffmpeg.exe
VOICEBOX_BASE_URL=http://127.0.0.1:17493
OPENROUTER_API_KEY=sk-or-v1-...
YOUTUBE_CLIENT_SECRETS=client_secrets.json
ONEDRIVE_PATH=C:\Users\YOU\OneDrive\DarkProductivity
DAILY_PRODUCTION_LIMIT=4
DAILY_UPLOAD_LIMIT=3
```

### 4. YouTube API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable **YouTube Data API v3**
3. Create an **OAuth 2.0 Desktop App** credential
4. Download `client_secrets.json` and place it in the project root

### 5. Voicebox Setup

```bash
# In a separate terminal:
start_voicebox.bat
```

This activates the `voicebox` conda environment, starts the server on port `17493`, and pre-loads the 1.7B model into VRAM automatically.

---

## Adding New Concepts

1. Open **`concepts.txt`** and add a line:
   ```
   The Gladiator's Ghosting: A Roman gladiator is left on read and spirals.
   ```

2. Run the **Safe Patcher** to generate the config (only processes new/incomplete concepts):
   ```bash
   python tmp_v65_patcher_fixed.py
   ```
   This creates `configs/the_gladiators_ghosting.json`. See `configs/example_concept.json` for the schema.

---

## Running the Factory

```bash
# Make sure start_voicebox.bat is running first, then:
python factory_floor.py
```

**What happens automatically:**
- Skips concepts already captioned in `niche_output_captioned/`
- Generates TTS audio → applies intercom FX → merges with Meta AI clips
- Concatenates 5 scenes → runs Whisper → applies Blueprint aesthetic
- Outputs `niche_output_captioned/<concept>_Captioned.mp4`

**Production limit:** Set `DAILY_PRODUCTION_LIMIT` in `.env` (default: 4 per run).

---

## Running the Upload Scheduler (Daemon)

```bash
python upload_scheduler.py
```

- Runs **24/7 as a background daemon**
- Uploads up to `DAILY_UPLOAD_LIMIT` videos per day (default: 3)
- Upload windows: **08:00, 12:30, 19:30** (optimized for 18–35 EN audience)
- Uploads as `private` — you manually publish on YouTube Studio
- After upload: moves file to OneDrive, logs YouTube ID, cleans temp files

---

## Project Structure

```
.
├── factory_floor.py           # Main production orchestrator
├── llm_handler.py             # LLM narrative + visual prompt engine
├── audio_fx_engine.py         # TTS intercom filter
├── meta_scrapling_video.py    # Meta AI video generation
├── master_caption_engine.py   # Blueprint captions + audio mix
├── upload_scheduler.py        # Timed YouTube uploader daemon
├── youtube_uploader.py        # YouTube API helper
├── start_voicebox.bat         # One-click Voicebox server launcher
├── definitive_render_v65.py   # Safe patch + cleanup + produce (convenience wrapper)
│
├── configs/
│   └── example_concept.json  # Template — copy and fill for each concept
├── sfx/                       # Audio FX assets (drone, EKG, click, hiss, zap)
├── docs/                      # Setup guides (voicebox, Meta AI)
│
├── .env.example               # Config template
├── requirements.txt           # Python dependencies
└── concepts.txt               # Concept ideas queue
```

> **Generated at runtime (not in repo):**
> `niche_output/` · `niche_output_captioned/` · `upload_log.json` · `token.json` · `configs/*.json` (except example)

---

## The Aesthetic System

Every video is rendered with the **V6.4 Pure Blueprint** aesthetic:

| Layer | Detail |
|-------|--------|
| **Blueprint filter** | Vintage 1980s engineering schematic look |
| **Karaoke subtitles** | Word-level highlight: white → neon green |
| **Scene 1 Dossier Banner** | Anomaly Log #, Subject, CRITICAL THREAT (first 3s) |
| **Scene 5 System Seal** | Archive closure stamp with anomaly outcome |
| **t=12s Flash** | 1-frame `CONTAINMENT BREACH` subliminal |
| **Audio: Layer 1** | Sub-bass drone + hiss (foundation) |
| **Audio: Layer 2** | EKG heartbeat escalation (cuts at 12s) |
| **Audio: Layer 3** | Geiger click on bracket words (-15dB) |
| **Audio: Layer 4** | 12s "Audio Vacuum" zap (-20dB) |
| **Audio: Layer 5** | Typing SFX ambience |

---

## Narrative Format (V6.5 Eerie-Clinical)

The LLM (`llm_handler.py`) generates scripts using these rules:

- **Persona**: Eerie Archive AI — cold, forensic, from the year 2099
- **Style**: Accessible metaphors only — *brain-rot, soul-melt, digital poison* (no medical jargon)
- **Pacing**: Every VO line is exactly **9–11 words** (syncs to 5s video scenes)
- **Brackets**: 1–2 "pain words" per line in `[brackets]` → triggers Geiger click SFX

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Voicebox times out on first call | Run `start_voicebox.bat` and wait for "SERVER IS READY" before starting factory |
| `_Captioned.mp4` already exists | Delete it from `niche_output_captioned/` to re-render |
| YouTube OAuth fails | Delete `token.json` and re-run `upload_scheduler.py` to re-authenticate |
| ImageMagick errors | Verify path in `master_caption_engine.py` line 2 matches your install |
