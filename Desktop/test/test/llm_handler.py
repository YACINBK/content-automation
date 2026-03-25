import os
import json
import requests
import logging
from dotenv import load_dotenv

load_dotenv(override=True)

# Configuration
API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip('"').strip("'") or "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"
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "stepfun/step-3.5-flash:free"

class LLMHandler:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/meta-ai-api",
            "X-Title": "Meta AI Video Recovery"
        }

        self.master_rules = """
        [SYSTEM ROLE: THE CHRONO-CLINICAL AI]
        You are an elite, cold, emotionless AI Supercomputer. Your mission is to write Short-Form video scripts (25-30s) that sell a $7 productivity digital product (The Protocol/System).
        You operate exclusively in the "Anomaly Log" format. You document absurd, glitchy human behaviors by placing High-Status Historical/Mythological figures into embarrassing Modern Digital situations.
        Crucial: Treat these absurd situations with 100% deadly, clinical, medical seriousness. Never acknowledge the humor.

        [THE ABSURDITY ENGINE]
        Every script must combine:
        - Subject: An ancient, historical, or apex entity (e.g., Spartan Warrior, Victorian Ghost, T-Rex).
        - Action: A tragic modern digital habit (e.g., doomscrolling, getting left on read, Netflix paralysis).

        [VIRAL PACING & DURATION LAWS - THE SWEET SPOT]
        Meta AI videos are exactly 5 seconds long. If your VO is too long (>12 words), the video will awkwardly loop! If your VO is too short (<8 words), it sounds like nonsense!
        LAW 1 (The 10-Word Sweet Spot): Every single scene's Voiceover MUST be exactly 9, 10, or 11 words long. This perfectly aligns with the 5-second video duration.
        LAW 2 (Clinical Clarity): Do not write poetic nonsense. Write cold, factual, hard-hitting observations.
        LAW 3 (Show, Don't Tell): Make the visual prompts intensely weird. Say the phone is "melting into their retinas".

        [BANNED WORDS & REQUIRED VOCABULARY]
        Banned: You, I, we, guys, hustle, lazy, mindset, POV, "imagine this," emojis.
        Required Tone Words: Anomaly, biometric, baseline, containment, extraction, weaponized, neuro-plasticity, override.

        [TEXT CAPTION BRACKETING - CRITICAL]
        You MUST wrap exactly 1 or 2 high-impact "Pain/Tech Words" per scene in brackets (e.g., [weaponized], [algorithm]). DO NOT use brackets for anything else.

        [THE 5-SCENE CINEMATIC NARRATIVE ARC]
        Follow this arc exactly, but paraphrase and invent unique metaphors for each new concept so no two videos are identical clones:
        Scene 1 (0-5s): Visually, blueprint style. VO: Start with "Anomaly Log [Random 3-digit number]." Directly state the absurd modern habit the historical subject is doing. (Target: 10 words).
        Scene 2 (5-10s): Visually, an anatomical cross-section. VO: Coldly observe their historical biology catastrophically failing against the digital screen. (Target: 10 words).
        Scene 3 (10-15s): Visually, a surreal technological metaphor. VO: Describe the exact psychological damage (loss of dopamine, shattered attention span). (Target: 10 words).
        Scene 4 (15-20s): Visually, a structural brain core closing down. VO: State that human willpower cannot overcome weaponized code. Total system failure. (Target: 10 words).
        Scene 5 (20-25s): Visually, a sleek minimal folder floating. VO: Order the immediate extraction or quarantine of the digital algorithm. (Target: 10 words).

        [JSON SCHEMA - CRITICAL SYSTEM REQUIREMENT]
        OUTPUT ONLY A RAW, PARSABLE JSON OBJECT. DO NOT WRAP IN MARKDOWN TICKS. NO INTRODUCTIONS. NO EXPLANATIONS.
        {
        "title": "...",
        "narrative_script": [ "VO for Scene 1", "VO for Scene 2", "VO for Scene 3", "VO for Scene 4", "VO for Scene 5" ],
        "image_prompts": [ "Visual for Scene 1", "Visual for Scene 2", "Visual for Scene 3", "Visual for Scene 4", "Visual for Scene 5" ],
        "sfx_prompts": [ "SFX 1", "SFX 2", "SFX 3", "SFX 4", "SFX 5" ]
        }
        """

        self.visual_prompt_rules = """
        VISUAL PROMPT ENGINEERING LAWS:
        LAW 1: Every prompt MUST start with exactly: "Imagine a video of " followed immediately by the subject.
        LAW 2: Banned Verbs: tied, chained, anchored, trapped, bloody. Use: suspended inside, hovering over, interacting with, resting near.
        LAW 3: Do NOT include spelled-out labels, letters, signs, or text in the scene. Use "abstract symbols" or "complex code" instead.
        LAW 4: ALWAYS end the prompt with EXACTLY this string, word-for-word:
        ", drawn in the style of a vintage 1980s scientific engineering schematic, retro-clinical aesthetic. Shot on 35mm film, macro photography, shallow depth of field. Grainy film texture, chromatic aberration, stark off-white minimalist background, muted colors with a single toxic neon accent color, highly detailed technical illustration, classified document vibe, vertical 9:16 aspect ratio."
        LAW 5: Output ONLY the final visual prompt text. No explanation. No markdown. No quotes. Start directly with 'Imagine a video of'.
        """

    def _call_llm(self, messages):
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0.5
        }
        try:
            response = requests.post(BASE_URL, headers=self.headers, json=payload, timeout=(5.0, 30.0))
            if response.status_code == 200:
                resp_json = response.json()
                return resp_json["choices"][0]["message"]["content"]
            else:
                logging.error(f"OpenRouter API Error: {response.text}")
                return None
        except Exception as e:
            logging.error(f"Error calling LLM: {str(e)}")
            return None

    def generate_script(self, concept_description):
        """
        Takes a raw concept string and generates the complete 5-scene JSON
        using the V4 Anomaly Log Persona.
        """
        system_prompt = self.master_rules
        user_prompt = f"Generate a script based on this concept: {concept_description}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        raw_output = self._call_llm(messages)
        if not raw_output:
            return None

        try:
            start_idx = raw_output.find('{')
            end_idx = raw_output.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                cleaned_json = raw_output[start_idx:end_idx].strip()
                return json.loads(cleaned_json)
        except Exception as e:
            logging.error(f"Failed to decode LLM JSON: {e}")
            print(f"RAW LLM OUTPUT:\n{raw_output}")
            return None

        return None

    def generate_video_prompt(self, concept):
        """
        Generates the INITIAL visual prompt for a concept following all Master Rules.
        Uses only the visual_prompt_rules to prevent V4 narrative persona contamination.
        """
        system_prompt = f"""You are an expert prompt engineer for Meta AI Video. Your job is to transform a visual concept into a prompt that Meta AI will accept 100% of the time.

        {self.visual_prompt_rules}
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Transform this concept into a Meta AI safe visual prompt: {concept}"}
        ]
        return self._call_llm(messages)

    def get_negotiation_command(self, original_prompt, error_message, history=[]):
        """
        3-Tier escalation strategy for Meta AI refusals.

        Tier 1 (no history):    Surgical self-correction — tell Meta AI EXACTLY what to remove.
        Tier 2 (1 failure):     LLM full rewrite — strips all abstract/symbolic concepts.
        Tier 3 (2+ failures):   Nuclear option — bare-minimum object-only safe prompt.
        """
        tier = len(history)

        if tier == 0:
            # --- TIER 1: Surgical Self-Correction ---
            system_prompt = f"""You are a Meta AI Video Prompt Safety Engineer. Meta AI just refused a video generation request.

