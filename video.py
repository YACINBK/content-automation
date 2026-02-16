import argparse
import sys
import os
import requests
from datetime import datetime
from metaai_api import MetaAI

# Ensure UTF-8 output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    args = parser.parse_args()

    # YOUR COOKIES HERE (Update these!)
    cookies = {
        "datr": "YOUR_DATR",
        "abra_sess": "YOUR_ABRA_SESS",
        "ecto_1_sess": "YOUR_ECTO_1_SESS"
    }
    
    print(f"🎬 Initializing MetaAI...")
    ai = MetaAI(cookies=cookies)
    
    print(f"🎨 Generating video for: {args.prompt}")
    
    try:
        result = ai.generate_video_new(args.prompt)
        
        if result and result.get("success"):
            print("✅ Video Generated Successfully!")
            
            # Create outputs directory
            output_dir = "outputs"
            os.makedirs(output_dir, exist_ok=True)
            
            video_urls = result.get("video_urls", [])
            for i, url in enumerate(video_urls):
                print(f"📥 Downloading Video {i+1}...")
                try:
                    response = requests.get(url, stream=True)
                    if response.status_code == 200:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = os.path.join(output_dir, f"video_{timestamp}_{i+1}.mp4")
                        with open(filename, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        print(f"   Saved to: {filename}")
                    else:
                        print(f"   ❌ Failed to download (Status: {response.status_code})")
                except Exception as e:
                    print(f"   ❌ Download error: {e}")
                    
        else:
            print("❌ Generation failed.")
            print(f"Debug Info: {result}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
