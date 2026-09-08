# V6.5 Production Handoff

This document describes the v6.5 source currently adopted as the repository baseline. It is grounded in the implementation rather than in older branch names or stale `main` documentation.

## Product Verdict

The strongest v6.5 capability is a simple niche-based production workflow:

```text
niche name + concepts.txt
        -> LLM production configs
        -> Meta AI visual clips + Voicebox narration
        -> FFmpeg scene assembly
        -> Whisper/MoviePy captions and audio finishing
        -> optional YouTube and OneDrive distribution
```

The user selects the niche through the CLI. The actual content description is written in that niche's `concepts.txt`; v6.5 does not expose a direct free-text `--description` argument.

## CLI Contract

`run.py` is the single entry point:

```bash
python3 run.py --list
python3 run.py --niche dark_productivity --patch
python3 run.py --niche dark_productivity --factory
python3 run.py --niche dark_productivity --upload
python3 run.py --niche dark_productivity --all
```

`--all` executes patch, factory, and upload in that order. The CLI validates the selected niche, injects absolute paths into child processes, loads its `niche.env`, and creates the working directories for configs, production output, and captioned output.

The current v6.5 implementation expects an existing niche and an existing `concepts.txt`. It does not bootstrap a new niche from the CLI.

## Stage Behavior

### 1. Patch

`tmp_v65_patcher_fixed.py` reads concept blocks beginning with `Concept N: Title`. It converts each title into a safe filename, sends the full description to `llm_handler.py`, and writes a JSON plan under the selected `configs/` directory.

A populated config containing `image_prompts` is skipped. This protects completed plans from being regenerated accidentally.

### 2. Factory

`factory_floor.py` coordinates the production stages:

- generates scene narration through the local Voicebox API;
- generates Meta AI visual clips through the browser automation layer;
- retries Voicebox requests up to three times;
- applies the v6.5 audio effect pass;
- muxes each clip and narration with FFmpeg;
- concatenates the scenes into a master reel;
- invokes `master_caption_engine.py` for captions and final finishing.

The worker architecture uses queues, but all worker counts are set to one. This is effectively sequential processing and is a deliberate reliability choice for browser automation, Voicebox, and FFmpeg workloads.

### 3. Upload

`upload_scheduler.py` processes captioned MP4s, uploads them to YouTube, moves them to the configured OneDrive destination, writes `upload_log.json`, and removes intermediate local production folders after successful upload handling.

Google Drive support exists in `drive_uploader.py` and is part of the repository's service integration surface. Upload behavior requires OAuth credentials and a valid local cloud path; it is not available in a clean checkout without those external prerequisites.

## Theme and Style Behavior

The v6.5 source has a built-in Chrono-Clinical identity. Its LLM prompts, caption styling, dossier metadata, visual overlays, and layered audio effects are implemented directly in the pipeline modules.

Individual overlay assets are optional: the caption engine warns and skips a missing overlay image. The complete audio finishing pass still expects its referenced sound files to exist in the runtime `sfx/` directory.

Optional niche customization is supported through the files and values created by `run.py`: `prompts/persona.txt` changes the narrative identity, `prompts/aesthetic.txt` changes the visual direction sent to Meta AI, and `VOICE_FILTER` in `niche.env` selects `intercom`, `brutalist`, or `none` audio treatment. Optional runtime assets can be added under the niche `assets/` directory for the finishing stage.

## Runtime Configuration

Global `.env` values provide secrets and machine-specific paths, including:

- `OPENROUTER_API_KEY`;
- `META_COOKIES`;
- `FFMPEG_PATH`;
- `VOICEBOX_BASE_URL`;
- OneDrive configuration;
- Google and YouTube OAuth file locations where applicable.

Per-niche `niche.env` currently provides branding and cloud destination values such as:

```dotenv
NICHE_NAME=Dark Productivity
GDRIVE_FOLDER=Niche
ONEDRIVE_SUBFOLDER=DarkProductivity
```

Never commit `.env`, OAuth tokens, client secrets, generated media, or runtime output.

## Files and Outputs

For a niche named `dark_productivity`:

```text
niches/dark_productivity/
  concepts.txt
  niche.env
  configs/<concept>.json
  niche_output/production_<concept>/
  niche_output_captioned/<concept>_Captioned.mp4
```

The generated production folder can contain scene audio, source clips, processed audio, synced scenes, the concatenated master, timestamps, and temporary finishing files.

## Maintenance Boundaries

- Meta AI selectors and browser behavior are external dependencies.
- Voicebox must be started separately before the factory stage.
- FFmpeg and ImageMagick paths in the v6.5 source reflect the original Windows development environment and should be checked before portability claims are made.
- The v6.5 tree includes the historical `tmp_v65_patcher_fixed.py` name; it is the active patcher invoked by `run.py` and should be renamed only with a coordinated CLI update.
- The hard-coded LLM credential was removed during adoption; credentials must come from environment variables.

## Baseline Status

The active local `main` branch is based on `origin/v6.5-chrono-clinical`. The former main-line documentation edits are preserved separately in a Git stash and are not being used as the source of truth for this documentation.