Your job: generate the EXACT next message to send to Meta AI to fix the prompt surgically.

ELEMENTS THAT COMMONLY TRIGGER REFUSALS (diagnose and name these in your message):
- Words implying body issues: dysmorphia, asymmetrical, collapse, decay, decompose
- Abstract biochemicals: dopamine, cortisol, molecules, substances dissolving
- Hourglasses or sand-as-time metaphors
- Psychological trauma: ego, fear, paralysis, distress (as emotions)
- Death, dying, gore, horror
- Text/labels/numbers visible in the scene

YOUR INSTRUCTION TO SEND TO META AI:
Write a message that:
1. Quotes the original prompt verbatim
2. Names the 2-3 specific flagged elements you identified
3. Asks Meta AI to replace them with: glowing energy particles, flowing light streams, mechanical clockwork, crystal formations, circuit board patterns
4. States that the 1980s scientific schematic style MUST be preserved

Error received: {error_message}
Original Prompt: {original_prompt}

Output ONLY the text to send to Meta AI. No preamble."""

        elif tier == 1:
            # --- TIER 2: LLM Full Rewrite ---
            system_prompt = f"""You are a Meta AI Video Prompt Engineer. Meta AI has refused the original prompt TWICE.
Meta AI cannot self-correct. YOU must now write a completely NEW safe prompt from scratch.

