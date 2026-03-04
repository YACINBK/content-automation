import re
import subprocess
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_command(command):
    logging.info(f"🚀 Executing: {' '.join(command)}")
    process = subprocess.Popen(
        command, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        text=True, 
        encoding='utf-8', 
        errors='replace'
    )
    
    output = ""
    for line in process.stdout:
        print(line, end="")
        output += line
    
    process.wait()
    return process.returncode, output

def parse_poems(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by the numbering pattern "n. TITLE by AUTHOR"
    # We look for a line starting with a number followed by a dot
    parts = re.split(r'\n\s*\d+\.\s+', '\n' + content)
    
    poems = []
    for p in parts:
        lines = p.strip().split('\n')
        if len(lines) < 2:
            continue
            
        # The first line of the part (after splitting) is the Title/Author line
        # The rest are verses
        title_author = lines[0].strip()
        verses = "\n".join(lines[1:]).strip()
        
        if verses:
            poems.append({
                "title": title_author,
                "text": verses
            })
            
    return poems

def main():
    import argparse
    import time
    parser = argparse.ArgumentParser(description="Bulk process poems from poem.txt")
    parser.add_argument("--dry-run", action="store_true", help="Print poems and stop")
    parser.add_argument("--start-at", type=int, default=1, help="Poem index to start at (1-based)")
    parser.add_argument("--delay", type=int, default=30, help="Seconds to wait between poems")
    parser.add_argument("--drive-folder", default=None, help="Target Google Drive folder")
    args = parser.parse_args()

    poem_file = "poem.txt"
    if not os.path.exists(poem_file):
        logging.error(f"❌ {poem_file} not found!")
        return

    poems = parse_poems(poem_file)
    logging.info(f"📋 Found {len(poems)} poems in {poem_file}")

    if args.dry_run:
        for i, poem in enumerate(poems, 1):
            print(f"{i}. {poem['title']}")
        return

    for i, poem in enumerate(poems, 1):
        if i < args.start_at:
            continue
            
        logging.info(f"\n{'#'*80}")
        print(f"🎬 PROCESSING POEM {i}/{len(poems)}: {poem['title']}")
        logging.info(f"{'#'*80}\n")
        
        cmd = [
            "python", "generate_poetry_video.py",
            "--poem-text", poem['text'],
            "--romance",
            "--include-people",
            "--voice", "morino",
            "--delete-local",
            "--music", "Enya - Caribbean Blue __ Best Part.mp3"
        ]
        
        if args.drive_folder:
            cmd.extend(["--drive-folder", args.drive_folder])
        
        ret_code, output = run_command(cmd)
        
        if ret_code == 0:
            logging.info(f"✅ Successfully processed: {poem['title']}")
        else:
            logging.error(f"❌ Failed to process: {poem['title']}")
            
        if i < len(poems):
            logging.info(f"⏳ Waiting {args.delay}s before next poem...")
            time.sleep(args.delay)
            
    logging.info("\n✨ All poems processed!")

if __name__ == "__main__":
    main()
