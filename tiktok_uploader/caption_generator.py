"""
caption_generator.py
====================
Uses OpenRouter LLM to generate a TikTok caption and hashtags
from a video's metadata JSON file.

The metadata JSON is the one produced by the content-generation pipeline
(e.g. custom_poem_20260302_021132_metadata.json).

Usage:
    from caption_generator import CaptionGenerator
    gen = CaptionGenerator()
    description, hashtags = gen.generate(metadata_dict)
"""

import os
import json
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """You are a social media expert specialising in TikTok content for poetry and art.
Your task is to write engaging TikTok captions and hashtags based on poem metadata.

Guidelines:
- The description must be SHORT (max 120 characters), evocative, and hook the viewer instantly.
- It should feel human, poetic, and emotional — NOT like a machine wrote it.
- Do NOT use generic filler phrases like "Check this out!" or "Watch now!".
- The hashtags list must contain exactly 5 to 8 highly relevant tags (no # prefix in the JSON values).
- Mix niche poetry tags with broader trending tags to maximise reach.

Output ONLY valid JSON in this exact format:
{
  "description": "your caption here",
  "hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}
"""


class CaptionGenerator:
    """
    Generates a TikTok description and hashtag list from poem metadata.
    Falls back to a sensible default if the LLM call fails.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or os.getenv("OPENROUTER_MODEL", "openrouter/auto")

        if not self.api_key:
            logger.warning(
                "⚠️  OPENROUTER_API_KEY not set — will use fallback captions."
            )

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------
    def generate(self, metadata: dict) -> tuple[str, list[str]]:
        """
        Return (description, hashtags_list) for the given metadata dict.

        Falls back to a generic caption derived from the metadata if the
        LLM call fails.
        """
        if not self.api_key:
            return self._fallback(metadata)

        try:
            return self._call_llm(metadata)
        except Exception as exc:
            logger.warning(f"⚠️  LLM caption generation failed: {exc}. Using fallback.")
            return self._fallback(metadata)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------
    def _call_llm(self, metadata: dict) -> tuple[str, list[str]]:
        """Send metadata to OpenRouter and parse the JSON response."""

        # Summarise the metadata in a compact prompt so we don't waste tokens
        poet       = metadata.get("poet", "Unknown Poet")
        title      = metadata.get("poem_title", "Untitled")
        topic      = metadata.get("topic", "")
        mood       = metadata.get("metadata", {}).get("mood", "")
        full_text  = metadata.get("full_text", "")[:400]  # cap at 400 chars

        user_prompt = f"""Poem metadata:
- Poet: {poet}
- Title: {title}
- Topic: {topic}
- Mood: {mood}
- Excerpt:
{full_text}

Generate a TikTok caption and hashtags for this poetry video."""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/poetry-automation",
            "X-Title": "Poetry TikTok Scheduler",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
        }

        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()

        content = resp.json()["choices"][0]["message"]["content"]

        # Extract JSON from the response (handle markdown code blocks)
        start = content.find("{")
        end   = content.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found in LLM response.")

        parsed = json.loads(content[start:end])
        description = parsed.get("description", "").strip()
        hashtags    = parsed.get("hashtags", [])

        # Ensure hashtags is a plain list of strings (strip any accidental '#')
        hashtags = [h.lstrip("#").strip() for h in hashtags if h]

        logger.info(f"✨ Caption generated: \"{description}\" | tags: {hashtags}")
        return description, hashtags

    def _fallback(self, metadata: dict) -> tuple[str, list[str]]:
        """Return a simple caption built from raw metadata fields."""
        poet  = metadata.get("poet", "")
        title = metadata.get("poem_title", "")
        topic = metadata.get("topic", "")

        if poet and title:
            desc = f'"{title}" by {poet}'
        elif topic:
            desc = f"A poem about {topic}"
        else:
            desc = "Poetry for the soul 🌿"

        tags = ["poetry", "poem", "fyp", "viral", "trending"]
        logger.info(f"📝 Using fallback caption: \"{desc}\"")
        return desc, tags
