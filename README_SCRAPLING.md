# Meta AI Video Automation (Scrapling Edition) 🚀

This module Provides a clean, automated way to generate AI videos on [Meta AI](https://www.meta.ai/) using the `scrapling` engine. It bypasses current API restrictions by simulating a real browser session with authenticated state.

---

## 📦 Prerequisites

1.  **Python 3.10+**
2.  **Scrapling Library**:
    ```bash
    pip install "scrapling[fetchers]"
    ```
3.  **Playwright Binaries**:
    ```bash
    playwright install chromium
    ```

---

## 🔑 Authentication (Cookies)

Meta AI requires an authenticated session to generate video. You must provide your session cookies in a `.env` file.

### 1. Extracting Cookies
- Open `meta.ai` in your Chrome/Edge browser and log in.
- Use a browser extension like **"EditThisCookie"** or **"Cookie-Editor"** to export your cookies as a **JSON Array**.
- Required cookies typically include: `datr`, `ecto_1_sess`, and `dpr`.

### 2. Setup Environment
Create a `.env` file in the root directory (refer to `.env.scrapling.example`):
```env
# Paste the ENTIRE JSON array of cookies here (surround with single quotes)
META_COOKIES='[{"name": "datr", "value": "...", ...}, ...]'
```

---

## 🎬 Usage

### 1. CLI Usage
Run the generator directly from your terminal:
```bash
python meta_video_generator.py --prompt "A laboratory rat in a glowing maze" --output my_video.mp4
```

**Options:**
- `--prompt`: (Required) Your creative prompt.
- `--output`: (Optional) Filename to save the .mp4.
- `--headless`: (Optional) Run without a visible browser window.

### 2. Python Integration
Import the generator into your existing pipeline:
```python
import asyncio
from meta_video_generator import generate_meta_video

async def main():
    success = await generate_meta_video(
        prompt="A pulsing anatomical human brain floating in a lab tank",
        output_path="brain_render.mp4",
        headless=False
    )
    if success:
        print("Masterpiece ready!")

asyncio.run(main())
```

---

## 🛠️ Troubleshooting

-   **Headless Mode**: If the generation fails or hangs, run **without** `--headless`. Meta AI sometimes requires a visible browser instance to stabilize the socket connection.
-   **Cookie Expiry**: If you get redirected to a login page, your `ecto_1_sess` cookie has likely expired. Simply re-export your cookies from your browser.
-   **Render Time**: Video generation can take anywhere from 45 seconds to 3 minutes. The script has a built-in 4-minute timeout.

---

## 🛡️ License & Disclaimer
This tool is for educational purposes. Use responsibly and ensure compliance with Meta AI's Terms of Service.
