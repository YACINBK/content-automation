import os
import sys
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Batch process a folder of images through the AI Vector Pipeline")
    parser.add_argument("--input_dir", type=str, required=True, help="Directory containing images to process")
    parser.add_argument("--mode", type=str, default="svg", choices=["svg", "dtf", "both"], help="Manufacturing target: 'svg' or 'dtf'")
    parser.add_argument("--colors", type=int, default=8, help="Number of spot colors for SVG mode")
    parser.add_argument("--fg_threshold", type=int, default=240, help="Level 1 BG removal threshold (0-255)")
    parser.add_argument("--erode_size", type=int, default=10, help="Alpha matting erode size. Higher = softer edges, lower = sharper edges.")
    parser.add_argument("--auto_smart_extract", action="store_true", help="Level 2 AUTO: Use VLM to blindly find the subject")
    parser.add_argument("--level2_extract", type=str, default=None, help="Level 2 MANUAL: GSAM2 Target (e.g. 'woman, flowers')")
    parser.add_argument("--punch_holes", type=str, default=None, help="Punch out trapped spaces via SAM 2")
    parser.add_argument("--invert_punch", action="store_true", help="Keep the DINO selection, delete everything else")
    parser.add_argument("--tight_mask", action="store_true", help="Forces SAM 2 to use tight pixel mask")
    parser.add_argument("--punch_color", type=str, default=None, help="Chroma-Key color to punch out (e.g. 'auto', 'red', '#FF0000')")
    
    args = parser.parse_args()

    if not os.path.exists(args.input_dir):
        print(f"[X] ERROR: Input directory not found: {args.input_dir}")
        sys.exit(1)

    valid_exts = ('.png', '.jpg', '.jpeg', '.webp')
    files = [f for f in os.listdir(args.input_dir) if f.lower().endswith(valid_exts)]
    
    if not files:
        print(f"[!] No valid images found in {args.input_dir} (looking for .png, .jpg, .webp)")
        sys.exit(0)

    print(f"\n" + "="*60)
    print(f"📦 BATCH INITIATED: Found {len(files)} images in '{args.input_dir}'")
    print(f"🏭 TARGET MODE: {args.mode.upper()}")
    print("="*60 + "\n")

    success_count = 0

    for idx, file in enumerate(files, 1):
        file_path = os.path.abspath(os.path.join(args.input_dir, file))
        print("\n" + "#"*60)
        print(f"▶️ BATCH [{idx}/{len(files)}]: Processing '{file}'")
        print("#"*60)

        # Construct the command for generate_from_scratch.py
        cmd = [
            sys.executable, "generate_from_scratch.py",
            "--input_image", file_path,
            "--mode", args.mode,
            "--colors", str(args.colors),
            "--fg_threshold", str(args.fg_threshold),
            "--erode_size", str(args.erode_size)
        ]

        if args.auto_smart_extract:
            cmd.append("--auto_smart_extract")
        
        if args.level2_extract:
            cmd.extend(["--level2_extract", args.level2_extract])
            
        if args.punch_holes:
            cmd.extend(["--punch_holes", args.punch_holes])
        if args.invert_punch:
            cmd.append("--invert_punch")
        if args.tight_mask:
            cmd.append("--tight_mask")
        if args.punch_color:
            cmd.extend(["--punch_color", args.punch_color])

        try:
            # subprocess.run waits for the command to finish before moving to the next
            subprocess.run(cmd, check=True)
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"\n[X] BATCH ERROR: Failed processing '{file}'. Moving to next image...")
            continue
        except KeyboardInterrupt:
            print("\n[!] BATCH ABORTED BY USER.")
            sys.exit(1)

    print("\n" + "="*60)
    print(f"[✔] BATCH PROCESSING COMPLETE! Successfully processed {success_count}/{len(files)} images.")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
