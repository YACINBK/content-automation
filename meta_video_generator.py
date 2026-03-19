import os
import sys
import json
import asyncio
import argparse
import base64
from scrapling.fetchers import AsyncStealthySession
from dotenv import load_dotenv

# Load Environment Variables from .env
load_dotenv(override=True)

async def generate_meta_video(prompt: str, output_path: str, headless: bool = False):
    """
    Automates the generation of an AI video on Meta AI (meta.ai) using Scrapling.
    
    Args:
        prompt (str): The creative prompt for the AI video.
        output_path (str): Local path to save the generated .mp4 file.
        headless (bool): Whether to run the browser in headless mode. 
                         Non-headless (False) is recommended for session stabilization.
    """
    
    # Configuration
    WINDOWS_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    
    # 1. Parse Cookies from Environment
    # Format: A JSON array of cookie objects (name, value, domain, path)
    env_cookies = os.getenv("META_COOKIES", "").strip()
    cookie_list = []
    if env_cookies:
        try:
            cookie_list = json.loads(env_cookies)
        except Exception as e:
            print(f"⚠️ Error: Failed to parse META_COOKIES from .env. Ensure it's a valid JSON array. Error: {e}")
            return False
    else:
        print("⚠️ Warning: No META_COOKIES found in .env. Attempting generation as a guest (may fail or require manual login).")

    print(f"🚀 Initializing Meta AI Video Automation...")
    print(f"🎬 Prompt: \"{prompt[:60]}...\"")
    
    async with AsyncStealthySession(headless=headless, user_agent=WINDOWS_UA) as session:
        # 2. Inject Cookies before navigation
        if cookie_list:
            print("🔑 Injecting authenticated session cookies...")
            await session.context.add_cookies(cookie_list)
            
        async def automation_logic(page):
            # A) Stabilize and handle potential popups
            print("🌐 Navigating to Meta AI...")
            await page.wait_for_timeout(3000)
            
            # Simple Age Verification Bypass (if cookies are fresh, this is usually skipped)
            try:
                if await page.get_by_text("Welcome to Meta AI").count() > 0:
                    print("⚠️ Bypassing age verification popup...")
                    dropdown = page.get_by_text("Year", exact=True)
                    if await dropdown.count() > 0:
                        await dropdown.first.click()
                        for _ in range(25): # Scroll to 1990s
                            await page.keyboard.press('ArrowDown')
                            await page.wait_for_timeout(30)
                        await page.keyboard.press('Enter')
                    
                    continue_btn = page.get_by_role("button", name="Continue")
                    if await continue_btn.count() > 0:
                        await continue_btn.first.click()
                    await page.wait_for_timeout(2000)
            except:
                pass

            # B) Send Generation Prompt
            # We use the "Imagine a video of..." command to trigger the T2V model
            gen_command = f"Imagine a video of {prompt}"
            print(f"✍️ Sending command: {gen_command[:70]}...")
            
            # Find the primary chat textbox
            chat_box = page.locator("role=textbox").first
            await chat_box.fill(gen_command)
            await page.wait_for_timeout(500)
            await page.keyboard.press('Enter')
            
            # C) Wait for Content Generation
            print("⏳ Waiting for Meta AI to render the video (this can take 1-3 minutes)...")
            try:
                # Wait for a video element to appear
                video_el = page.locator('video').last
                await video_el.wait_for(state="attached", timeout=240000) # 4 min timeout
                
                # Stabilization wait for post-render download readiness
                await page.wait_for_timeout(10000) 
                
                # Extract Source URL
                video_src = await video_el.get_attribute("src")
                if not video_src:
                    video_src = await video_el.locator('source').first.get_attribute("src")
                
                if not video_src:
                    raise Exception("Video generated but no source URL found.")

                # D) Binary Download via Browser (Bypasses CDN 403 blocks)
                print("📥 Downloading high-fidelity binary...")
                video_base64 = await page.evaluate(f"""
                    async (url) => {{
                        const response = await fetch(url);
                        const blob = await response.blob();
                        return new Promise(resolve => {{
                            const reader = new FileReader();
                            reader.onloadend = () => resolve(reader.result);
                            reader.readAsDataURL(blob);
                        }});
                    }}
                """, video_src)
                
                # Save to disk
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(video_base64.split(",", 1)[1]))
                
                print(f"✅ Success! Video saved to: {output_path}")
                return True

            except Exception as e:
                print(f"❌ Generation failed: {e}")
                await page.screenshot(path="meta_generator_error.png")
                return False

        # Execute
        result = await session.fetch("https://www.meta.ai/", page_action=automation_logic, timeout=600000)
        return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Universal Meta AI Video Generator")
    parser.add_argument("--prompt", required=True, help="Creative prompt for the video.")
    parser.add_argument("--output", default="output.mp4", help="Filename for the generated video.")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (default: False/Visible).")
    
    args = parser.parse_args()
    
    # Run Async Loop
    asyncio.run(generate_meta_video(args.prompt, args.output, args.headless))
