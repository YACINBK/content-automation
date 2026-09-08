# Content Automation Engine

Turn a written content idea into a finished short-form video with one command.

Choose a niche. Describe the content. Run the pipeline.

```bash
python3 run.py --niche dark_productivity --all
```

The engine generates the production plan, writes the narration, creates the visual scenes, assembles the video, burns timed captions, applies the selected audio treatment, and can distribute the finished result to YouTube and cloud storage.

## See The Workflow

```text
concepts.txt
    |
    v
LLM production plan
    |
    +--> five narrative scenes
    +--> five visual prompts
    +--> metadata and sound cues
    |
    v
Meta AI clips + local Voicebox narration
    |
    v
FFmpeg assembly + audio treatment
    |
    v
Whisper timestamps + styled captions
    |
    v
Captioned MP4
    |
    +--> optional YouTube upload
    +--> optional OneDrive / Google Drive archive
```

## A Three-Line Demo

### 1. Choose a niche

```bash
python3 run.py --list
```

```text
Available niches:
   dark_productivity              (no output yet)
```

### 2. Write a concept

Edit `niches/dark_productivity/concepts.txt`:

```text
Concept 1: The Spartan's Draft
Subject: A heavily-armored Spartan Warlord.
Modern Habit: He must write a polite corporate email on a tiny keyboard.
Psychological Twist: A warrior who fears no army begins to fear passive-aggressive notifications.
```

The title becomes the project name. The complete block becomes the creative brief. No JSON production plan needs to be written by hand.

### 3. Run everything

```bash
python3 run.py --niche dark_productivity --all
```

The result is produced under the selected niche:

```text
niches/dark_productivity/
  configs/the_spartans_draft.json
  niche_output/production_the_spartans_draft/
  niche_output_captioned/the_spartans_draft_Captioned.mp4
```

## Make Every Niche Feel Different

The pipeline is reusable, but the creative identity belongs to the niche. Add these files inside the target niche:

```text
niches/<your_niche>/
  concepts.txt
  niche.env
  prompts/
    persona.txt
    aesthetic.txt
  assets/
    ...optional audio assets...
```

### Narrative Profile

`prompts/persona.txt` defines who the content engine sounds like.

```text
You are a calm museum historian documenting lost civilizations.
Use precise language, quiet suspense, and evidence-led storytelling.
```

### Visual Profile

`prompts/aesthetic.txt` defines the visual direction appended to generated scene prompts.

```text
, natural documentary light, weathered stone textures, wide archaeological framing, restrained colors, vertical 9:16 composition.
```

Change those two files and the same CLI can produce a completely different channel identity without changing the engine code.

### Audio Profile

Set the voice treatment in the niche's `niche.env`:

```dotenv
NICHE_NAME=Dark Productivity
GDRIVE_FOLDER=DarkProductivity
ONEDRIVE_SUBFOLDER=DarkProductivity
VOICE_FILTER=brutalist
```

Available audio modes:

| Mode | Result |
| --- | --- |
| `none` | Voice pass-through |
| `intercom` | Band-pass, boosted radio/intercom character |
| `brutalist` | High-pass, normalization, compression, and a harder vocal presence |

The Voicebox profile can also be selected per niche:

```dotenv
VOICEBOX_PROFILE_ID=your-voicebox-profile-id
```

For compatibility with older local setups, `DEFAULT_VOICE_ID` is also accepted from `.env`.

## What `--all` Does

| Stage | What happens | Main output |
| --- | --- | --- |
| Patch | Turns concept blocks into structured five-scene JSON plans | `configs/<slug>.json` |
| Factory | Generates narration and clips, muxes scenes, creates the master reel, and renders captions | `niche_output_captioned/<slug>_Captioned.mp4` |
| Upload | Uploads, schedules, archives, logs, and cleans completed work | YouTube + cloud archives |

Run a single stage when you want control:

```bash
python3 run.py --niche dark_productivity --patch
python3 run.py --niche dark_productivity --factory
python3 run.py --niche dark_productivity --upload
```

The factory is intentionally sequential. It uses resume checks and one worker per stage to favor reliable browser automation, local speech synthesis, and media assembly over fragile parallel throughput.

## Why This Is More Than A Script

- **Brief in, production plan out**: the LLM converts natural-language ideas into a repeatable scene schema.
- **Niche-aware generation**: persona, visual direction, voice profile, and audio treatment travel with the niche.
- **Automatic scene production**: each concept becomes paired narration and visual scenes.
- **Production-grade finishing**: FFmpeg assembly, word-level Whisper timing, styled captions, overlays, and audio processing happen in sequence.
- **Restart-friendly workflow**: existing configs, clips, audio, synced scenes, and completed videos are reused where possible.
- **Distribution built in**: completed videos can be uploaded, scheduled, archived, logged, and cleaned up without manually moving files between stages.

## Project Map

```text
run.py                    one CLI for niche selection and stage control
concepts.txt              content briefs for the active project
niches/<name>/            niche configuration, prompts, assets, and outputs
configs/                  generated production plans
llm_handler.py            narrative and visual prompt generation
factory_floor.py          narration, clips, assembly, and orchestration
audio_fx_engine.py        audio post-processing profiles
audio_fx_engine.py        selectable voice processing profiles
master_caption_engine.py  Whisper timing, captions, overlays, and final mix
meta_scrapling_video.py   Meta AI browser automation
upload_scheduler.py       YouTube and cloud distribution
```

## Setup

Requirements:

- Python 3.9+
- FFmpeg available on `PATH`, or configured with `FFMPEG_PATH`
- An OpenRouter API key
- Meta AI session cookies
- A local Voicebox server
- Google OAuth credentials for upload and Drive features
- A reachable OneDrive destination when archiving is enabled

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

Keep `.env`, OAuth files, tokens, and generated media out of Git. Voicebox setup is documented in [docs/voicebox_setup.md](docs/voicebox_setup.md). The deeper operational handoff is in [docs/PROJECT_HANDOFF.md](docs/PROJECT_HANDOFF.md).

## Current Boundary

This repository automates the production workflow; it does not include the external Meta AI account, Voicebox service, API credentials, generated media, or cloud deployment. Those integrations are intentionally configured at runtime.

## License

MIT License
