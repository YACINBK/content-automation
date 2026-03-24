"""
Meta AI Video Generator - Best Format
Uses Playwright directly for full control over cookie injection before navigation.
"""
import os
import sys
import json
import asyncio
import argparse
import base64
import re
from dotenv import load_dotenv

load_dotenv(override=True)

async def run_automation(prompt: str, output_file: str, headless: bool = False):
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Installing playwright...")
        os.system("pip install playwright && playwright install chromium")
        from playwright.async_api import async_playwright

    WINDOWS_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )

    # Parse cookies from .env
    env_cookies = os.getenv("META_COOKIES", "").strip()
    cookie_list = []
    if env_cookies:
        try:
            cookie_list = json.loads(env_cookies)
            print(f"Loaded {len(cookie_list)} cookies from .env")
        except Exception as e:
            print(f"Cookie parse error: {e}")
    else:
        print("WARNING: No META_COOKIES in .env")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(user_agent=WINDOWS_UA)

        # Inject cookies BEFORE any navigation
        if cookie_list:
            await context.add_cookies(cookie_list)
            print(f"Injected {len(cookie_list)} session cookies into context")

        page = await context.new_page()

        print("Navigating to meta.ai...")
        await page.goto("https://www.meta.ai/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        # Age gate bypass (only fires if logged-out / new session)
        try:
            if await page.get_by_text("Welcome to Meta AI").count() > 0:
                print("Age gate detected — bypassing...")
                dropdown = page.get_by_text("Year", exact=True)
                if await dropdown.count() > 0:
                    await dropdown.first.click()
                    for _ in range(25):
                        await page.keyboard.press("ArrowDown")
                        await page.wait_for_timeout(30)
                    await page.keyboard.press("Enter")
                continue_btn = page.get_by_role("button", name="Continue")
                if await continue_btn.count() > 0:
                    await continue_btn.first.click()
                await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Age gate check: {e}")

        # Submit the video generation command
        prefix = "Imagine a video of "
        if prompt.lower().startswith(prefix.lower()):
            gen_command = prompt
        else:
            gen_command = f"{prefix}{prompt}"

        print(f'Sending: "{gen_command[:80]}..."')

        # Find the active chat input with multiple fallbacks
        selectors = [
            'textarea[data-testid="composer-input"]',
            'div[contenteditable="true"]',
            'role=textbox',
            '[placeholder*="Ask anything"]'
        ]

        chat_box = None
        for sel in selectors:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                chat_box = loc
                print(f"Found active chat input via: {sel}")
                break

        if not chat_box:
            print("WARNING: No visible chat input found. Taking diagnostic screenshot.")
            await page.screenshot(path="debug_no_input.png")
            chat_box = page.locator("role=textbox").first

        print(f"Using chat input: {await chat_box.get_attribute('placeholder') or 'No Placeholder'}")

        try:
            await chat_box.scroll_into_view_if_needed()
            await chat_box.click(force=True, timeout=10000)
            await chat_box.fill(gen_command)
            await page.wait_for_timeout(500)
            await page.keyboard.press("Enter")
        except Exception as e:
            print(f"Initial submission failed: {e}")
            await page.screenshot(path="debug_click_fail.png")
            await page.mouse.click(500, 800)
            await page.keyboard.type(gen_command)
            await page.keyboard.press("Enter")

        await page.wait_for_timeout(2000)

        # --- SELF-CORRECTION LOOP ---
        max_attempts = 4  # 1 initial + 3 negotiation rounds
        # Persistent LLM history maintained across all negotiation rounds
        llm_history = []

        for attempt in range(max_attempts):
            print(f"Attempt {attempt + 1}: Waiting for video or rejection...")

            old_msg_count = await page.locator(".ur-markdown").count()

            video_found = False
            rejection_detected = False

            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < 240:  # 4 min hard cap
                # 1. Check for video
                if await page.locator("video").count() > 0:
                    video_found = True
                    break

                # 2. Check for NEW text rejection/stalling
                current_msgs = page.locator(".ur-markdown")
                msg_count = await current_msgs.count()

                if msg_count > old_msg_count:
                    bot_messages = current_msgs.last
                    msg_text = await bot_messages.inner_text()

                    # Ignore "Thinking..." boilerplate
                    if "thought for" in msg_text.lower() and len(msg_text) < 50:
                        await asyncio.sleep(2)
                        continue

                    # Explicit rejection keywords
                    if any(x in msg_text.lower() for x in ["oops", "too complex", "unable to", "can't generate", "unfortunately"]):
                        print(f"Bot Rejection Detected: {msg_text[:100]}...")
                        rejection_detected = True
                        break

                    # Stall detection: if Meta replied with TEXT (not video) for >15s, assume problem
                    if (asyncio.get_event_loop().time() - start_time) > 15:
                        if len(msg_text) > 10:
                            print("Text response detected for >15s with no video. Assuming complication.")
                            rejection_detected = True
                            break

                await asyncio.sleep(5)

            # --- SUCCESS ---
            if video_found:
                print("Video element detected. Proceeding to download...")
                video_el = page.locator("video").last
                await page.wait_for_timeout(10000)

                video_src = await video_el.get_attribute("src")
                if not video_src:
                    video_src = await video_el.locator("source").first.get_attribute("src")

                if not video_src:
                    raise Exception("Video appeared but no src URL found")

                print("Downloading binary...")
                video_base64 = await page.evaluate(
                    """
                    async (url) => {
                        const r = await fetch(url);
                        const b = await r.blob();
                        return new Promise(res => {
                            const fr = new FileReader();
                            fr.onloadend = () => res(fr.result);
                            fr.readAsDataURL(b);
                        });
                    }
                    """,
                    video_src,
                )

                os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
                with open(output_file, "wb") as f:
                    f.write(base64.b64decode(video_base64.split(",", 1)[1]))

                print(f"SUCCESS: Video saved → {output_file}")
                await browser.close()
                return True

            # --- NEGOTIATION ---
            elif rejection_detected and attempt < max_attempts - 1:
                print(f"[NEGOTIATION] Attempt {attempt + 1} — Entering Adaptive LLM Negotiation Phase...")
                from llm_handler import LLMHandler
                llm = LLMHandler()

                # Build negotiation command — uses visual_prompt_rules ONLY, never V4 persona
                negotiation_command = llm.get_negotiation_command(gen_command, msg_text, history=llm_history)

                # FALLBACK if LLM call fails entirely
                if not negotiation_command:
                    print("[NEGOTIATION] LLM call failed — using hardcoded fallback interrogation.")
                    negotiation_command = (
                        f'refine this prompt ({gen_command}) in order to make it acceptable '
                        f'by meta ai while conserving its context 100% and not losing any mentioned details'
                    )

                print(f"[NEGOTIATION] Sending to Meta AI: {negotiation_command[:120]}...")

                try:
                    for sel in selectors:
                        loc = page.locator(sel).first
                        if await loc.count() > 0 and await loc.is_visible():
                            chat_box = loc
                            break

                    await chat_box.click(force=True)
                    await chat_box.fill(negotiation_command)
                    await page.wait_for_timeout(500)
                    await page.keyboard.press("Enter")

                    # Wait for Meta AI to reply
                    neg_msg_count = await page.locator(".ur-markdown").count()
                    for _ in range(120):  # up to 60s
                        await asyncio.sleep(0.5)
                        if (await page.locator(".ur-markdown").count()) > neg_msg_count:
                            break

                    bot_response = await page.locator(".ur-markdown").last.inner_text()
                    print(f"[NEGOTIATION] Meta AI replied: {bot_response[:120]}...")

                    # Update LLM history — keeps context across all negotiation rounds
                    llm_history.append({"role": "assistant", "content": negotiation_command})
                    llm_history.append({"role": "user", "content": f"Meta AI replied: {bot_response}"})

                    # Extract the refined prompt from Meta's response
                    extracted = llm.extract_reformulated_prompt(bot_response)
                    
                    # Ensure extraction isn't empty before calling len() on it
                    extracted_text = str(extracted) if extracted else ""
                    print(f"[NEGOTIATION] LLM extracted: {extracted_text[:120]}")

                    # ROBUST FALLBACK: Never send empty/placeholder strings to Meta
                    EMPTY_MARKERS = ["[No output", "empty string", "no \"imagine\"", "no scene", "none"]
                    is_bad_extraction = (
                        not extracted_text
                        or len(extracted_text.strip()) < 10
                        or any(m.lower() in extracted_text.lower() for m in EMPTY_MARKERS)
                    )

                    if is_bad_extraction:
                        print("[NEGOTIATION] Extraction invalid. Applying raw text fallback.")
                        # Allow multi-line capturing until the closing quote or end of string
                        m = re.search(r'(Imagine[^"]+)', bot_response, re.IGNORECASE)
                        if m:
                            new_prompt = m.group(1).strip()
                        else:
                            # Last resort: LLM re-crafts a safe prompt from the original
                            print("[NEGOTIATION] No Imagine found. LLM is re-crafting from scratch.")
                            new_prompt = llm.generate_video_prompt(gen_command) or gen_command
                    else:
                        new_prompt = extracted.strip()

                    # -- CONVERSATIONAL CONSENT FEATURE --
                    # If Meta AI ends its message by proposing the prompt and asking "Shall we try this?"
                    offer_keywords = ["shall we", "give this one a shot", "give it a shot", "what do you think", "generate this for you", "try this", "would you like"]
                    last_paragraph = bot_response.split('\n')[-1].lower()
                    
                    if "?" in last_paragraph and any(k in last_paragraph for k in offer_keywords):
                        print("[NEGOTIATION] Meta AI offered to generate a refined prompt. Autoresizing consent.")
                        new_prompt = "Yes, please generate exactly that without changing any details."

                    # Always enforce the required prefix, UNLESS it's our conversational consent reply
                    if not new_prompt.lower().startswith("imagine") and not new_prompt.lower().startswith("yes,"):
                        new_prompt = f"Imagine a video of {new_prompt}"

                    print(f"[NEGOTIATION] Re-firing with: {new_prompt[:120]}...")

                    for sel in selectors:
                        loc = page.locator(sel).first
                        if await loc.count() > 0 and await loc.is_visible():
                            chat_box = loc
                            break

                    await chat_box.click(force=True)
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Backspace")
                    await chat_box.fill(new_prompt)
                    await page.wait_for_timeout(1000)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(2000)
                    # outer loop continues → polls for video on next attempt

                except Exception as neg_err:
                    print(f"[NEGOTIATION] Step failed: {neg_err}")
                    # Do NOT break — let the outer loop try again

            else:
                print("FAILED: No video produced after all negotiation attempts or timeout.")
                await page.screenshot(path="meta_error.png")
                await browser.close()
                return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Meta AI Video Generator")
    parser.add_argument("--prompt", required=True, help="Video prompt")
    parser.add_argument("--output", required=True, help="Output .mp4 path")
    parser.add_argument("--headless", action="store_true", help="Headless mode")
    args = parser.parse_args()
    asyncio.run(run_automation(args.prompt, args.output, args.headless))
