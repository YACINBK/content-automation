# Content Automation Engine

Turn a written content idea into a finished short-form video with one command.

Name a creative workspace. Give it a content brief. Run the pipeline.

```bash
python3 run.py --niche dark_productivity --all
```

The engine generates the production plan, writes the narration, creates the visual scenes, assembles the source video and voice track, burns timed captions, layers the selected audio and visual treatment on top, and can distribute the finished result to YouTube and cloud storage.

The command-line requirement is only the niche name. The production requirement is one or more content blocks in that niche's `concepts.txt`; those blocks are the material sent to the LLM. A niche name by itself creates or selects a workspace, but it cannot generate a meaningful video without content.

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

### 1. Name a workspace

```bash
python3 run.py --list
```

```text
Existing workspaces:
   dark_productivity              (no output yet)
```

This is not a fixed menu of products. `--niche` is a workspace key. Use an existing workspace or name a new one; the CLI creates its folders and starter files automatically.

### 2. Write a concept

For the example workspace, edit `niches/dark_productivity/concepts.txt`:

```text
Concept 1: The Spartan's Draft
Subject: A heavily-armored Spartan Warlord.
Modern Habit: He must write a polite corporate email on a tiny keyboard.
Psychological Twist: A warrior who fears no army begins to fear passive-aggressive notifications.
```

The title becomes the project name. The complete block becomes the creative brief. No JSON production plan needs to be written by hand. Add more blocks to generate more projects in the same run.

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

## Make Every Workspace Feel Different

The pipeline is reusable, but the creative identity belongs to the workspace. Add these files inside the target niche:

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

Change those two files and the same CLI can produce a completely different channel identity without changing the engine code. They shape the LLM's narrative and visual instructions; they do not replace the generated video clips or narration.

### Audio Treatment

The generated Voicebox narration is the base audio layer. Set an optional treatment in the niche's `niche.env`:

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

The Voicebox profile can also be selected per workspace:

```dotenv
VOICEBOX_PROFILE_ID=your-voicebox-profile-id
```

For compatibility with older local setups, `DEFAULT_VOICE_ID` is also accepted from `.env`.

### Visual Treatment

The generated Meta AI clips are the base visual layer. The aesthetic file influences how those clips are requested, while the caption renderer adds its finishing overlays, captions, metadata, and closure treatment on top of the assembled video. In other words: the profile shapes and finishes the assets produced by the pipeline; it is not a replacement asset source.

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
run.py                    one CLI for workspace selection and stage control
concepts.txt              content briefs for the active project
niches/<name>/            niche configuration, prompts, assets, and outputs
configs/                  generated production plans
llm_handler.py            narrative and visual prompt generation
factory_floor.py          narration, clips, assembly, and orchestration
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
