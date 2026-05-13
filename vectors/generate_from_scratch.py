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
    parser.add_argument("--prompt", type=str, required=False, help="Description of the hoodie artwork (Required if not providing --input_image)")
    parser.add_argument("--input_image", type=str, default=None, help="Bypass generation and process an existing image file")
    parser.add_argument("--raw_prompt", action="store_true", help="Bypass LLM enhancement and use the exact prompt provided")
    parser.add_argument("--art_style", type=str, default="vector", choices=["vector", "oil"], help="Aesthetic style of the generated graphic")
    parser.add_argument("--colors", type=int, default=8, help="Number of spot colors for screen printing (Max 8 recommended)")
    parser.add_argument("--cognitive_mode", action="store_true", help="Enable the Semantic/Cognitive Architecture (SAM 2 + Florence 2). Bypasses all bg removal and basic color quantization.")
    parser.add_argument("--fg_threshold", type=int, default=240, help="Level 1 BG removal threshold (0-255). Lower to keep more subject edges.")
    parser.add_argument("--erode_size", type=int, default=10, help="Alpha matting erode size. Higher = softer edges, lower = sharper edges.")
    parser.add_argument("--auto_smart_extract", action="store_true", help="Level 2 AUTO: Ollama autonomously pilots GSAM2 to extract the main subject.")
    parser.add_argument("--level2_extract", type=str, default=None, help="Level 2 MANUAL: GSAM2 Target. Provide a text string (e.g. 'cat, skateboard') to exclusively extract.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--llm_provider", type=str, default="openrouter", choices=["deepseek", "ollama", "openrouter"], help="LLM Provider to use")
    parser.add_argument("--llm_model", type=str, default="google/gemini-2.0-flash-001", help="Model name for the chosen provider")
    parser.add_argument("--mode", type=str, default="svg", choices=["svg", "dtf", "both"], help="Manufacturing target: 'svg' for Screen Printing, 'dtf' for Direct-to-Film, 'both' for experimentation.")
    parser.add_argument("--punch_holes", type=str, default=None, help="Double-Layered Extract: Provide a prompt to find trapped negative space")
    parser.add_argument("--invert_punch", action="store_true", help="If DINO selects the subject instead of the hole, use this to KEEP the selection and delete the hole.")
    parser.add_argument("--tight_mask", action="store_true", help="Forces SAM 2 to use the tightest possible sub-part pixel mask (fixes blobs over holes).")
    parser.add_argument("--punch_color", type=str, default=None, help="Final Deterministic Chroma-Key math to delete exact trapped colors (e.g. 'auto', 'white', 'black', 'red', or '#FF0000').")
    args = parser.parse_args()

    if not args.prompt and not args.input_image:
        print("[X] ERROR: You must provide either --prompt (to generate) or --input_image (to process).")
        sys.exit(1)

    print("\n" + "="*50)
    print("🚀 INITIALIZING MASTER PIPELINE: USE CASE A")
    print("="*50)

    llm_dir = LLMDirector(provider=args.llm_provider, model_name=args.llm_model)
    
    if args.input_image:
        print("\n" + "="*50)
        print("📥 INGESTION PHASE: BYPASSING GENERATION")
        print(f"[*] Loading existing image: {args.input_image}")
        print("="*50)
        
        if not os.path.exists(args.input_image):
            print(f"[X] ERROR: Input image not found: {args.input_image}")
            sys.exit(1)
            
        generated_img_path = args.input_image
        
    else:
        # 1. LLM Prompt Expansion (The Missing Brain)
        print("\n" + "="*50)
        print("🧠 LLM DIRECTOR: ENHANCING PROMPT")
        print("="*50)
        
        if args.raw_prompt:
            print("[!] Bypassing LLM Director. Using exact raw prompt.")
            final_prompt = args.prompt
        elif not llm_dir.check_connection():
            print(f"[!] Warning: {args.llm_provider.upper()} service is not available.")
            print("[!] Defaulting to raw prompt bypass.")
            final_prompt = args.prompt
        else:
            final_prompt = llm_dir.enhance_prompt_for_flux(args.prompt, art_style=args.art_style)
            
            # Soft Relay: Giving VRAM time to flush back to 0% before ComfyUI
            if args.llm_provider == "ollama":
                print(f"\n[!] SOFT RELAY: Forcing Ollama to drop model from VRAM...")
                print(f"[*] Waiting 5 seconds for CUDA cache to fully flush before waking ComfyUI...")
                time.sleep(5)
                print(f"[OK] VRAM flush assumed complete. Handing baton to ComfyUI.\n")
            else:
                print(f"\n[OK] {args.llm_provider.upper()} API requires 0GB local VRAM. Bypassing Soft Relay. Handing baton to ComfyUI instantly.\n")

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
    print("🎨 STARTING POST-PROCESSING ENGINE")
    print(f"[*] SPOT COLORS: {args.colors}")
    print("="*50)

    # Pre-calculate SAM2 Target
    sam2_target = args.level2_extract
    llm_dir = LLMDirector(provider=args.llm_provider, model_name=args.llm_model)

    if args.cognitive_mode:
        print("\n" + "="*50)
        print("🧠 INITIATING COGNITIVE ARCHITECTURE (Phase 1-4)")
        print("="*50)
        
        from semantic_vectorizer import SemanticVectorizer
        semantic_engine = SemanticVectorizer()
        final_svg_path = semantic_engine.execute_cognitive_core(generated_img_path)
        
        if final_svg_path:
            print("\n" + "="*50)
            print("🏭 COGNITIVE ROUTING LAYER: TARGET METHOD => [SVG]")
            print(f"[✔] Screen Printing SVG: {final_svg_path}")
            print("="*50)
        else:
            print("[X] ERROR: Cognitive pipeline failed to produce an SVG.")
        
        print("\n[✔] COGNITIVE PIPELINE COMPLETE!")
        return

    if args.auto_smart_extract and not args.prompt:
        print("[!] Note: --auto_smart_extract normally uses the prompt for context. Since an existing image was provided, the VLM will analyze it blindly.")

    # 3. Process and Vectorize
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
        
        # STEP A2: The Edge Refiner (RMBG-2.0 Alpha Matting) -> Now using backgroundremover u2net_human_seg
        print(f"\n[*] INITIATING HYBRID PROTOCOL Phase 2: Edge Refinement (Alpha Matting)")
        nobg_img = engine.remove_background(isolated_img, fg_threshold=args.fg_threshold, erode_size=args.erode_size)
    else:
        # Step A: Strip Background (Level 1 Smart Protocol via fg_threshold)
        print(f"\n[*] INITIATING LEVEL 1 PROTOCOL: Alpha Matting (backgroundremover)")
        nobg_img = engine.remove_background(generated_img_path, fg_threshold=args.fg_threshold, erode_size=args.erode_size)
    
    # NEW STEP A3: Double-Layered Hole Punching (Negative Space)
    if args.punch_holes:
        print(f"\n[*] INITIATING DOUBLE-LAYERED NEGATIVE SPACE PUNCH-OUT")
        extractor = SmartExtractor()
        
        # 1. Get raw hole boolean mask from the original image using SAM 2
        hole_mask_bool = extractor.extract_holes(generated_img_path, text_prompt=args.punch_holes, tight_mask=args.tight_mask)
        
        if hole_mask_bool is not None:
            # 2. Execute Boolean Image Math in VectorPrepEngine
            nobg_img = engine.punch_holes_from_array(nobg_img, hole_mask_bool, invert_logic=args.invert_punch)
        else:
            print("[!] No holes found to punch out.")

    # NEW STEP A4: Deterministic Chroma-Key Punch
    if args.punch_color:
        nobg_img = engine.chroma_key_punch(nobg_img, color=args.punch_color, tolerance=30)

    # 3. Apply Routing Layer (Forking to Target Manufacturing Method)
    print("\n" + "="*50)
    print(f"🏭 ROUTING LAYER: TARGET METHOD => [{args.mode.upper()}]")
    print("="*50)
    
    if args.mode in ["dtf", "both"]:
        # PATH A: Direct-to-Film (Raster Path)
        print(f"\n[*] INITIATING PATH A: Direct-to-Film (DTF) Target")
        dtf_img = engine.prepare_for_dtf(nobg_img)
        print(f"[✔] DTF Printable File: {dtf_img}")
        
    if args.mode in ["svg", "both"]:
        # PATH B: Screen Printing (Vector Path)
        print(f"\n[*] INITIATING PATH B: Screen Printing (Vector) Target")
        print(f"[*] TARGET SPOT COLORS: {args.colors}")
        
        # Step B: Quantize Colors (Perceptual K-Means)
        quantized_img = engine.quantize_colors_oklab(nobg_img, n_colors=args.colors)
        
        # Step C: Stacked SVG Vectorization & Sanitization
        svg_img = engine.run_vtracer(quantized_img)
        print(f"[✔] Screen Printing SVG: {svg_img}")
    
    print("\n[✔] FULL PIPELINE COMPLETE!")

if __name__ == "__main__":
    main()
