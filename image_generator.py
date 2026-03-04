"""
Meta AI Image Generation Interface
===================================

This script interfaces with Meta AI's image generation model.
1. Authentication: Uses session cookies (datr, abra_sess, etc.) to authenticate requests.
2. Generation: Sends text prompts to Meta's image generation endpoint.
3. Downloads: Automatically downloads the resulting generated images.
4. Batch Processing: Handles multiple prompts (one per verse) efficiently.

Usage:
    python image_generator.py --prompts "prompt1" "prompt2" "prompt3"

Outputs:
    Saves .jpg files to the 'outputs/images/' directory with verse numbering.
"""

import argparse
import sys
from metaai_api import MetaAI
import requests
from pathlib import Path
import os
import re
from datetime import datetime
from typing import List, Optional
import time

# Windows terminal trick: Ensure Emojis and special characters print correctly
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure the 'outputs/images/' directory exists for storing images
output_dir = Path("outputs") / "images"
output_dir.mkdir(parents=True, exist_ok=True)

# Authentication Cookies for Meta AI.
# These represent a logged-in session. If they expire, you must update them from your browser.
cookies = {
    "datr": "g9jnaMBtvXrPj-HsqRZiCN1B",
    "abra_sess": "For9stzaqJwDFjYYDmZHb1ZMOGxENFhvb0pnFubT5pgNAA==",
    "ecto_1_sess": "49ba7aaa-6b18-48ee-adb6-09e3691fe796.v1:c36Gy2PdnTecXq6hdTL8GElDOxUSj98co9HSYXZroVGQqqcbt0GNlX3olVNsH-MfWeSRNnkSlXgSM18e4MNMtMEdiVxyqOI78s4aLjtX32iX4ToBcfpkKjodijZsGLAso3YkkKptLe2JiBZr27U7VeIe-IjT4gv69TnOgyNrJM_9vLYxxIDU3kHQcaGwX1PeZZJc823gq6UNT5EVkK-akZAEHEP3dTmqWRwwEmKNR45hWUjsakeMtKxHGo4ZJfLFtb25lCmiuqWbh6YcOiSzrwl0hOyZRfj3WZ70iJiAhcA7jSg4ixcbJ3NMVZqVgP3GFEtJZIfZp6c1KBm2sZmhEO0RQqPAi_06cVNoBZs92N0MG9DXIl3LJCjLav7T4LJ2atmvhmfnUbbaDH_nohgTjFk3F1evNaLZUJ2bmVW5TvWjGTXf2l9ylFu3oqKbqTG-5RwUf1m8kA3c2NORkqX4zaBAfFA_oWQ6L8n4Rnlwx9VE_bzfU949ROKg0rEP1Qw:0WAD_oys7w7RPgvX:vXF_qi-zNS_DSBS1RHgxRA.cMlF8Xn-tnMWL-3mBLHInMxPfOS9TXVMGyzttQe-35k"
}


def sanitize_filename(text: str, max_length: int = 50) -> str:
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


