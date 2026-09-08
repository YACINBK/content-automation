# V6.5 Chrono-Clinical Content Engine

A niche-driven short-form video production pipeline. The v6.5 workflow turns written concepts into five-scene video plans, generates Meta AI clips, creates local Voicebox narration, assembles and captions the result, and optionally uploads and archives completed videos.

This repository is an automation orchestrator. It depends on external services and local tools: an OpenRouter-compatible LLM, Meta AI browser access, Voicebox, FFmpeg, Whisper, MoviePy, and Google OAuth for distribution.

## The Main User Experience

The intended workflow is deliberately small:

1. Choose a niche with the CLI.
2. Add one or more content descriptions to that niche's `concepts.txt`.
3. Run the complete pipeline.

```bash
python3 run.py --niche dark_productivity --all
```

The content description is file-based in v6.5. There is no direct `--description` command-line argument. The CLI selects the niche workspace; the concept file supplies the production ideas.

## Pipeline

`--all` runs three stages in order:

1. **Patch** (`tmp_v65_patcher_fixed.py`): parses concept blocks and asks the LLM for one JSON production plan per concept.
2. **Factory** (`factory_floor.py`): generates narration through Voicebox, requests visual clips through Meta AI, applies audio processing, muxes each scene with FFmpeg, concatenates the master reel, and sends it to the caption engine.
3. **Upload** (`upload_scheduler.py`): uploads completed captioned videos to YouTube, syncs them to OneDrive, records an upload log, and cleans intermediate production files.

Stages are also available independently:

```bash
python3 run.py --list
python3 run.py --niche dark_productivity --patch
python3 run.py --niche dark_productivity --factory
python3 run.py --niche dark_productivity --upload
```

The factory uses queue-based workers but sets every worker limit to one. The effective design is sequential, prioritizing Meta AI and Voicebox reliability over throughput. Existing audio, clips, synced scenes, configs, and captioned outputs are reused where the stage supports resume behavior.

## Repository Layout

```text
run.py                    niche CLI and environment injection
concepts.txt              active concept descriptions
configs/                  generated JSON plans and example schema
niches/<name>/niche.env   niche branding and cloud destination values
llm_handler.py            LLM prompts, JSON generation, and Meta negotiation
factory_floor.py          narration, visual generation, muxing, and orchestration
audio_fx_engine.py        Voicebox audio post-processing
master_caption_engine.py  Whisper timestamps, captions, overlays, and final mix
meta_scrapling_video.py   Playwright Meta AI automation
upload_scheduler.py       YouTube, OneDrive, and upload-ledger workflow
docs/                     integration and handoff documentation
```

## Niche and Content Contract

The v6.5 CLI expects the selected niche to already exist:

```text
niches/
  dark_productivity/
    niche.env
    concepts.txt
    configs/
    niche_output/
    niche_output_captioned/
```

The v6.5 patcher accepts concept blocks beginning with `Concept N: Title`, followed by a description. It uses the title to create a safe config filename and sends the full block to the LLM. Populated configs containing `image_prompts` are skipped so completed plans are not overwritten.

`niche.env` currently carries values such as `NICHE_NAME`, `GDRIVE_FOLDER`, and `ONEDRIVE_SUBFOLDER`. Global secrets and service paths belong in `.env`, which must never be committed.

## Visual and Audio Direction

V6.5 has a built-in Chrono-Clinical presentation: schematic visual prompts, retro-clinical captions, dossier metadata, CRT/film overlays, and layered audio effects. The renderer treats individual overlay and sound files as optional at runtime; missing overlay assets are skipped with a warning, while required audio assets must be available for the complete finishing pass.

The v6.5 configuration layer now supports optional niche customization. Add `prompts/persona.txt` to change the narrative identity, `prompts/aesthetic.txt` to change the visual direction sent to Meta AI, and set `VOICE_FILTER` in `niche.env` to `intercom`, `brutalist`, or `none` for audio treatment. Optional runtime assets can be placed in the niche `assets/` directory and are passed to the finishing stage.

## Prerequisites

- Python 3.9+
- FFmpeg on `PATH` or configured with `FFMPEG_PATH`
- Python packages from `requirements.txt`
- A valid `OPENROUTER_API_KEY`
- Meta AI session cookies in `.env`
- A local Voicebox server, normally at `http://127.0.0.1:17493`
- Google OAuth client credentials for `--upload`
- A reachable OneDrive destination for upload archiving

Install the Python dependencies and keep credentials local:

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

See [docs/voicebox_setup.md](docs/voicebox_setup.md) for the local TTS service setup.

## Current Scope

This is the v6.5 production pipeline source and its operational configuration, not a hosted service. The repository does not include API credentials, Meta AI access, Voicebox itself, generated media, or a deployment environment.

## License

MIT License
