# AI Image Vectorization Pipeline (8GB VRAM Optimized)

This repository contains a full-stack, AI-powered image generation and vectorization pipeline optimized explicitly for apparel design (Screen Printing and DTF) under strict **8GB VRAM hardware constraints** (RTX 4060).

## 🚀 Features

- **Automated Prompt Engineering**: DeepSeek/Ollama autonomously rewrites your basic ideas into FLUX-optimized vector-style prompts.
- **Image Generation**: Automated FLUX API calls via ComfyUI.
- **Semantic Extraction**: Uses SAM 2 (Segment Anything 2) to surgically target subjects and punch out trapped negative space based on text prompts.
- **Advanced Edge Matting**: Uses `backgroundremover` (`u2net_human_seg`) with customizable alpha matting erosion to create perfectly soft or sharp edges for apparel printing.
- **Spot Color Quantization**: Converts images to human perceptual color space (Oklab) and uses Weighted K-Means to quantize down to a strict number of spot colors (e.g., 6 colors for screen printing).
- **Stacked SVG Tracing**: Uses `vtracer` to convert the quantized raster into a clean, layer-separated SVG vector.
- **Batch Processing**: An external orchestrator (`batch_processor.py`) guarantees 100% VRAM flushing between every image to prevent PyTorch memory leaks.

## 🛠️ Installation & Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/YACINBK/image-vectorization.git
   cd image-vectorization
   ```

2. **Conda Environment**:
   ```bash
   conda create -n comfy_vectors python=3.10
   conda activate comfy_vectors
   pip install -r requirements.txt
   ```
   *(Ensure you have `backgroundremover`, `scour`, `vtracer`, `scikit-learn`, `opencv-python`, and `torch` installed)*

3. **Backend Requirements**:
   - **ComfyUI**: Must be running locally on `http://127.0.0.1:8188` to process FLUX generations.
   - **LLM**: Either local Ollama or an active DeepSeek API key.

## 💻 Usage

### 1. Generate & Vectorize from Scratch
Generates an image from a prompt, removes the background, color quantizes, and outputs an SVG.
```bash
python generate_from_scratch.py \
  --prompt "A fierce cybernetic tiger head" \
  --mode svg \
  --colors 6 \
  --erode_size 10 \
  --fg_threshold 240
```

### 2. Process an Existing Image (Bypass Generation)
Process an existing image through the alpha matting and vectorization engines.
```bash
python generate_from_scratch.py \
  --input_image "path/to/image.jpg" \
  --mode both \
  --colors 8 \
  --erode_size 12
```

### 3. VRAM-Safe Batch Processing
Process an entire folder of images. Guaranteed to stay under 8GB VRAM by aggressively flushing memory between subprocesses.
```bash
python batch_processor.py \
  --input_dir "path/to/folder" \
  --mode svg \
  --colors 8 \
  --erode_size 10
```

## 🧠 The Pipeline Architecture

1. **LLM Director (`llm_director.py`)**: Enhances basic prompts.
2. **Comfy Orchestrator (`comfy_orchestrator.py`)**: Talks to ComfyUI.
3. **Smart Extractor (`smart_extractor.py`)**: Grounding DINO + SAM 2 for semantic isolation and hole punching.
4. **Vector Prep Engine (`vector_prep.py`)**: 
   - `backgroundremover` Alpha Matting
   - Oklab Perceptual K-Means Quantization
   - Python VTracer Bindings
   - Topological SVG Optimization (Scour)