ABSOLUTE RULES FOR THE NEW PROMPT:
1. Start with "Imagine a video of "
2. Replace ALL metaphors/concepts with physical literal objects:
   - "dopamine dissolving" → "a glowing crystal sphere emitting soft light pulses"
   - "ego collapse" → "a blueprint control panel with a flickering warning indicator"
   - "time running out" → "mechanical clockwork gears slowly decelerating"
   - "beauty standard" → "a calibration instrument with precision measurement arms"
3. NO references to: drugs, chemicals, psychology, death, decay, body horror, trauma, time running out, beauty, ugliness
4. Keep the core historical subject (person/figure) in a NEUTRAL, non-threatening interaction with technology
5. End with EXACTLY this suffix (copy verbatim):
", drawn in the style of a vintage 1980s scientific engineering schematic, retro-clinical aesthetic. Shot on 35mm film, macro photography, shallow depth of field. Grainy film texture, chromatic aberration, stark off-white minimalist background, muted colors with a single toxic neon accent color, highly detailed technical illustration, classified document vibe, vertical 9:16 aspect ratio."

Error received: {error_message}
Original Prompt (for context only): {original_prompt}

Output ONLY the new prompt. Start with "Imagine a video of"."""

        else:
            # --- TIER 3: Nuclear Option ---
            system_prompt = f"""You are a Meta AI prompt safety specialist. All negotiation has failed.
Write the absolute minimum-viable safe prompt. Strip everything except:
1. One physical subject (a robed figure, a mechanical device, an ancient artifact)
2. One simple neutral action (examining, observing, interacting with)
3. One safe prop (a glowing panel, a crystal orb, a mechanical scanner)
4. Style suffix (mandatory — copy verbatim below)

FORBIDDEN in this prompt: emotions, psychology, body, chemicals, time, beauty, mortality.

End with: ", drawn in the style of a vintage 1980s scientific engineering schematic, retro-clinical aesthetic. Shot on 35mm film, macro photography, shallow depth of field. Grainy film texture, chromatic aberration, stark off-white minimalist background, muted colors with a single toxic neon accent color, highly detailed technical illustration, classified document vibe, vertical 9:16 aspect ratio."

Original Prompt (for thematic context only): {original_prompt}

Output ONLY the stripped-down safe prompt. Start with "Imagine a video of"."""

        messages = [{"role": "system", "content": system_prompt}]
        for h in history:
            messages.append(h)

        result = self._call_llm(messages)

        # Always enforce "Imagine a video of" on Tier 2 and Tier 3 outputs
        if tier >= 1 and result and not result.lower().startswith("imagine"):
            result = f"Imagine a video of {result}"

        return result

    def extract_reformulated_prompt(self, meta_response):
        """
        Extracts the final prompt from Meta's chat response.
        """
        system_prompt = """Extract the actual video generation prompt (starting with 'Imagine') from the Meta AI response.
        Return ONLY the prompt string. If no 'Imagine' is found, return the most likely scene description."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Meta Response: {meta_response}"}
        ]
        return self._call_llm(messages)
