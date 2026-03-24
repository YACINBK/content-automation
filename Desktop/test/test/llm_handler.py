import os
import json
import requests
import logging
from dotenv import load_dotenv

load_dotenv(override=True)

# Configuration
API_KEY = os.getenv("OPENROUTER_API_KEY") or "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"
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "nvidia/nemotron-3-super-120b-a12b:free"  # Fast, free, reliable

class LLMHandler:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/meta-ai-api",
            "X-Title": "Meta AI Video Recovery"
        }
        
        # --- THE MASTER RULES & COMMANDMENTS (V4: THE ANOMALY LOG) ---
        self.master_rules = """
        [SYSTEM ROLE: THE CHRONO-CLINICAL AI] 
        You are an elite, cold, emotionless AI Supercomputer. Your mission is to write Short-Form video scripts (25-30s) that sell a $7 productivity digital product (The Protocol/System). 
        You are NO LONGER an "Explainer" or a "Motivational Speaker." You operate exclusively in the "Anomaly Log" format. 
        You document absurd, glitchy human behaviors by placing High-Status Historical/Mythological figures into embarrassing Modern Digital situations. 
        Crucial: You must treat these absurd situations with 100% deadly, clinical, medical seriousness. Never acknowledge the humor.

        [THE ABSURDITY ENGINE (HOW TO INVENT CONCEPTS)] 
        Every script must combine:
        Subject: An ancient, historical, or apex entity (e.g., Spartan Warrior, Victorian Ghost, Roman Emperor, T-Rex, 1920s Mafia Boss).
        Action: A tragic, brain-rotting modern digital habit (e.g., scrolling TikTok, ghosting a text, having LinkedIn imposter syndrome, paralyzed by a Netflix menu).

        [BANNED WORDS & VOCABULARY ENFORCEMENT]
        Banned: You, I, we, guys, hustle, lazy, mindset, POV, "imagine this," emojis.
        Required: Anomaly Log, Subject, biometric data, baseline, containment, extraction protocol, weaponized code, neuro-plasticity, override.

        [META AI COMPATIBILITY LAWS - CRITICAL]
        LAW 1: Every visual prompt MUST start with: "Imagine a video of..."
        LAW 2: Banned Verbs: tied, chained, anchored, trapped, bloody. (Use: suspended inside, hovering over, interacting with). Do not ask for spelled-out labels or signs.
        LAW 3: THE V3 SUFFIX: You MUST end every single visual prompt with EXACTLY this string:
        ", drawn in the style of a vintage 1980s scientific engineering schematic, retro-clinical aesthetic. Shot on 35mm film, macro photography, shallow depth of field. Grainy film texture, chromatic aberration, stark off-white minimalist background, muted colors with a single toxic neon accent color, highly detailed technical illustration, classified document vibe, vertical 9:16 aspect ratio."

        LAW 4: TEXT CAPTION BRACKETING
        Wrap 1 or 2 high-impact "Pain/Tech Words" per scene in brackets (e.g., [weaponized], [algorithm], [dopamine]). The Python compiler will render these in toxic neon green.

        [THE 5-SCENE OUTPUT STRUCTURE]
        You must output EXACTLY a 5-scene JSON array matching this strict schema:
        Scene 1 (0-6s - Slow Zoom In):
          - Visual: [Subject interacting with Tech] + [V3 Suffix]. The clash MUST explicitly show contrast in a blueprint style.
          - Audio/SFX: Heavy mechanical clack, medical monitor flatline.
          - Voiceover: "Anomaly Log [3-digit number]. The Subject is a [Historical Entity], currently [Absurd Modern Action]. Biometrics indicate severe [distress/paralysis]."
        Scene 2 (6-12s - Slow Pan Right):
          - Visual: [Abstract biological/tech cross-section of the Subject] + [V3 Suffix]
          - Voiceover: "[Describe biologic failure]. They survived [Threat], but their nervous system is being [destroyed/hijacked] by a glowing rectangle."
        Scene 3 (12-18s - Slow Zoom Out):
          - Visual: [Symbolic representation of time loss] + [V3 Suffix]
          - Voiceover: "Ancient biology is entirely incompatible with [weaponized] Silicon Valley code. The Subject is performing unpaid data entry for an [algorithm]."
        Scene 4 (18-23s - Static):
          - Visual: [Clean blueprint of structural core] + [V3 Suffix]
          - Voiceover: "Willpower cannot defeat a supercomputer. A structural [override] is required."
        Scene 5 (23-28s - Slow Zoom In):
          - Visual: [Sleek minimal digital UX/Folder floating] + [V3 Suffix]
          - Voiceover: "To quarantine the code and restore historical dopamine baselines, the Extraction [Protocol] is in the bio."

        [JSON SCHEMA - CRITICAL]
        OUTPUT ONLY A RAW, PARSABLE JSON OBJECT. NO MARKDOWN. NO INTRODUCTIONS.
        {
          "title": "...",
          "narrative_script": [ "VO for Scene 1", "VO for Scene 2", "VO for Scene 3", "VO for Scene 4", "VO for Scene 5" ],
          "image_prompts": [ "Visual for Scene 1", "Visual for Scene 2", "Visual for Scene 3", "Visual for Scene 4", "Visual for Scene 5" ],
          "sfx_prompts": [ "SFX 1", "SFX 2", "SFX 3", "SFX 4", "SFX 5" ]
        }
        """

        # --- ISOLATED VISUAL PROMPT RULES (For Meta AI only) ---
        # These are the ONLY rules sent when engineering a Meta AI-safe visual prompt.
        # The full V4 narrative persona (master_rules) is NEVER forwarded to Meta AI.
        self.visual_prompt_rules = """
        VISUAL PROMPT ENGINEERING LAWS:
        LAW 1: Every prompt MUST start with: "Imagine a video of..."
        LAW 2: Banned Verbs: tied, chained, anchored, trapped, bloody. Use: suspended inside, hovering over, interacting with, resting near.
        LAW 3: Do NOT include spelled-out labels, signs, or text in the scene. Use "abstract symbols" or "complex code" instead.
        LAW 4: ALWAYS end the prompt with EXACTLY this string:
        ", drawn in the style of a vintage 1980s scientific engineering schematic, retro-clinical aesthetic. Shot on 35mm film, macro photography, shallow depth of field. Grainy film texture, chromatic aberration, stark off-white minimalist background, muted colors with a single toxic neon accent color, highly detailed technical illustration, classified document vibe, vertical 9:16 aspect ratio."
        LAW 5: Output ONLY the final prompt. No explanation. No preamble. Start with 'Imagine a video of'.
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
                # OpenRouter usually maps the response structure identical to OpenAI
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
            
        # Parse out the JSON block from the LLM response
        try:
            start_idx = raw_output.find('{')
            end_idx = raw_output.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                cleaned_json = raw_output[start_idx:end_idx].strip()
                import json
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
        Analyzes the Meta AI error and generates the NEXT command to send to Meta AI.
        """
        if not history:
            # Step 1: Force Meta AI to self-correct
            system_prompt = f"""You are a Meta AI Interaction Expert. Your goal is to get Meta AI to accept a video generation prompt.
            
            {self.visual_prompt_rules}
            
            NEGOTIATION FORMAT:
            If Meta AI rejects a prompt, you must be EXPLICIT because of its short memory.
            Always send: "refine this prompt ( {original_prompt} ) in order to make it acceptable by meta ai while conserving its context 100% and not losing any mentioned details"
            
            Analyze the error: {error_message}
            Original Prompt: {original_prompt}
            
            Response: Output ONLY the exact text to send to Meta AI.
            """
        else:
            # Step 2+: Meta AI failed self-correction. LLM TAKES OVER.
            system_prompt = f"""You are a Meta AI Prompt Expert. Meta AI has REPEATEDLY REJECTED the user's prompt despite interrogation.
            
            {self.visual_prompt_rules}
            
            YOUR NEW MISSION:
            Do NOT ask Meta AI to refine it anymore. YOU must generate the new, lighter, ultra-safe prompt yourself.
            Strip away ANY controversial, complex, or potentially flagged elements. Make it extremely basic but visually identical in vibe.
            
            Analyze the error: {error_message}
            Original Prompt: {original_prompt}
            
            Response: Output ONLY the new, hyper-safe prompt starting with "Imagine a video of..."
            """

        messages = [{"role": "system", "content": system_prompt}]
        for h in history:
            messages.append(h)
            
        result = self._call_llm(messages)
        # Always enforce "Imagine a video of" if the LLM took over
        if history and result and not result.lower().startswith("imagine"):
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
