import os
import sys
import json
import asyncio
import argparse
import base64
from scrapling.fetchers import AsyncStealthySession
from dotenv import load_dotenv

load_dotenv(override=True)

async def generate_meta_video(prompt: str, output_path: str, headless: bool = False):
    WINDOWS_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    
    env_cookies = os.getenv("META_COOKIES", "").strip()
    cookie_list = []
    if env_cookies:
        try:
            cookie_list = json.loads(env_cookies)
        except Exception as e:
            print(f"Error: {e}")
            return False

    async with AsyncStealthySession(headless=headless, user_agent=WINDOWS_UA) as session:
        if cookie_list:
            await session.context.add_cookies(cookie_list)
            
        async def automation_logic(page):
            await page.wait_for_timeout(3000)
            try:
                if await page.get_by_text("Welcome to Meta AI").count() > 0:
                    dropdown = page.get_by_text("Year", exact=True)
                    if await dropdown.count() > 0:
                        await dropdown.first.click()
                        for _ in range(25): 
                            await page.keyboard.press('ArrowDown')
                        await page.keyboard.press('Enter')
                    await page.get_by_role("button", name="Continue").first.click()
                    await page.wait_for_timeout(2000)
            except:
                pass

            gen_command = f"Imagine a video of {prompt}"
            chat_box = page.locator("role=textbox").first
            await chat_box.fill(gen_command)
            await page.wait_for_timeout(500)
            await page.keyboard.press('Enter')
            
            try:
                video_el = page.locator('video').last
                await video_el.wait_for(state="attached", timeout=240000)
                await page.wait_for_timeout(10000) 
                video_src = await video_el.get_attribute("src") or await video_el.locator('source').first.get_attribute("src")
                video_base64 = await page.evaluate(f"(url) => fetch(url).then(r => r.blob()).then(b => new Promise(res => {{ const rf = new FileReader(); rf.onloadend = () => res(rf.result); rf.readAsDataURL(b); }}))", video_src)
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(video_base64.split(",", 1)[1]))
                return True
            except:
                return False

        return await session.fetch("https://www.meta.ai/", page_action=automation_logic, timeout=600000)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", default="output.mp4")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    asyncio.run(generate_meta_video(args.prompt, args.output, args.headless))
