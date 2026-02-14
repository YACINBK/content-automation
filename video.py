"""
Meta AI Video Generation Interface
==================================

This script interfaces with Meta AI's video generation model. 
1. Authentication: Uses session cookies (datr, abra_sess, etc.) to authenticate requests.
2. Generation: Sends a text prompt to Meta's 'generate_video_new' endpoint.
3. Downloads: Automatically downloads the resulting 4 generated video files.
4. Auto-Play: Opens the first generated video automatically for immediate review.

Usage:
    python video.py --prompt "A cozy 2D lofi illustration..."

Outputs:
    Saves .mp4 files to the 'outputs/' directory with a timestamped slug.
"""

import argparse
import sys
from metaai_api import MetaAI
import requests
from pathlib import Path
import os
import re
from datetime import datetime

# Windows terminal trick: Ensure Emojis and special characters print correctly
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure the 'outputs/' directory exists for storing raw video clips
output_dir = Path("outputs")
output_dir.mkdir(exist_ok=True)

# Authentication Cookies for Meta AI.
# These represent a logged-in session. If they expire, you must update them from your browser.
cookies = {
    "datr": "AP2NaQK7olTjm_TvBSXPqHhB",
    "abra_sess": "FqyV5szPn9YDFioYDjg3Vm5VN0J3c2pyb1FBFvb%2F75gNAA%3D%3D==",
    "ecto_1_sess": "36ba8935-2b8b-4f84-a08a-a6bc715dc5b4.v1%3AxGMSNaL_f8zDMDnDjb4ZnfXo-slIfe-XvQ2zAAhLqmDSTPUTdSzypQK3k5OX_IvXF48O1Mwd8HWbfPNY1J5bemG5oFbQuueRRUNZi_X9Hhyj5lNr5Z3r5kywzUhkBapJU_cQXjd8NloSMMhZft_0xmaVmYjuS1qs1JTAhARB5jPTgOopwoEtKyLJdRsKV-NA0FGSWsP-awwSztQ95e1c6t1Yuw7IKZ90L5YuloL3oJeRl_Qt615KP4nYGG4UakFERlTeUKlcDnQDsV9HP9nq8TGWDrXhU8uiSwXASDCPgLdZcj8MSenhHPmOSed0i8xPqfq1Z5g96pxzfqEfgivIXAGT4j6YxQ2KA4CNrNKv7rJ0M2H_qb7BtBnPUiUkvMkItgaidmixEEljTMkrADsDK9QKVpw3fvaXYeQGvgjhfpCUogugI-hy4jiiRAOYDNCdc84254id8UxUVWKqfpO480qoduVUkfTrwovMv8vUp4w06JfRNEoqD1HiDrm3%3AhNRxYHbVcmsG3aF_%3AnsWRU_UH8mQkg2J0nsDmog.QHdEll4bupl8SrOkGzCdkk3H0IGAeCFm3cMu3IcZ7Tg"
}

def sanitize_filename(text, max_length=50):
    """
    Converts a verbose prompt into a safe, filesystem-friendly filename slug.
    
    Args:
        text (str): The prompt text to be slugified.
        max_length (int): Maximum character length for the resulting slug.
        
    Returns:
        str: A lowercased, underscored string safe for file mapping.
    """
    # Use the start of the prompt for the filename
    text = text[:max_length]
    
    # Remove symbols/emojis, keep only alphanumeric and spaces
    text = re.sub(r'[^\w\s-]', '', text)
    
    # Replace whitespace with underscores
    text = re.sub(r'\s+', '_', text)
    
    # Clean up redundant underscores
    text = re.sub(r'_+', '_', text)
    
    return text.strip('_').lower()

def main():
    """
    Main script logic for triggering video generation via MetaAI API.
    """
    parser = argparse.ArgumentParser(description="Meta AI Video Generator Utility")
    parser.add_argument("--prompt", required=True, help="Visual description (The prompt used by Meta AI)")
    args = parser.parse_args()

    video_prompt = args.prompt

    print("=" * 60)
    print("🎬 META AI VIDEO ENGINE: INITIALIZING GENERATION")
    print("=" * 60)

    # Initialize the MetaAI client with our authentication cookies
    ai = MetaAI(cookies=cookies)

    print(f"\n🎨 Submitting Prompt to Model...")
    print(f"   Prompt: {video_prompt[:80]}...")
    print(f"   ⏳ Estimated wait time: 45-60 Seconds\n")

    # API Trigger
    result = ai.generate_video_new(prompt=video_prompt)

    print(f"\n📊 API Response Received:")
    print(f"   Status: {'✅ SUCCESS' if result.get('success') else '❌ FAILED'}")
    print(f"   Videos Produced: {len(result.get('video_urls', []))}")

    if result["success"] and result.get("video_urls"):
        # Create unique naming pattern: [prompt_slug]_[timestamp]_[number].mp4
        prompt_slug = sanitize_filename(video_prompt)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for i, url in enumerate(result['video_urls'], 1):
            try:
                print(f"📥 Downloading Variant {i}/{len(result['video_urls'])}...")
                
                # Fetch the video binary data
                response = requests.get(url, timeout=60, stream=True)
                response.raise_for_status()
                
                filename = output_dir / f"{prompt_slug}_{timestamp}_{i}.mp4"
                
                # Save to disk
                with open(filename, 'wb') as f:
                    size_bytes = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            size_bytes += len(chunk)
                
                size_mb = size_bytes / (1024 * 1024)
                print(f"   ✅ Saved to Disk: {filename.name} ({size_mb:.2f} MB)")
                
                # Automatically open the first video for review
                if i == 1:
                    print(f"   🎬 Triggering OS view for the primary variant...")
                    if os.name == 'nt':  # Windows
                        os.startfile(filename)
                    elif os.name == 'posix':  # macOS/Linux
                        if os.uname().sysname == 'Darwin':  # macOS
                            os.system(f'open "{filename}"')
                        else:  # Linux
                            os.system(f'xdg-open "{filename}"')
                
                print()
                
            except Exception as e:
                print(f"   ❌ Download Failed: {e}\n")
        
        print(f"🎉 All generated clips stored in: {output_dir.absolute()}")
    else:
        print(f"\n❌ VIDEO GENERATION FAILED")
        print(f"   Reason: {result.get('error', 'API internal error')}")
        print(f"\n   Debug Data: {result}")

if __name__ == "__main__":
    main()
