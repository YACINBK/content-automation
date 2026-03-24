import asyncio
import os
import json
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv(override=True)

async def debug_input():
    env_cookies = os.getenv("META_COOKIES", "").strip()
    cookie_list = json.loads(env_cookies)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await context.add_cookies(cookie_list)
        page = await context.new_page()
        
        print("Navigating to meta.ai...")
        await page.goto("https://www.meta.ai/")
        await asyncio.sleep(5)
        
        # 1. Find all textboxes
        textboxes = await page.get_by_role("textbox").all()
        print(f"Initial Textboxes Found: {len(textboxes)}")
        for i, tb in enumerate(textboxes):
            ph = await tb.get_attribute("placeholder")
            print(f"Textbox {i}: role=textbox, placeholder='{ph}'")
            
        # 2. Trigger rejection
        prompt = "Imagine a video of a wireframe mannequin silhouette suspended inside a giant glowing neon blue hourglass containing static, drawn in the style of a vintage 1980s scientific engineering schematic, retro-clinical aesthetic. Shot on 35mm film, macro photography, shallow depth of field. Grainy film texture, chromatic aberration, stark off-white minimalist background, muted colors with a single toxic neon accent color, highly detailed technical illustration, classified document vibe, vertical 9:16 aspect ratio."
        
        chat_input = page.get_by_placeholder("Ask anything").first
        if await chat_input.count() == 0:
             chat_input = page.get_by_role("textbox").first
             
        print(f"Using chat_input: {await chat_input.count()} elements found.")
        await chat_input.fill(prompt)
        await page.keyboard.press("Enter")
        
        print("Waiting for rejection (45s)...")
        await asyncio.sleep(45)
        
        # 3. Check textboxes again
        textboxes = await page.get_by_role("textbox").all()
        print(f"Post-Rejection Textboxes Found: {len(textboxes)}")
        for i, tb in enumerate(textboxes):
            ph = await tb.get_attribute("placeholder")
            txt = await tb.inner_text()
            print(f"Textbox {i}: placeholder='{ph}', text='{txt[:50]}'")
            
        await page.screenshot(path="debug_input_rejection.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_input())
