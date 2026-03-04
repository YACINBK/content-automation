"""
Poetry Engine - Poetry Selection & Image Prompt Generation
===========================================================

This module handles:
1. LLM-based selection of famous poetry excerpts (public domain poets)
2. Breaking poetry into individual verses/lines
3. Generating artistic image prompts for each verse
4. Applying fixed early century oil painting aesthetic

Created for poetry-based video automation.
"""

import os
import json
import logging
import requests
import re
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# API Configuration
API_KEY = os.getenv("OPENROUTER_API_KEY") or "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"
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "openrouter/free"

# Style templates — applied to every image prompt
OIL_PAINTING_STYLE = "early century oil painting, soft warm lighting, textured oil paint effect, muted earth tones, classical European illustration, nostalgic mood, detailed brush strokes, museum painting style"

# Used when --include-people is on (warmer, portraiture-focused)
PEOPLE_PAINTING_STYLE = "early century oil painting, warm intimate lighting, rich portraiture technique, expressive face and gesture, textured oil paint, deep amber and gold tones, classical European figure painting, detailed brush strokes, museum quality"

# Used when --romance is on (vivid, passionate, intimate)
ROMANCE_PAINTING_STYLE = "romantic oil painting, warm emotional atmosphere, rich crimson and deep gold palette, soft candlelight, lush painterly brushwork, impressionist warmth, museum quality art nouveau style"

# Base parts of the system prompt
POETRY_SYSTEM_PROMPT_BASE = """You are an expert poetry curator and visual artist specializing in classical poetry and oil painting aesthetics.

CORE DIRECTIVE 1: FAMOUS POETRY SELECTION
Select excerpts from famous PUBLIC DOMAIN poets such as:
- Rumi, Hafez, Omar Khayyam (Persian poets)
- William Shakespeare, William Blake, John Keats (English poets)
- Emily Dickinson, Walt Whitman, Robert Frost (American poets)
- Pablo Neruda, Rabindranath Tagore (International poets)

CORE DIRECTIVE 2: TOPIC RELEVANCE
The selected poetry MUST deeply resonate with the given topic. Choose verses that capture the essence, emotion, and atmosphere of the theme.

CORE DIRECTIVE 3: VERSE STRUCTURE
Select EXACTLY 6-8 verses (lines or couplets) that:
- Flow naturally together
- Tell a cohesive emotional story
- Are suitable for individual visual representation
- Each verse should be 1-2 lines maximum

CORE DIRECTIVE 4: IMAGE PROMPT GENERATION
For EACH AND EVERY verse, create a vivid visual scene that:
- Captures the emotional essence of that specific verse
- Translates abstract concepts into concrete imagery
- Focuses on atmosphere, mood, and symbolic elements (clocks, nature, landscape, shadows)
- Is suitable for early 20th century oil painting style

CRITICAL: The number of image_prompts MUST EXACTLY MATCH the number of verses. For every single line in the 'verses' array, there MUST be exactly one corresponding entry in 'image_prompts'. If you provide 4 verses, you MUST provide 4 image prompts. No exceptions.
"""

HUMAN_CENTRIC_DIRECTIVE = """
CORE DIRECTIVE 5: HUMAN SUBJECT AWARENESS
If a verse addresses or describes a person (lover, friend, mother, stranger) or an interpersonal interaction, PRIORITIZE showing them.
- Use "Portraiture", "Figure painting", or "Silhouetted couple" where appropriate.
- Focus on expressive gestures and emotional presence.
- Ensure the figures feel integrated into the classical scene.
"""

ROMANCE_DIRECTIVE = """
CORE DIRECTIVE 7: ROMANTIC & FLIRTY AESTHETIC
The imagery MUST be super romantic, flirty, and emotionally charged:
- Prioritize intimate close-ups (lingering gazes, hands touching or brushing against skin).
- Use warm, passionate color accents (crimson, deep golds, soft rose).
- Emphasize the chemistry between subjects—stolen glances, leaning in, soft smiles.
- Atmosphere should be dreamy, sensual, and deeply evocative of yearning and passion.
"""

