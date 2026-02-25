# Voicebox Storytelling Engine 🎬

A universal, "Narration-First" video production pipeline. This engine automates the entire process of turning a script into a synchronized, aesthetically graded video reel using the local **Voicebox API** and **Meta AI**.

## ✨ Why this is better
Unlike the old manual ways, this engine:
1.  **Starts with Narration**: The voice dictates the timing and the number of scenes.
2.  **Automatic Syncing**: Every visual clip is perfectly scaled to match the audio's natural breath.
3.  **Aesthetic Grading**: Automatically applies cinematic gothic grading (saturation, crimson shift, film grain) to every frame.
4.  **One-Shot Production**: One command builds the entire timeline, generates visuals, and muxes the master.

---

## 🚀 Getting Started

### 1. Requirements
- **FFmpeg**: Installed on your system path.
- **Voicebox API**: Running locally on port 17493.
- **Python 3.10+**

### 2. Setup
- **Existing Voicebox Users**: See the [Fast-Track Guide](file:///C:/Users/YACIN/Desktop/test/test/docs/voicebox_setup.md).
- **New Users**:
  ```bash
  # Install dependencies
  pip install -r requirements.txt

  # Create your .env file
  cp .env.example .env
  # Edit .env and paste your Meta AI cookies and Voice ID
  ```

### 3. Usage
Run the engine with a project configuration:
```bash
python voicebox_story_engine.py --config configs/bloody_mary_v5.json
```

---

## 📐 Narration-First Workflow
The engine follows a 4-Phase pipeline:
1.  **Blueprinting**: Generates the full narration sequentially and calculates the total duration $T$.
2.  **Visual Logic**: Calculates $N$ scenes (approx 5s each) and precise duration $D$ per clip ($D = T / N$).
3.  **Generation**: Calls Meta AI with your prompts + the "Anchor Block" (aesthetic context).
4.  **Assembly**: FFmpeg applies grading, trims clips to $D$, and muxes the final master video.

## 🎨 Configuration
Modify files in `configs/` to tweak the aesthetic or the script:
- `gothic_grade`: Control saturation, brightness, and "crimson" shift.
- `anchor_block`: Common keywords applied to every visual generation for consistency.
- `visual_prompts`: A sequence of prompts the engine cycles through.
