import asyncio
import os
import json
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv(override=True)

async def debug_dom():
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
        
        prompt = "Imagine a video of a wireframe mannequin silhouette suspended inside a giant glowing neon blue hourglass containing static, drawn in the style of a vintage 1980s scientific engineering schematic, retro-clinical aesthetic. Shot on 35mm film, macro photography, shallow depth of field. Grainy film texture, chromatic aberration, stark off-white minimalist background, muted colors with a single toxic neon accent color, highly detailed technical illustration, classified document vibe, vertical 9:16 aspect ratio."
        
        chat_box = page.locator("role=textbox").first
        await chat_box.fill(prompt)
        await page.keyboard.press("Enter")
        
        print("Prompt sent. Waiting for response...")
        await asyncio.sleep(30) # Wait for rejection to appear
        
        # Find the "Oops!" text and trace its parents
        try:
            oops_element = page.get_by_text("Oops! I can't generate", exact=False).first
            if await oops_element.count() > 0:
                print("Found 'Oops!' element. Analyzing parents...")
                # Get the class of the parent containers
                eval_script = """
                (el) => {
                    let info = [];
                    let curr = el;
                    for(let i=0; i<5; i++) {
                        if(!curr) break;
                        info.push({
                            tag: curr.tagName,
                            className: curr.className,
                            role: curr.getAttribute('role'),
                            id: curr.id
                        });
                        curr = curr.parentElement;
                    }
                    return info;
                }
                """
                parent_info = await oops_element.evaluate(eval_script)
                print(json.dumps(parent_info, indent=2))
            else:
                print("Rejection text not found.")
        except Exception as e:
            print(f"Error finding element: {e}")
            
        await page.screenshot(path="debug_dom_final.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_dom())
