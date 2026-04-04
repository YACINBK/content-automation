import os
import sys
import json
import argparse
import time
from comfy_orchestrator import ComfyUIOrchestrator
from vector_prep import VectorPrepEngine
from llm_director import LLMDirector
from smart_extractor import SmartExtractor

def main():
    parser = argparse.ArgumentParser(description="Master Pipeline: Generate (FLUX) -> Vectorize (VTracer)")
    parser.add_argument("--prompt", type=str, required=True, help="Description of the hoodie artwork")
    parser.add_argument("--art_style", type=str, default="vector", choices=["vector", "oil"], help="Aesthetic style of the generated graphic")
    parser.add_argument("--colors", type=int, default=8, help="Number of spot colors for screen printing (Max 8 recommended)")
    parser.add_argument("--fg_threshold", type=int, default=240, help="Level 1 BG removal threshold (0-255). Lower to keep more subject edges.")
    parser.add_argument("--auto_smart_extract", action="store_true", help="Level 2 AUTO: Ollama autonomously pilots GSAM2 to extract the main subject.")
    parser.add_argument("--level2_extract", type=str, default=None, help="Level 2 MANUAL: GSAM2 Target. Provide a text string (e.g. 'cat, skateboard') to exclusively extract.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--llm_provider", type=str, default="deepseek", choices=["deepseek", "ollama"], help="LLM Provider to use")
    parser.add_argument("--llm_model", type=str, default="DeepSeek-V3-0324", help="Model name for the chosen provider")
    args = parser.parse_args()

    print("\n" + "="*50)
    print("🚀 INITIALIZING MASTER PIPELINE: USE CASE A")
    print("="*50)

    # 1. LLM Prompt Expansion (The Missing Brain)
    print("\n" + "="*50)
    print("🧠 LLM DIRECTOR: ENHANCING PROMPT")
    print("="*50)
    
    llm_dir = LLMDirector(provider=args.llm_provider, model_name=args.llm_model)
    
    # Pre-calculate SAM2 Auto-Extraction if requested
    sam2_target = args.level2_extract
    
    if not llm_dir.check_connection():
        print(f"[!] Warning: {args.llm_provider.upper()} service is not available.")
        print("[!] Defaulting to raw prompt bypass.")
        final_prompt = args.prompt
        if args.auto_smart_extract:
            print("[!] LLM is offline. Falling back to raw prompt for SAM 2 Auto Extraction.")
            sam2_target = args.prompt
    else:
        final_prompt = llm_dir.enhance_prompt_for_flux(args.prompt, art_style=args.art_style)
        
        # Soft Relay: Giving VRAM time to flush back to 0% before ComfyUI
        if args.llm_provider == "ollama":
            print(f"\n[!] SOFT RELAY: Forcing Ollama to drop model from VRAM...")
            print(f"[*] Waiting 5 seconds for CUDA cache to fully flush before waking ComfyUI...")
            time.sleep(5)
            print(f"[OK] VRAM flush assumed complete. Handing baton to ComfyUI.\n")
        else:
            print(f"\n[OK] DeepSeek requires 0GB VRAM. Bypassing Soft Relay. Handing baton to ComfyUI instantly.\n")

    print(f"[*] FINAL PROMPT: {final_prompt}")

    # 2. Generate Image via ComfyUI
    workflow_path = "flux_schnell_api.json"
    if not os.path.exists(workflow_path):
        print(f"[X] ERROR: Missing API workflow file: {workflow_path}")
        sys.exit(1)
        
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)
        
    # Inject prompt and seed
    workflow["6"]["inputs"]["text"] = final_prompt
    seed = args.seed if args.seed is not None else int.from_bytes(os.urandom(4), 'big')
    workflow["3"]["inputs"]["seed"] = seed
    
    print(f"[*] SEED: {seed}\n")
    
    orchestrator = ComfyUIOrchestrator()
    generated_img_path = orchestrator.generate_image(workflow)
    
    if not generated_img_path or not os.path.exists(generated_img_path):
        print("[X] ERROR: Image generation failed. Is ComfyUI running?")
        sys.exit(1)

    print("\n" + "="*50)
    print("🎨 STARTING VECTORIZATION ENGINE")
    print(f"[*] SPOT COLORS: {args.colors}")
    print("="*50)

    # 2. Process and Vectorize
    engine = VectorPrepEngine()
    
    # AUTO SMART EXTRACT: Wait until AFTER the image exists, then ask the VLM!
    if args.auto_smart_extract and not args.level2_extract:
        print("\n" + "="*50)
        print("👁️ VLM SURGEON: ANALYZING IMAGE FOR SEMANTIC EXTRACTION")
        print("="*50)
        
        # This will use Gemini 2.0 Flash via OpenRouter by default
        vlm_target = llm_dir.analyze_image_for_extraction(generated_img_path)
        if vlm_target:
            sam2_target = vlm_target
        else:
            print("[!] VLM Analysis failed. Falling back to Level 1 Extraction.")
            sam2_target = None
            
    # Decide which Extraction Level to run based on the user's flags
    if sam2_target:
        # STEP A1: The Semantic Surgeon (SAM 2)
        print(f"\n[*] INITIATING HYBRID PROTOCOL Phase 1: Semantic Isolation (SAM 2)")
        print(f"[*] Extraction Targets: '{sam2_target}'")
        extractor = SmartExtractor()
        isolated_img = extractor.extract_subject(generated_img_path, sam2_target)
        
        # STEP A2: The Edge Refiner (RMBG-2.0)
        print(f"\n[*] INITIATING HYBRID PROTOCOL Phase 2: Edge Refinement (RMBG-2.0 Alpha Matting)")
        nobg_img = engine.remove_background(isolated_img, fg_threshold=args.fg_threshold)
    else:
        # Step A: Strip Background (Level 1 Smart Protocol via fg_threshold)
        print(f"\n[*] INITIATING LEVEL 1 PROTOCOL: RMBG-2.0 Alpha Matting")
        nobg_img = engine.remove_background(generated_img_path, fg_threshold=args.fg_threshold)
    
    # Step B: Quantize Colors (Perceptual K-Means)
    quantized_img = engine.quantize_colors_oklab(nobg_img, n_colors=args.colors)
    
    # Step C: Stacked SVG Vectorization & Sanitization
    svg_img = engine.run_vtracer(quantized_img)
    
    print("\n[✔] FULL PIPELINE COMPLETE!")
    print(f"[✔] Final Printable SVG: {svg_img}")

if __name__ == "__main__":
    main()