POETRY_SYSTEM_PROMPT_FOOTER = """
CORE DIRECTIVE 6: ARTISTIC CONSISTENCY
All image prompts should feel like they belong to the same artistic series:
- Consistent color palette (muted earth tones, warm lighting)
- Similar compositional style
- Cohesive visual narrative

OUTPUT FORMAT (JSON ONLY):
{
    "poet": "Name of the poet",
    "poem_title": "Title of the poem or 'Untitled'",
    "topic": "The user's topic",
    "full_text": "Complete selected excerpt with line breaks",
    "verses": [
        "First line/verse",
        "Second line/verse",
        "Third line/verse",
        "Fourth line/verse"
    ],
    "image_prompts": [
        "Visual description for verse 1",
        "Visual description for verse 2",
        "Visual description for verse 3",
        "Visual description for verse 4"
    ],
    "metadata": {
        "mood": "Overall emotional tone",
        "color_palette": "Dominant colors",
        "time_period": "Historical context"
    }
}

EXAMPLE OF 1:1 MAPPING:
If you choose 4 lines:
"verses": ["Line 1", "Line 2", "Line 3", "Line 4"]
Then you MUST have:
"image_prompts": ["Prompt 1", "Prompt 2", "Prompt 3", "Prompt 4"]
DO NOT Group multiple verses into one prompt. 
DO NOT leave any verse without a prompt.

CRITICAL RULES:
1. Do NOT include the oil painting style in image_prompts. That will be added automatically.
2. The arrays "verses" and "image_prompts" MUST have the EXACT SAME LENGTH.
3. Count your verses and image_prompts before responding to ensure they match.
4. Ensure the JSON is valid (properly escaped quotes, no literal newlines inside strings).
5. Output ONLY the JSON. Do not include any pre-talk, after-talk, post-analysis, or multiple examples.
"""


