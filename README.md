# 🎭 Poetry Video Automation Hub

An advanced, end-to-end automation suite for creating stunning vertical poetry videos. This system transforms raw text or abstract topics into cinematic experiences featuring **AI-narrated poetry**, **verse-synchronized internal imagery**, and **classic oil-painting aesthetics**.

---

## 🌟 Core Capabilities

*   **🧠 Intelligent Selection**: Automatically selects famous, public-domain poetry based on your chosen theme.
*   **📝 Raw Text Support**: Input any poem directly—the AI handles segmentation, titles, and visual prompts.
*   **🎨 Human-Centric Imagery**: Optional `--include-people` flag for soulful, character-focused portraits.
*   **🎙️ Expressive Narration**: Pro-level ElevenLabs voices with contemplative poetry-optimized pacing.
*   **📦 Bulk Processing**: Generate dozens of videos at once from a simple text list.
*   **�‍❤️‍👨 Romance Aesthetic**: **New:** Optional `--romance` flag for flirty, intimate, and high-passion visuals.
*   **�🔇 Silent Fallback**: Automatically assembles high-quality silent videos if API limits are reached.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.8+**
- **FFmpeg**: [Download here](https://ffmpeg.org/download.html) (Ensure it's in your system PATH)
- **API Keys**: OpenRouter (for LLM) and ElevenLabs (for Voice)

### 2. Installation
```bash
# Clone the repo and install dependencies
pip install metaai-api requests moviepy python-dotenv elevenlabs
```

### 3. Environment Setup
Create a `.env` file in the root directory:
```env
OPENROUTER_API_KEY=your_key_here
ELEVEN_API_KEY=your_key_here
```

---

## 🎬 How to Use

### Method A: Topic-Based (AI Choice)
Let the AI choose a famous poem for you.
```bash
python generate_poetry_video.py --topic "solitude and the sea" --include-people
```

### Method B: Direct Poem Input (Manual Text)
Provide your own poetry text. The system will segment it automatically.
```bash
python generate_poetry_video.py --poem-text "We were never meant to exist in the same world.
But please, just give me this one moment.
Let me explain why your light is different.
In a galaxy crowded with burning stars, you’re the only moon I see.
But wait, it’s more than just that.
Among eight billion souls, my eyes only hunt for your reflection.
You are the fire I would reach for, even if it meant turning to ash.
The warmth is worth the wreckage, and I’d pay that price every time.
Even though we’ll never share a lifetime, allow me this one truth.
I want to love you aloud in ways you’ve never heard.
And perhaps, in ways you’ve never felt before.
If only for a single heartbeat.
" --include-people --romance --voice morino 
```

### Method C: Bulk Generation
Process multiple poems listed in `generate-bulk.txt` (separated by `***`).
```bash
python bulk_processor.py
```

---

## 📋 Complete CLI Options

| Flag | Description |
| :--- | :--- |
| `--topic` | Theme for AI selection (e.g., "romance", "nature"). |
| `--poem-text` | Direct input of poem text (skips AI selection). |
| `--romance` | 👩‍❤️‍👨 **New:** Enforce a super romantic and flirty aesthetic for imagery. |
| `--include-people` | 👩 **New:** Prioritizes human subjects in the oil-painting style. |
| `--retry-images` | Enables automatic retries for image generation failures. |
| `--dry-run` | Shows what *would* happen (Poem + Prompts) without spending credits. |
| `--skip-voice` | Skips narration (useful for creating silent videos). |
| `--session-name` | Resume an existing session (skips AI selection). |
| `--resolution` | Set custom size (default: `1080x1920`). |
| `--drive-folder` | ☁️ **New:** Upload results to a specific Google Drive folder. |
| `--delete-local` | 🗑️ **New:** Delete local files after successful Drive upload. |

### ☁️ Google Drive Integration

You can automatically backup your final videos and metadata to Google Drive:

1.  Enable **Google Drive API** in Google Cloud Console.
2.  Create **OAuth2 Desktop App** credentials and download as `credentials.json`.
3.  Install dependencies: `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`
4.  Run with the flag:
    ```bash
    python generate_poetry_video.py --topic "nature" --drive-folder "Automated Videos"
    ```
    *On the first run, a browser window will open for one-time authentication.*

---

## 🛠️ Post-Processing & Utilities

### 🔇 Silent Video Assembly
If you run out of ElevenLabs credits, or just want a silent version:
```bash
python assemble_silent.py --metadata metadata/your_poem_metadata.json
```

### 💰 Credit Checker
Quickly see how many characters you have left in ElevenLabs:
```bash
python check_credits.py
```

---

## 🔑 Meta AI Setup (Critical)
To generate the oil-painting images, you must provide your session cookies in `image_generator.py`:
1.  Log in to [Meta AI](https://www.meta.ai/).
2.  Open **Developer Tools** (F12) > **Application** > **Cookies**.
3.  Copy values for `datr`, `abra_sess`, and `ecto_1_sess`.
4.  Paste them into the `cookies` dictionary at the top of `image_generator.py`.

---

## 📂 Project Organization

-   📂 `final_videos/`: **Your final products.** 
-   📂 `metadata/`: Detailed JSON history of every run.
-   📂 `examples/`: Template JSONs for manual editing.
-   📂 `outputs/`: Temporary image and audio fragments.
-   ⚙️ `bulk_processor.py`: The mass-generation orchestrator.
-   ⚙️ `poetry_engine.py`: The core LLM logic.
-   ⚙️ `image_generator.py`: The Meta AI engine.

---

## 🎨 Aesthetic Philosophy
The system uses a signature **Early 20th Century European Oil Painting** style:
-   **Lighting**: Soft, warm, amber hues.
-   **Texture**: Muted earth tones with visible brush strokes.
-   **Mood**: Nostalgic, museum-quality illustrations.

---

## 📄 License
MIT. Made for creative automation. 🎭🎞️✨
