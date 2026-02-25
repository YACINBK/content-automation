# 🧪 Meta AI Testing Tools

Standalone scripts for testing Meta AI video generation without running the full pipeline.

---

## 📁 Scripts

### 1. `test_meta_video.py` - Video Generation Tester

**Purpose:** Test Meta AI video generation with style presets (minimalist_dark, oil_painting, nostalgic_oil).

**Usage:**
```bash
python test_meta_video.py --prompt "A lighthouse in a storm" --style nostalgic_oil
```

**Features:**
- ✅ Generates raw videos without audio/slideshow assembly
- ✅ Downloads first video variant automatically
- ✅ Supports all 3 style presets
- ✅ Shows all generated variants

**Output:** `test_video_{style}.mp4`

---

### 2. `diagnose_meta.py` - Cookie Diagnostic Tool

**Purpose:** Check if Meta AI cookies are valid and provide update instructions.

**Usage:**
```bash
python diagnose_meta.py
```

**Features:**
- ✅ Tests cookie validity
- ✅ Provides step-by-step cookie update guide
- ✅ Shows which cookies are loaded
- ✅ Detects expired sessions

**When to use:**
- Before starting a new project
- After getting "NO VIDEO URLs FOUND" errors
- When videos stop generating
- Every 24-48 hours (cookies expire)

---

## 🔧 Cookie Management

### Current Cookies Location
Cookies are hardcoded in these files:
- `generate_reel.py` (line ~200)
- `test_meta_video.py` (line ~50)
- `video.py` (legacy pipeline)

### How to Update Cookies

1. **Open Chrome/Edge** and go to https://www.meta.ai/
2. **Open DevTools** (F12) → Application → Cookies → https://www.meta.ai
3. **Copy these 3 cookies:**
   - `datr`
   - `abra_sess`
   - `ecto_1_sess`
4. **Update in scripts:**
```python
cookies = {
    "datr": "YOUR_DATR_VALUE",
    "abra_sess": "YOUR_ABRA_SESS_VALUE",
    "ecto_1_sess": "YOUR_ECTO_1_SESS_VALUE"
}
```

### Cookie Lifespan
- **Typical duration:** 24-48 hours
- **Symptoms of expiration:**
  - "NO VIDEO URLs FOUND" warnings
  - Empty response arrays
  - 403 Forbidden errors

---

## 🎨 Style Presets

### `minimalist_dark`
- Grainy film texture
- Heavy silhouettes
- Dark atmosphere
- Golden hour lighting

### `oil_painting`
- Living oil painting aesthetic
- Heavy brushstrokes
- Chiaroscuro lighting
- Museum quality

### `nostalgic_oil` ✨
- Early 20th century European style
- Soft warm lighting
- Muted earth tones
- Textured brush strokes

---

## 📊 Example Test Results

```bash
$ python test_meta_video.py --prompt "A lighthouse in a storm" --style nostalgic_oil

🎨 Testing Meta AI Video Generation
   Style: nostalgic_oil
   Prompt: A lighthouse in a storm

📝 Full Prompt:
   A lighthouse in a storm, early 20th century oil painting, mid-shot, 
   wide angle, soft warm lighting, textured oil paint effect, muted earth 
   tones, classical European illustration, nostalgic mood, detailed brush 
   strokes, museum painting style

🔌 Connecting to Meta AI...
✅ MetaAI object created successfully

🎬 Generating video...
✅ Video generation successful!

🎥 Generated 4 video variant(s):
   [1] https://scontent-arn2-1.xx.fbcdn.net/...
   [2] https://scontent-arn2-1.xx.fbcdn.net/...
   [3] https://scontent-arn2-1.xx.fbcdn.net/...
   [4] https://scontent-arn2-1.xx.fbcdn.net/...

⬇️ Downloading first variant...
💾 Saved to: test_video_nostalgic_oil.mp4
   Size: 4.05 MB
```

---

## 🐛 Troubleshooting

### Issue: "NO VIDEO URLs FOUND"
**Solution:** Run `python diagnose_meta.py` and update cookies if needed.

### Issue: "ModuleNotFoundError: No module named 'metaai_api'"
**Solution:** The script automatically adds the path. Ensure `metaai-api/` folder exists.

### Issue: "Authentication failed"
**Solution:** Cookies expired. Follow the cookie update guide above.

---

## 🔗 Integration with Main Pipeline

These test scripts use the **same style presets** as `generate_reel.py`:
- Changes to `STYLES` dictionary should be synced across both files
- Cookie updates should be applied to all scripts
- Test scripts validate Meta AI connectivity before running full pipeline

---

**Created:** 2026-02-17  
**Branch:** `oil-style`  
**Purpose:** Rapid testing and debugging of Meta AI integration
