"""
Meta AI Video Generation Test Script
======================================

Tests Meta AI video generation with the new nostalgic_oil style prompts.
Generates raw videos without audio/slideshow assembly.

Usage:
    python test_meta_video.py --prompt "your scene description" --style nostalgic_oil
"""

import argparse
import os
import sys

# Add metaai-api to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'metaai-api'))

from metaai_api import MetaAI

# Style presets from generate_reel.py
STYLES = {
    "minimalist_dark": {
        "visual_prompt": "Mid-shot, wide angle, distant subject, grainy film texture, heavy silhouette, minimalist character, dark atmosphere, golden hour lighting, muted tones, 8k resolution, cinematic composition"
    },
    "oil_painting": {
        "visual_prompt": "Mid-shot, wide angle, distant subject, living oil painting, heavy brushstrokes, chiaroscuro lighting, classical composition, canvas texture, museum quality, subtle motion"
    },
    "nostalgic_oil": {
        "visual_prompt": "early 20th century oil painting, mid-shot, wide angle, soft warm lighting, textured oil paint effect, muted earth tones, classical European illustration, nostalgic mood, detailed brush strokes, museum painting style"
    }
}

def test_video_generation(prompt, style="nostalgic_oil"):
    """
    Test Meta AI video generation with style-enhanced prompts.
    
    Args:
        prompt: Base scene description
        style: Style preset to apply
    """
    print(f"🎨 Testing Meta AI Video Generation")
    print(f"   Style: {style}")
    print(f"   Prompt: {prompt}")
    print()
    
    # Get style enhancement
    style_enhancement = STYLES.get(style, STYLES["nostalgic_oil"])["visual_prompt"]
    full_prompt = f"{prompt}, {style_enhancement}"
    
    print(f"📝 Full Prompt:")
    print(f"   {full_prompt}")
    print()
    
    # Initialize Meta AI with cookies
    cookies = {
        "datr": "AP2NaQK7olTjm_TvBSXPqHhB",
        "abra_sess": "FqyV5szPn9YDFioYDjg3Vm5VN0J3c2pyb1FBFvb%2F75gNAA%3D%3D==",
        "ecto_1_sess": "36ba8935-2b8b-4f84-a08a-a6bc715dc5b4.v1%3AxGMSNaL_f8zDMDnDjb4ZnfXo-slIfe-XvQ2zAAhLqmDSTPUTdSzypQK3k5OX_IvXF48O1Mwd8HWbfPNY1J5bemG5oFbQuueRRUNZi_X9Hhyj5lNr5Z3r5kywzUhkBapJU_cQXjd8NloSMMhZft_0xmaVmYjuS1qs1JTAhARB5jPTgOopwoEtKyLJdRsKV-NA0FGSWsP-awwSztQ95e1c6t1Yuw7IKZ90L5YuloL3oJeRl_Qt615KP4nYGG4UakFERlTeUKlcDnQDsV9HP9nq8TGWDrXhU8uiSwXASDCPgLdZcj8MSenhHPmOSed0i8xPqfq1Z5g96pxzfqEfgivIXAGT4j6YxQ2KA4CNrNKv7rJ0M2H_qb7BtBnPUiUkvMkItgaidmixEEljTMkrADsDK9QKVpw3fvaXYeQGvgjhfpCUogugI-hy4jiiRAOYDNCdc84254id8UxUVWKqfpO480qoduVUkfTrwovMv8vUp4w06JfRNEoqD1HiDrm3%3AhNRxYHbVcmsG3aF_%3AnsWRU_UH8mQkg2J0nsDmog.QHdEll4bupl8SrOkGzCdkk3H0IGAeCFm3cMu3IcZ7Tg"
    }
    
    print("🔌 Connecting to Meta AI...")
    ai = MetaAI(cookies=cookies)
    
    print("🎬 Generating video...")
    try:
        # Generate video using the correct method
        response = ai.generate_video_new(full_prompt)
        
        if response.get("success"):
            print("✅ Video generation successful!")
            print()
            
            # Display video URLs
            if "video_urls" in response and response["video_urls"]:
                print(f"🎥 Generated {len(response['video_urls'])} video variant(s):")
                for i, url in enumerate(response["video_urls"], 1):
                    print(f"   [{i}] {url}")
                print()
                
                # Download first variant
                import requests
                print("⬇️ Downloading first variant...")
                video_url = response["video_urls"][0]
                video_data = requests.get(video_url).content
                
                output_file = f"test_video_{style}.mp4"
                with open(output_file, "wb") as f:
                    f.write(video_data)
                
                print(f"💾 Saved to: {output_file}")
                print(f"   Size: {len(video_data) / 1024 / 1024:.2f} MB")
            else:
                print("⚠️ No video URLs in response")
                print(f"Response: {response}")
        else:
            print("❌ Video generation failed")
            print(f"Error: {response.get('error', 'Unknown error')}")
            print(f"Response: {response}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="Test Meta AI video generation with style presets")
    parser.add_argument("--prompt", required=True, help="Base scene description")
    parser.add_argument("--style", default="nostalgic_oil", choices=STYLES.keys(), 
                       help="Visual style preset")
    
    args = parser.parse_args()
    
    test_video_generation(args.prompt, args.style)

if __name__ == "__main__":
    main()