class PoetryEngine:
    """Handles poetry selection and image prompt generation."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the poetry engine with API credentials."""
        self.api_key = api_key or API_KEY
        self.oil_painting_style = OIL_PAINTING_STYLE
    
    def select_poetry(self, topic: str, include_people: bool = False, romance: bool = False) -> Optional[Dict]:
        """
        Select famous poetry based on topic and generate image prompts.
        
        Args:
            topic (str): The theme/topic for poetry selection
            include_people (bool): Whether to prioritize human subjects in images
            romance (bool): Whether to enforce a super romantic and flirty aesthetic
            
        Returns:
            Dict containing poetry data and image prompts, or None if failed
        """
        user_prompt = f"""Select a powerful excerpt from famous poetry for the topic: "{topic}"

Requirements:
- Choose 6-8 verses that deeply resonate with this theme
- Each verse should be visually rich and emotionally evocative
- Create distinct, atmospheric image prompts for each verse
- Ensure the poetry is from a public domain poet
- The excerpt should feel complete and meaningful

Generate JSON response."""
        
        style = ROMANCE_PAINTING_STYLE if romance else (PEOPLE_PAINTING_STYLE if include_people else None)
        return self._generate_poetry_json(user_prompt, include_people, romance, _style=style)

    def process_raw_poem(self, poem_text: str, include_people: bool = False, romance: bool = False) -> Optional[Dict]:
        """
        Process a raw poem provided by the user.

        Verses are parsed LOCALLY from the input text — the LLM is only asked
        to generate image prompts for each verse.  This guarantees that no line
        is dropped, merged, or reworded by the model.

        Parsing rules:
        - Non-empty lines separated by blank lines form natural verse groups.
        - Lines starting with '[Optional Visual' are treated as image-hint
          comments: they are stripped from the spoken verses but their hint
          text is forwarded to the image-prompt LLM call.
        - If every line is non-blank (no blank-line separators), each line
          becomes its own verse.
        """
        import re as _re

        # ------------------------------------------------------------------ #
        # 1. Parse input into verse groups                                    #
        # ------------------------------------------------------------------ #
        raw_lines = poem_text.splitlines()

        # Separate optional-visual hints from real lines
        visual_hint_re = _re.compile(r'^\[Optional Visual.*?\]', _re.IGNORECASE)
        visual_hints: dict[int, str] = {}   # index of NEXT verse → hint text
        clean_lines = []
        pending_hint = None

        for line in raw_lines:
            stripped = line.strip()
            m = visual_hint_re.match(stripped)
            if m:
                # Store hint to attach to the next real verse
                pending_hint = stripped
            else:
                if pending_hint is not None:
                    visual_hints[len(clean_lines)] = pending_hint
                    pending_hint = None
                clean_lines.append(stripped)

        # Group by blank-line separators into verse blocks
        verse_blocks: list[str] = []
        current: list[str] = []
        for line in clean_lines:
            if line == "":
                if current:
                    verse_blocks.append(" ".join(current))
                    current = []
            else:
                current.append(line)
        if current:
            verse_blocks.append(" ".join(current))

        # Fallback: if no blank-line separators were found, OR if any block is
        # suspiciously large (lines got merged), split by individual lines instead.
        if len(verse_blocks) <= 1 and len(clean_lines) > 1:
            verse_blocks = [l for l in clean_lines if l]
        elif any(len(b) > 120 for b in verse_blocks):
            # Some blocks are too long — the poem likely has lines not separated by blank lines
            verse_blocks = [l for l in clean_lines if l]

        if not verse_blocks:
            logging.error("❌ Could not parse any verses from the provided poem text.")
            return None

        num_verses = len(verse_blocks)
        logging.info(f"   📝 Parsed {num_verses} verses from poem text (exact, no LLM rewrite)")
        for i, v in enumerate(verse_blocks):
            logging.info(f"      Verse {i+1}: \"{v[:80]}\"")

        # ------------------------------------------------------------------ #
        # 2. Ask the LLM ONLY for image prompts                               #
        # ------------------------------------------------------------------ #
        verses_for_prompt = "\n".join(
            f"{i+1}. {v}" + (f"  [hint: {visual_hints[i]}]" if i in visual_hints else "")
            for i, v in enumerate(verse_blocks)
        )

        user_prompt = f"""You are generating image prompts for a poetry video.

The poem has EXACTLY {num_verses} verses listed below. Your ONLY task is to produce
one vivid, painterly image prompt for each verse — in the same order.

Verses:
{verses_for_prompt}

Return a JSON object with this exact structure:
{{
  "poem_title": "<a poetic title for this poem>",
  "poet": "<inferred poet name or 'Unknown'>",
  "full_text": "<all verses joined with newlines>",
  "verses": [<the {num_verses} verse strings, EXACTLY as provided above, no changes>],
  "image_prompts": [<exactly {num_verses} image prompt strings, one per verse>]
}}

CRITICAL: The "verses" array MUST have exactly {num_verses} entries matching the input.
The "image_prompts" array MUST also have exactly {num_verses} entries."""

        style = ROMANCE_PAINTING_STYLE if romance else (PEOPLE_PAINTING_STYLE if include_people else None)
        result = self._generate_poetry_json(
            user_prompt, include_people, romance, _style=style, _min_verses=num_verses
        )

        if result is None:
            return None

        # ------------------------------------------------------------------ #
        # 3. Force verses back to user's original text (LLM cannot change it) #
        # ------------------------------------------------------------------ #
        result["verses"] = verse_blocks
        result["full_text"] = "\n".join(verse_blocks)

        # Pad or trim image_prompts to match verse count
        prompts = result.get("image_prompts", [])
        if len(prompts) < num_verses:
            logging.warning(f"   ⚠️  LLM returned {len(prompts)} prompts for {num_verses} verses — padding.")
            prompts += [f"Abstract painterly scene evoking: {verse_blocks[i]}" for i in range(len(prompts), num_verses)]
        elif len(prompts) > num_verses:
            prompts = prompts[:num_verses]
        result["image_prompts"] = prompts

        return result


    def _generate_poetry_json(self, user_prompt: str, include_people: bool, romance: bool = False,
                              _style: Optional[str] = None, _min_verses: Optional[int] = None) -> Optional[Dict]:
        """Internal helper to call the LLM and parse the JSON response.
        Retries up to 2 extra times if the LLM returns fewer than MIN_VERSES.
        Pass _min_verses to override the default minimum (e.g. for user-provided poems)."""
        MIN_VERSES = _min_verses if _min_verses is not None else 6
        MAX_ATTEMPTS = 3

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/poetry-automation",
            "X-Title": "Poetry Video Automation"
        }
        
        # Build system prompt dynamically
        system_prompt = POETRY_SYSTEM_PROMPT_BASE
        if include_people:
            system_prompt += HUMAN_CENTRIC_DIRECTIVE
        if romance:
            system_prompt += ROMANCE_DIRECTIVE
        system_prompt += POETRY_SYSTEM_PROMPT_FOOTER
        
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }

        for attempt in range(1, MAX_ATTEMPTS + 1):
            if attempt > 1:
                logging.info(f"🔄 Retry {attempt}/{MAX_ATTEMPTS}: requesting more verses from LLM...")
            else:
                logging.info(f"🎭 Requesting poetry processing (Human-centric: {include_people}, Romance: {romance})...")
            
            try:
                response = requests.post(BASE_URL, headers=headers, json=payload, timeout=60)
                if response.status_code != 200:
                    logging.error(f"❌ API error: {response.status_code}")
                    continue
                
                data = response.json()
                if 'choices' not in data:
                    continue

                content_str = data['choices'][0]['message']['content']
                clean_content = self._extract_json(content_str)
                if not clean_content:
                    logging.error(f"❌ No valid JSON object found in response")
                    logging.error(f"   Raw Content: {content_str[:500]}...")
                    continue
                
                try:
                    fixed_content = clean_content.strip()
                    
                    def escape_newlines(match):
                        return match.group(0).replace('\n', '\\n')
                    
                    fixed_content = re.sub(r'"(.*?)"', escape_newlines, fixed_content, flags=re.DOTALL)
                    
                    try:
                        poetry_data = json.loads(fixed_content)
                    except json.JSONDecodeError:
                        poetry_data = json.loads(clean_content.strip())
                        
                except json.JSONDecodeError as e:
                    logging.error(f"❌ JSON Decode Error: {e}")
                    logging.error(f"   Raw Content: {clean_content}")
                    continue
                
                if not self._validate_poetry_data(poetry_data):
                    logging.error("❌ Invalid poetry data structure")
                    continue

                verse_count = len(poetry_data['verses'])
                if verse_count < MIN_VERSES and attempt < MAX_ATTEMPTS:
                    logging.warning(
                        f"⚠️  LLM returned only {verse_count} verses (need {MIN_VERSES}). "
                        f"Retrying... ({attempt}/{MAX_ATTEMPTS})"
                    )
                    continue
                
                # Apply the mood-appropriate painting style to all image prompts
                active_style = _style or self.oil_painting_style
                poetry_data['styled_image_prompts'] = [
                    f"{prompt}, {active_style}"
                    for prompt in poetry_data['image_prompts']
                ]
                
                logging.info(f"✅ Processed: '{poetry_data['poem_title']}' by {poetry_data['poet']}")
                logging.info(f"📝 Verses: {verse_count}")
                if verse_count < MIN_VERSES:
                    logging.warning(f"   ⚠️  Only {verse_count} verses after {MAX_ATTEMPTS} attempts — proceeding anyway.")
                
                return poetry_data
            
            except Exception as e:
                logging.error(f"❌ Poetry processing error: {e}")
                continue

        logging.error(f"❌ Failed to get valid poetry data after {MAX_ATTEMPTS} attempts.")
        return None
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extracts the first valid JSON object by balancing braces."""
        start_idx = text.find('{')
        if start_idx == -1:
            return None
            
        brace_count = 0
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                
            if brace_count == 0:
                # Found the matching closing brace
                return text[start_idx:i+1]
                
        return None

    def _validate_poetry_data(self, data: Dict) -> bool:
        """Validate that poetry data has required fields, auto-healing verse/prompt mismatches."""
        required_fields = ['poet', 'poem_title', 'verses', 'image_prompts']
        
        if not all(field in data for field in required_fields):
            logging.error(f"❌ Missing required fields. Found: {list(data.keys())}")
            return False
        
        verses_count = len(data['verses'])
        prompts_count = len(data['image_prompts'])
        
        if verses_count != prompts_count:
            logging.warning(f"⚠️  Verse/prompt count mismatch: {verses_count} verses, {prompts_count} prompts.")
            
            if prompts_count == 0:
                logging.error("❌ No image prompts returned by LLM.")
                return False
            
            if verses_count > prompts_count:
                # Group consecutive verses to match the number of prompts
                logging.info(f"   🔧 Auto-grouping {verses_count} verses into {prompts_count} groups...")
                groups = []
                chunk_size = verses_count / prompts_count
                for i in range(prompts_count):
                    start = round(i * chunk_size)
                    end = round((i + 1) * chunk_size)
                    groups.append(" / ".join(data['verses'][start:end]))
                data['verses'] = groups
                logging.info(f"   ✅ Grouped into {len(groups)} verses.")
            else:
                # More prompts than verses — truncate prompts
                logging.info(f"   🔧 Truncating prompts to match {verses_count} verses.")
                data['image_prompts'] = data['image_prompts'][:verses_count]
        
        verses_count = len(data['verses'])
        if verses_count < 1 or verses_count > 20:
            logging.error(f"❌ Unreasonable verse count: {verses_count} (need 1-20)")
            return False
        
        return True
    
    def get_verse_count(self, poetry_data: Dict) -> int:
        """Get the number of verses in the poetry."""
        return len(poetry_data.get('verses', []))
    
    def get_full_text(self, poetry_data: Dict) -> str:
        """Get the complete poetry text for narration."""
        return poetry_data.get('full_text', '\n'.join(poetry_data.get('verses', [])))


# Example usage and testing
if __name__ == "__main__":
    engine = PoetryEngine()
    
    # Test with a topic
    test_topic = "solitude and reflection"
    result = engine.select_poetry(test_topic)
    
    if result:
        print("\n" + "="*60)
        print(f"POET: {result['poet']}")
        print(f"POEM: {result['poem_title']}")
        print("="*60)
        print("\nFULL TEXT:")
        print(result['full_text'])
        print("\n" + "="*60)
        print("\nVERSE-BY-VERSE BREAKDOWN:")
        for i, (verse, prompt) in enumerate(zip(result['verses'], result['styled_image_prompts']), 1):
            print(f"\nVERSE {i}: {verse}")
            print(f"IMAGE: {prompt[:100]}...")
        print("\n" + "="*60)
    else:
        print("❌ Failed to generate poetry")
