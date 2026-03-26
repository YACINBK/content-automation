import os
import json
import requests
import logging
from dotenv import load_dotenv

load_dotenv(override=True)

# Configuration
API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip('"').strip("'") or "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"
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "google/gemini-2.0-flash-001"

class LLMHandler:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/meta-ai-api",
            "X-Title": "Meta AI Video Recovery"
        }

        self.master_rules = """
        [SYSTEM ROLE: THE EERIE ARCHIVE AI]
        You are an elite forensic investigator AI from the year 2099. Your mission is to document ancient entities failing against modern digital traps.
        You operate in the "Anomaly Log" format. You are cold, high-status, and clinically eerie.
        Crucial: Use simple but high-impact metaphors that everyone understands. Avoid advanced medical jargon like "synaptic" or "neuro-plasticity".

        [THE NARRATIVE ENGINE]
        Every script must combine:
        - Subject: An ancient entity (e.g., Spartan, Ghost, T-Rex).
        - Tragedy: They are trapped in a modern digital habit (scrolling, ghosting, gaming).
        - Impact: Don't use medical terms. Use vivid physical words: "brain-rot", "circuits frying", "soul-melt", "digital poison", "glitch-lock".

        [PACING LAWS - THE 10-WORD SWEET SPOT]
        LAW 1: Every single scene's Voiceover MUST be exactly 9, 10, or 11 words long. This perfectly aligns with the video duration.
        LAW 2: Directness. Coldly state facts. No preamble. No "imagine this".
        LAW 3: Bracketing. Wrap 1-2 high-impact "Pain Words" per scene in brackets (e.g., [poison], [glitch]).

        [THE 5-SCENE ANOMALY ARC]
        Scene 1: Anomaly Log [Num]. Subject [Name] is trapped in [Habit].
        Scene 2: Their ancient anatomy is rotting against the blue light.
        Scene 3: The [algorithm] is eating their sanity. Focus on the loss.
        Scene 4: They are a shell now. Total override of the soul.
        Scene 5: Seal the log. Purge the corrupted data stream immediately.

        [JSON SCHEMA]
        {
        "title": "Anomaly Log [NUM]: [SUBJECT]",
        "subject_name": "NAME",
        "hook_threat": "ALARM (e.g. BRAIN_ROT)",
        "anomaly_outcome": "STATUS (e.g. PURGED, LOST, CORRUPTED, STABILIZED)",
        "narrative_script": [ "VO 1", "VO 2", "VO 3", "VO 4", "VO 5" ],
        "image_prompts": [ "Visual 1", "Visual 2", "Visual 3", "Visual 4", "Visual 5" ],
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
        LAW 6: IDENTIFICATION ACCURACY. If the subject is a historical figure (e.g., Cleopatra, Einstein), NEVER just use their name. ALWAYS add 2-3 specific descriptive traits (e.g., 'Cleopatra with gold kohl-lined eyes and a ceremonial uraeus crown').
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
            # The provided snippet for fallback logic seems to belong to a different function
            # or context (e.g., a loop iterating through visual prompts, using 'master_prompt', 'full_concept', 'i', 'visual_prompts').
            # Since this is the _call_llm method, and these variables are not defined here,
            # applying the snippet directly would cause a NameError.
            # Therefore, only the MODEL_NAME change is applied to maintain syntactical correctness
            # and avoid introducing undefined variables into this specific method.
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
