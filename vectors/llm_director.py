import json
import urllib.request
import urllib.error
import os
from dotenv import load_dotenv

# Load the environment variables from the user's known workspace .env file
load_dotenv("D:/test/test/.env")

class LLMDirector:
    def __init__(self, provider="deepseek", model_name="DeepSeek-V3-0324"):
        self.provider = provider
        self.model_name = model_name
        
        # DeepSeek Config
        self.ds_api_key = os.environ.get("DEEPSEEK_API_KEY")
        self.ds_base_url = os.environ.get("DEEPSEEK_BASE_URL")
        
        # OpenRouter (VLM) Config
        self.or_api_key = os.environ.get("OPENROUTER_API_KEY")
        self.or_base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions")
        self.or_model = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
        
        # Ollama Config
        self.ollama_host = "http://localhost:11434"
        
        print(f"\n[*] LLM ROUTING ENABLED: Using provider '{self.provider}' (Model: {self.model_name})")

    def check_connection(self):
        """Checks if the chosen provider is available."""
        if self.provider == "deepseek":
            # For DeepSeek API, we just assume it's reachable. 
            return True
        elif self.provider == "ollama":
            try:
                req = urllib.request.Request(f"{self.ollama_host}/api/tags")
                urllib.request.urlopen(req, timeout=3)
                return True
            except (urllib.error.URLError, TimeoutError):
                return False
        return False

    def _call_deepseek(self, system_prompt, user_prompt, temperature=0.7):
        """Calls the DeepSeek Azure API."""
        headers = {
            "Content-Type": "application/json",
            "api-key": self.ds_api_key,
            "Authorization": f"Bearer {self.ds_api_key}" # Provide both for Azure/Native compatibility
        }
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "top_p": 0.9
        }
        
        req = urllib.request.Request(
            self.ds_base_url or "",
            data=json.dumps(payload).encode('utf-8'),
            headers=headers
        )
        response = urllib.request.urlopen(req)
        result = json.loads(response.read().decode('utf-8'))
        return result['choices'][0]['message']['content'].strip()

    def _call_ollama(self, system_prompt, user_prompt, temperature=0.7):
        """Calls the local Ollama server."""
        payload = {
            "model": self.model_name,
            "prompt": f"{system_prompt}\n\nUSER CONCEPT: {user_prompt}",
            "stream": False,
            "keep_alive": 0,  # CRITICAL: Drops the model from VRAM instantly after generation
            "options": {
                "temperature": temperature,
                "top_p": 0.9
            }
        }
        req = urllib.request.Request(
            f"{self.ollama_host}/api/generate",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        response = urllib.request.urlopen(req)
        result = json.loads(response.read().decode('utf-8'))
        return result.get("response", "").strip()

    def enhance_prompt_for_flux(self, raw_concept, art_style="vector"):
        """Uses chosen LLM to expand a basic idea into a highly optimized FLUX print prompt."""
        print(f"[*] Asking {self.provider.upper()} to engineer the perfect print prompt (Style: {art_style.upper()})...")
        
        if art_style == "oil":
            style_template = (
                "[SUBJECT], thick impasto oil painting style, isolated on a solid bright neon green background. "
                "Expressive, visible palette knife strokes, high contrast color blocking, flat patches of paint. "
                "Masterpiece, traditional medium aesthetics. NO gradients, NO blended transitions. "
                "Clean silhouette, bold structural outlines, no depth of field. "
                "Even studio lighting, well-lit edges, no backlight. "
                "The artwork is contained entirely within the center. No background environment, no painted canvas texture."
            )
        else:
            style_template = (
                "[SUBJECT], isolated on a solid bright neon green background. A vibrant, high-contrast illustration "
                "using flat vector-style shading and bold outlines. The artwork is stylized with minimal colors, "
                "screen-print aesthetics, and clean geometric primitives. "
                "Clean silhouette, bold structural outlines, no depth of field. "
                "Even studio lighting, well-lit edges, no backlight. "
                "Professional graphic design, crisp edges, apparel graphic. No background environment."
            )
            
        system_prompt = (
            "You are an expert prompt engineer for FLUX.1 AI preparing artwork for apparel screen printing. "
            "Your job is to take a user's raw concept and turn it into a highly detailed visual prompt. "
            "RULES: "
            "1. HIERARCHICAL LAYER PROMPTING: Describe the main subject completely, then describe the accessories, and ONLY define the background at the very end. "
            "2. NO NEGATIVE PROMPTS: Focus entirely on describing exactly what you do want. "
            "3. EXTREME CONTRAST BACKGROUND: Always use the unnatural neon green background to ensure mathematically perfect edge extraction. "
            f"4. PRINT-SPECIFIC FORMAT: You MUST format your final output using EXACTLY this template, replacing [SUBJECT] with your hierarchically structured description:\n{style_template}"
        )

        try:
            if self.provider == "deepseek":
                enhanced_prompt = self._call_deepseek(system_prompt, raw_concept, temperature=0.7)
            else:
                enhanced_prompt = self._call_ollama(system_prompt, raw_concept, temperature=0.7)
            
            enhanced_prompt = enhanced_prompt.strip('"').strip("'")
            print(f"[OK] {self.provider.upper()} Engineered Prompt: {enhanced_prompt}")
            return enhanced_prompt
            
        except Exception as e:
            print(f"[X] ERROR: {self.provider.upper()} failed ({e}). Applying manual fallback prompt engineering rules.")
            fallback_prompt = style_template.replace("[SUBJECT]", raw_concept)
            return fallback_prompt

    def extract_core_subjects(self, raw_concept):
        """DEPRECATED (Text-Only): Uses chosen LLM to guess what SAM 2 should extract based on prompt alone."""
        print(f"[*] Asking {self.provider.upper()} Surgeon to identify core subjects from text...")
        
        system_prompt = (
            "You are an expert graphic designer preparing artwork for a t-shirt print. "
            "Your job is to read a raw concept and identify ONLY the main subjects/characters/objects "
            "that must be printed. You must ignore backgrounds, environments, locations, or lighting instructions. "
            "RULES: "
            "1. Output MUST be a simple comma-separated list of nouns. "
            "2. Keep descriptions incredibly brief (e.g. 'cyberpunk cat, neon jacket, motorcycle'). "
            "3. DO NOT include background elements (e.g. ignore 'park bench', 'city street', 'night sky'). "
            "4. Return ONLY the list. No explanations, no quotes."
        )

        try:
            if self.provider == "deepseek":
                extracted_subjects = self._call_deepseek(system_prompt, raw_concept, temperature=0.3)
            else:
                extracted_subjects = self._call_ollama(system_prompt, raw_concept, temperature=0.3)
            
            extracted_subjects = extracted_subjects.strip('"').strip("'")
            print(f"[OK] {self.provider.upper()} Surgeon guessed: {extracted_subjects}")
            return extracted_subjects
            
        except Exception as e:
            print(f"[X] ERROR: {self.provider.upper()} Surgeon failed ({e}). Falling back to raw concept.")
            return raw_concept

    def analyze_image_for_extraction(self, image_path):
        """VLM (Vision-Language Model): Uses OpenRouter to look at the generated image and apply Semantic Anchoring rules."""
        import base64
        print(f"[*] Asking OpenRouter VLM ({self.or_model}) to visually identify core subjects for SAM 2...")
        
        if not self.or_api_key:
            print("[X] ERROR: OpenRouter API key missing. Cannot perform VLM analysis.")
            return None

        # Convert image to base64
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"[X] ERROR reading image for VLM: {e}")
            return None

        system_prompt = (
            "You are an expert graphic designer preparing artwork for apparel screen printing. "
            "I will provide you with an image. Your task is to identify the primary subject(s) "
            "and any critically important props or elements that give the artwork its semantic meaning and context.\n\n"
            "Rules for Selection:\n"
            "1. Identify the main character, subject, or focal point.\n"
            "2. Identify any items the subject is holding, interacting with, or standing on that are necessary "
            "for the image to make sense (e.g., if a person is sitting on a chair, keep the chair. If a knight "
            "is holding a glowing sword, keep the sword).\n"
            "3. Strictly IGNORE all background environments, scenery, skies, distant buildings, or unprintable clutter.\n\n"
            "Output Format:\n"
            "You must output ONLY a comma-separated list of the objects to keep. Do not include any conversational text, "
            "explanations, or punctuation other than commas. Keep the descriptions simple."
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.or_api_key}"
        }
        
        payload = {
            "model": self.or_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": "Analyze this image according to your rules and output the comma-separated list."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]
                }
            ],
            "temperature": 0.2
        }

        try:
            req = urllib.request.Request(
                self.or_base_url,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers
            )
            response = urllib.request.urlopen(req)
            result = json.loads(response.read().decode('utf-8'))
            extracted_subjects = result['choices'][0]['message']['content'].strip()
            
            # Grounding DINO parses much better when objects are separated by periods instead of commas
            # e.g. "astronaut, laser gun, moon rock" -> "astronaut. laser gun. moon rock."
            dino_ready_prompt = extracted_subjects.replace(",", ".").strip()
            if not dino_ready_prompt.endswith("."):
                dino_ready_prompt += "."
                
            print(f"[OK] VLM Surgeon identified: {extracted_subjects}")
            print(f"    -> DINO Formatting: {dino_ready_prompt}")
            
            return dino_ready_prompt
            
        except Exception as e:
            print(f"[X] ERROR: VLM Surgeon failed ({e}).")
            return None
