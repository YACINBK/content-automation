import re
import subprocess
import os
import json
from pathlib import Path

def run_command(command):
    print(f"Executing: {' '.join(command)}")
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    
    output = ""
    for line in process.stdout:
        print(line, end="")
        output += line
    
    process.wait()
    return process.returncode, output

def main():
    with open("generate-bulk.txt", "r", encoding="utf-8") as f:
        content = f.read()

    # Split by the separator stars
    raw_poems = re.split(r'\*+', content)
    
    poems = []
    for rp in raw_poems:
        # Clean up headers like "poem number 1 :"
        clean_p = re.sub(r'poem number \d+\s*:\s*', '', rp).strip()
        if clean_p and len(clean_p) > 20: # Ensure it's not just junk
            poems.append(clean_p)

    print(f"📋 Found {len(poems)} poems to process.")

    for i, poem in enumerate(poems, 1):
        print(f"\n{'#'*80}")
        print(f"🚀 PROCESSING POEM {i}/{len(poems)}")
        print(f"{'#'*80}\n")
        
        # 1. Try full pipeline first
        cmd = [
            "python", "generate_poetry_video.py",
            "--poem-text", poem,
            "--include-people",
            "--retry-images"
        ]
        
        ret_code, output = run_command(cmd)
        
        # 2. Check if it failed specifically because of voice credits
        if ret_code != 0 and "credits" in output.lower() and "required" in output.lower():
            print(f"\n⚠️  Narration failed due to credit limits. Attempting SILENT assembly for Poem {i}...")
            
            # Find the metadata file generated in this session
            # The session name is usually [slug]_[timestamp]
            # Let's find the latest metadata file in the metadata directory
            metadata_dir = Path("metadata")
            files = list(metadata_dir.glob("*.json"))
            if files:
                latest_metadata = max(files, key=os.path.getmtime)
                print(f"🔎 Using latest metadata: {latest_metadata}")
                
                # Run silent assembly
                silent_cmd = [
                    "python", "assemble_silent.py",
                    "--metadata", str(latest_metadata)
                ]
                run_command(silent_cmd)
        
        elif ret_code != 0:
            print(f"❌ Poem {i} failed for reasons other than credits.")

    print("\n✅ Bulk processing finished.")

if __name__ == "__main__":
    main()