class ImageGenerator:
    """Handles batch image generation using Meta AI."""
    
    def __init__(self, cookies_dict: Optional[dict] = None):
        """Initialize the Meta AI client with authentication cookies."""
        self.cookies = cookies_dict or cookies
        self.ai = MetaAI(cookies=self.cookies)
        self.output_dir = output_dir
    
    GENERATION_TIMEOUT = 90   # seconds for Meta AI primary attempt
    RETRY_TIMEOUT     = 60   # seconds for Meta AI simplified retry

    def _generate_with_pollinations(
        self, prompt: str, session_slug: str, timestamp: str, verse_idx: int
    ) -> Optional[str]:
        """
        Fallback image generation via Pollinations.ai.
        - Free, no API key required
        - No content review queue
        - Returns a 1080x1920 image
        """
        import urllib.parse
        clean_prompt = prompt[:500].replace('\n', ' ')
        encoded = urllib.parse.quote(clean_prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=1080&height=1920&nologo=true&seed={verse_idx}"
        )
        try:
            print(f"   🌐 Pollinations.ai fallback for verse {verse_idx}...")
            response = requests.get(url, timeout=120, stream=True)
            if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
                filename = self.output_dir / f"{session_slug}_{timestamp}_verse_{verse_idx}.jpg"
                size_bytes = 0
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(8192):
                        if chunk:
                            f.write(chunk)
                            size_bytes += len(chunk)
                size_kb = size_bytes / 1024
                print(f"   ✅ Pollinations saved: {filename.name} ({size_kb:.1f} KB)")
                return str(filename)
            else:
                print(f"   ❌ Pollinations failed: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"   ❌ Pollinations error: {e}")
            return None

    def _try_meta_ai(self, prompt: str, timeout: int):
        """Run a single Meta AI generation call inside a thread with timeout."""
        import concurrent.futures
        def _gen():
            return self.ai.generate_image_new(prompt=prompt)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_gen)
            return future.result(timeout=timeout)  # raises TimeoutError on timeout

    def generate_images(
        self,
        prompts: List[str],
        session_name: str = None,
        base_prompts: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Generate images for multiple prompts (one per verse).

        3-layer fallback strategy (fully automatic, no supervision required):
          1. Meta AI with the original styled prompt (GENERATION_TIMEOUT)
          2. Meta AI with the simplified base prompt if layer 1 times out (RETRY_TIMEOUT)
          3. Pollinations.ai if both Meta AI attempts fail (no auth, no content review)

        Args:
            prompts:       Styled prompts (one per verse).
            session_name:  Session label for filenames.
            base_prompts:  Optional unstyled prompts for the simplified retry layer.

        Returns:
            List of file paths (never None — guaranteed by Pollinations.ai fallback).
        """
        
        if not prompts:
            print("❌ No prompts provided")
            return []

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_slug = sanitize_filename(session_name or "poetry")

        print("=" * 60)
        print("🎨 META AI IMAGE ENGINE: BATCH GENERATION")
        print("=" * 60)
        print(f"📊 Total verses to generate: {len(prompts)}")
        print(f"🕒 Estimated time: {len(prompts) * 30} seconds\n")

        generated_paths: List[Optional[str]] = []

        try:
            for i, prompt in enumerate(prompts, 1):
                print(f"\n{'='*60}")
                print(f"🖼️  VERSE {i}/{len(prompts)}")
                print(f"{'='*60}")
                print(f"Prompt: {prompt[:80]}...")
                print(f"⏳ Generating (est. 30s, timeout {self.GENERATION_TIMEOUT}s)...\n")

                path = None
                import concurrent.futures as _cf

                # ── Layer 1: Meta AI full styled prompt ────────────────────
                try:
                    result = self._try_meta_ai(prompt, self.GENERATION_TIMEOUT)
                except _cf.TimeoutError:
                    print(f"⏱️  Verse {i} timed out on Meta AI — trying simplified prompt...")
                    result = None
                except Exception as e:
                    print(f"⚠️  Meta AI error verse {i}: {e}")
                    result = None

                if result and result.get("success") and result.get("image_urls"):
                    path = self._download_image(result["image_urls"][0], session_slug, timestamp, i)

                # ── Layer 2: Meta AI simplified base prompt ────────────────
                if path is None:
                    simple = (
                        base_prompts[i - 1]
                        if base_prompts and i - 1 < len(base_prompts)
                        else prompt.split(",")[0]
                    )
                    print(f"   🔄 Retrying Meta AI with simplified prompt...")
                    try:
                        result2 = self._try_meta_ai(simple, self.RETRY_TIMEOUT)
                    except _cf.TimeoutError:
                        print("   ⏱️  Simplified retry also timed out.")
                        result2 = None
                    except Exception as e:
                        print(f"   ⚠️  Simplified retry error: {e}")
                        result2 = None

                    if result2 and result2.get("success") and result2.get("image_urls"):
                        path = self._download_image(result2["image_urls"][0], session_slug, timestamp, i)

                # ── Layer 3: Pollinations.ai — guaranteed fallback ─────────
                if path is None:
                    fallback_prompt = (
                        base_prompts[i - 1]
                        if base_prompts and i - 1 < len(base_prompts)
                        else prompt.split(",")[0]
                    )
                    path = self._generate_with_pollinations(
                        fallback_prompt, session_slug, timestamp, i
                    )

                generated_paths.append(path)

                if i < len(prompts):
                    time.sleep(2)

        except KeyboardInterrupt:
            print(f"\n⚠️  Batch interrupted. Keeping {len(generated_paths)}/{len(prompts)} results.")
            generated_paths.extend([None] * (len(prompts) - len(generated_paths)))

        print(f"\n{'='*60}")
        print("🎉 BATCH GENERATION COMPLETE")
        print(f"{'='*60}")
        successful = sum(1 for p in generated_paths if p is not None)
        print(f"✅ Successful: {successful}/{len(prompts)}")
        print(f"📁 Saved to: {self.output_dir.absolute()}\n")

        return generated_paths

    def _download_image(
        self, url: str, session_slug: str, timestamp: str, verse_idx: int
    ) -> Optional[str]:
        """
        Download an image from url and save it.
        Includes retry logic with exponential backoff for 429 (Rate Limit) errors.
        """
        max_retries = 3
        backoff_base = 5

        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    print("✅ Generation successful!")
                    print("📥 Downloading image...")
                else:
                    wait_time = backoff_base * (2 ** (attempt - 1))
                    print(f"   🔄 Retry download {attempt}/{max_retries-1} in {wait_time}s...")
                    time.sleep(wait_time)

                response = requests.get(url, timeout=60, stream=True)
                
                if response.status_code == 429:
                    print(f"   ⚠️  Download rate limited (429).")
                    continue
                
                response.raise_for_status()
                filename = self.output_dir / f"{session_slug}_{timestamp}_verse_{verse_idx}.jpg"
                size_bytes = 0
                with open(filename, "wb") as f:
                    for chunk in response.iter_content(8192):
                        if chunk:
                            f.write(chunk)
                            size_bytes += len(chunk)
                print(f"💾 Saved: {filename.name} ({size_bytes/1024:.1f} KB)")
                return str(filename)
            except Exception as e:
                print(f"❌ Download failed: {e}")
                if attempt == max_retries - 1:
                    return None
        return None


    
    def retry_failed(self, prompts: List[str], previous_results: List[Optional[str]], 
                     session_name: str = None, max_retries: int = 2) -> List[str]:
        """
        Retry generation for failed images.
        
        Args:
            prompts (List[str]): Original list of prompts
            previous_results (List[Optional[str]]): Results from previous attempt
            session_name (str): Session name for file naming
            max_retries (int): Maximum retry attempts per failed image
            
        Returns:
            List[str]: Updated list of image paths
        """
        results = previous_results.copy()
        failed_indices = [i for i, path in enumerate(results) if path is None]
        
        if not failed_indices:
            print("✅ No failed images to retry")
            return results
        
        print(f"\n🔄 Retrying {len(failed_indices)} failed images...")
        
        for idx in failed_indices:
            for attempt in range(max_retries):
                print(f"\n🔄 Retry {attempt + 1}/{max_retries} for verse {idx + 1}")
                
                try:
                    result = self.ai.generate_image_new(prompt=prompts[idx])
                    
                    if result.get("success") and result.get("image_urls"):
                        image_url = result["image_urls"][0]
                        response = requests.get(image_url, timeout=60, stream=True)
                        response.raise_for_status()
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        session_slug = sanitize_filename(session_name or "poetry")
                        filename = self.output_dir / f"{session_slug}_{timestamp}_verse_{idx + 1}_retry.jpg"
                        
                        with open(filename, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        
                        results[idx] = str(filename)
                        print(f"✅ Retry successful: {filename.name}")
                        break
                    
                except Exception as e:
                    print(f"❌ Retry attempt {attempt + 1} failed: {e}")
                
                time.sleep(3)
        
        return results


def main():
    """
    Main script logic for batch image generation.
    """
    parser = argparse.ArgumentParser(description="Meta AI Image Generator for Poetry")
    parser.add_argument("--prompts", nargs='+', required=True, 
                       help="List of image prompts (one per verse)")
    parser.add_argument("--session", default="poetry",
                       help="Session name for file organization")
    parser.add_argument("--retry", action="store_true",
                       help="Enable automatic retry for failed generations")
    args = parser.parse_args()
    
    generator = ImageGenerator()
    
    # Generate images
    results = generator.generate_images(args.prompts, args.session)
    
    # Retry failed generations if enabled
    if args.retry:
        results = generator.retry_failed(args.prompts, results, args.session)
    
    # Print final summary
    successful = [p for p in results if p is not None]
    print(f"\n📊 FINAL RESULTS:")
    print(f"   Total: {len(results)}")
    print(f"   Successful: {len(successful)}")
    print(f"   Failed: {len(results) - len(successful)}")
    
    if successful:
        print(f"\n✅ Generated images:")
        for path in successful:
            print(f"   - {path}")


if __name__ == "__main__":
    main()
