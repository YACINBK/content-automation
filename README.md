# Universal Content Engine

Command-line pipeline for automated video generation, processing, and distribution.

## Overview

This pipeline sequentially executes script generation, TTS synthesis, video clip sourcing, muxing, and YouTube distribution. 

### Core Components
- **Scripting (`llm_handler.py`)**: Interfaces with OpenRouter to generate scene-by-scene JSON structures from concept text.
- **Audio (`audio_fx_engine.py`)**: Handles TTS via a local Voicebox API and applies required audio filters.
- **Visuals (`meta_scrapling_video.py`)**: Automates Meta AI for video clip generation based on prompt parameters.
- **Muxing (`factory_floor.py`)**: Drives FFmpeg to sync audio/video sequences and concatenate master files.
- **Distribution (`youtube_uploader.py`)**: Uploads the final compiled `.mp4` via the YouTube Data API v3.

## Requirements

- Python 3.9+
- `ffmpeg` (must be accessible in system PATH)
- Local Voicebox API server (default: `http://127.0.0.1:17493`)
- Google Cloud OAuth credentials (`client_secrets.json`)
- OpenRouter API key

## Setup

1. Clone the repository and configure the virtual environment:
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate  # Windows
   pip install -r requirements.txt
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to include required API keys and endpoint paths.

3. Authenticate Google OAuth:
   Place `client_secrets.json` in the root directory. Initial execution of the upload module will trigger a browser OAuth flow to generate `token.json`.

## Usage

The pipeline is executed via `run.py`. Ensure your `concepts.txt` is populated in the target niche directory before running.

List configured niches:
```bash
python run.py --list
```

Execute the full pipeline sequentially:
```bash
python run.py --niche dark_productivity --all
```

Execute individual stages:
```bash
python run.py --niche dark_productivity --patch    # Generate JSON configurations
python run.py --niche dark_productivity --scrape   # Generate source video clips
python run.py --niche dark_productivity --factory  # Compile and mux media
python run.py --niche dark_productivity --upload   # Distribute to target platforms
```

## License
MIT License
