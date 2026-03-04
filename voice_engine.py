# -*- coding: utf-8 -*-
"""
Voice Engine - VoiceBox Local API
==================================

Drop-in replacement for the ElevenLabs-based voice engine.
Uses the local VoiceBox REST API (http://localhost:8000) to generate speech.

Environment Variables:
  VOICEBOX_BASE_URL      API base URL (default: http://localhost:8000)
  VOICEBOX_PROFILE_ID    Voice profile ID to use (default: first available profile)
  VOICEBOX_LANGUAGE      Language code for TTS (default: en)
"""

import os
import io
import time
import wave
import logging
import textwrap
import requests
from typing import Optional

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "http://127.0.0.1:17493"
DEFAULT_LANGUAGE = "en"
MAX_CHUNK_CHARS  = 500   # VoiceBox handles long text better when chunked
MAX_RETRIES      = 3
RETRY_DELAY_SEC  = 5


class VoiceEngineError(RuntimeError):
    """Raised when voice generation fails unrecoverably."""


class VoiceEngine:
    """
    Generates speech narration using the local VoiceBox REST API.

    Public interface (same as the old ElevenLabs engine):
        engine = VoiceEngine()
        engine.generate(text: str, output_path: str) -> None
    """

    def __init__(self, profile_name: Optional[str] = None):
        self.base_url   = os.getenv("VOICEBOX_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.profile_id = os.getenv("VOICEBOX_PROFILE_ID", "")
        self.language   = os.getenv("VOICEBOX_LANGUAGE", DEFAULT_LANGUAGE)

        self._check_server()

        if profile_name:
            # Select profile by display name (e.g. "nathan", "morini")
            resolved = self._select_profile_by_name(profile_name)
            if resolved:
                self.profile_id, resolved_name = resolved
                logger.info(f"   🎤 Selected voice profile: \"{resolved_name}\" (id={self.profile_id})")
            else:
                logger.warning(
                    f"   ⚠️  Profile \'{profile_name}\' not found — falling back to auto-select."
                )
                self.profile_id = self._auto_select_profile()
        elif not self.profile_id:
            self.profile_id = self._auto_select_profile()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, text: str, output_path: str) -> None:
        """
        Generate speech for *text* and save it to *output_path*.

        For long texts the input is split into sentence-level chunks,
        each synthesised separately and then concatenated as WAV audio.
        The output file is always a valid WAV regardless of the file
        extension requested by the caller.
        """
        logger.info(f"🎙️  VoiceEngine: generating audio ({len(text)} chars) → {output_path}")

        chunks = self._split_text(text)

        if len(chunks) == 1:
            wav_bytes = self._generate_chunk(chunks[0])
        else:
            logger.info(f"   📝 Text split into {len(chunks)} chunks for generation.")
            wav_parts = [self._generate_chunk(c) for c in chunks]
            wav_bytes = self._concatenate_wav(wav_parts)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(wav_bytes)

        size_kb = len(wav_bytes) / 1024
        logger.info(f"   ✅ Saved: {output_path} ({size_kb:.1f} KB)")

    def generate_verses(self, verses: list[str], output_path: str,
                        gap_ms: int = 600) -> list[float]:
        """
        Generate speech for each verse individually, then concatenate into
        one WAV file with a short silence gap between verses.

        Returns a list of durations (in seconds) — one per verse — so the
        video assembler can map each image to the exact time slice of its
        corresponding verse narration.

        Args:
            verses:      List of verse strings to narrate.
            output_path: Where to save the final concatenated WAV.
            gap_ms:      Silence gap between verses in milliseconds (default 600 ms).

        Returns:
            List[float]: Duration in seconds for each verse's audio segment
                         (NOT including the trailing gap).
        """
        logger.info(f"🎙️  VoiceEngine: generating {len(verses)} verse(s) → {output_path}")

        verse_durations: list[float] = []
        all_parts: list[bytes] = []

        # We need sample rate / params — generate first verse to learn them
        params = None

        for i, verse in enumerate(verses):
            text = verse.strip()
            if not text:
                logger.warning(f"   ⚠️  Verse {i+1} is empty — skipping.")
                verse_durations.append(0.0)
                continue

            logger.info(f"   🗣️  Verse {i+1}/{len(verses)}: \"{text[:60]}\"")
            wav_bytes = self._generate_chunk(text)

            # Measure the audio duration
            with wave.open(io.BytesIO(wav_bytes)) as w:
                if params is None:
                    params = w.getparams()
                frames = w.getnframes()
                rate = w.getframerate()
                duration = frames / rate

            verse_durations.append(duration)
            all_parts.append(wav_bytes)

            # Append silence gap (except after the last verse)
            if i < len(verses) - 1 and params is not None:
                all_parts.append(self._make_silence(params, gap_ms))

            logger.info(f"      ⏱️  Duration: {duration:.2f}s")

        # Concatenate all parts
        final_wav = self._concatenate_wav(all_parts)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(final_wav)

        total = sum(verse_durations)
        logger.info(f"   ✅ Saved: {output_path} | total narration: {total:.2f}s")
        return verse_durations

    def generate_whole(self, verses: list[str], output_path: str) -> list[float]:
        """
        Generate speech for ALL verses in ONE single VoiceBox call, then
        estimate per-verse durations proportionally by character count.

        Produces more natural-sounding narration (no gaps/restarts).
        Returns the same interface as generate_verses() so the assembler
        can still map each image to the right time slice.

        Args:
            verses:      List of verse strings to narrate.
            output_path: Where to save the generated WAV.

        Returns:
            List[float]: Estimated duration in seconds for each verse,
                         proportional to its share of total characters.
        """
        clean_verses = [v.strip() for v in verses]
        n = len(clean_verses)

        logger.info(f"🎙️  VoiceEngine (single-shot): {n} verse(s) → {output_path}")

        # Join with newline separator for natural pacing
        full_text = "\n".join(v for v in clean_verses if v)
        logger.info(f"   📝 Full poem: {len(full_text)} chars")

        # Generate the entire poem in one call
        wav_bytes = self._generate_chunk(full_text)

        # Measure the actual total WAV duration
        with wave.open(io.BytesIO(wav_bytes)) as w:
            total_duration = w.getnframes() / w.getframerate()

        logger.info(f"   🔊 Generated: total duration = {total_duration:.2f}s")

        # Save audio file
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(wav_bytes)

        # Distribute total duration proportionally by character count
        char_counts = [len(v) for v in clean_verses]
        total_chars = sum(char_counts)

        if total_chars == 0:
            verse_durations = [total_duration / n] * n
        else:
            verse_durations = [(c / total_chars) * total_duration for c in char_counts]

        for i, (dur, verse) in enumerate(zip(verse_durations, clean_verses)):
            label = verse[:50] if verse else "(empty)"
            logger.info(f"      Verse {i+1}: {dur:.2f}s — \"{label}\"")

        logger.info(f"   ✅ Saved: {output_path} | total: {total_duration:.2f}s")
        return verse_durations



    def _check_server(self) -> None:
        """Verify VoiceBox is reachable before doing any work."""
        try:
            r = requests.get(f"{self.base_url}/health", timeout=5)
            r.raise_for_status()
            data = r.json()
            status = data.get("status", "unknown")
            model_loaded = data.get("model_loaded", False)
            logger.info(f"   ✅ VoiceBox API: {status} | model_loaded={model_loaded}")
            if not model_loaded:
                logger.warning(
                    "   ⚠️  VoiceBox model is not loaded yet. "
                    "Open the VoiceBox app and wait for the model to finish loading."
                )
        except requests.exceptions.ConnectionError:
            raise VoiceEngineError(
                f"Cannot connect to VoiceBox at {self.base_url}. "
                "Make sure VoiceBox is running."
            )
        except Exception as e:
            raise VoiceEngineError(f"VoiceBox health check failed: {e}")

    def _auto_select_profile(self) -> str:
        """Return the ID of the first available voice profile."""
        try:
            r = requests.get(f"{self.base_url}/profiles", timeout=10)
            r.raise_for_status()
            profiles = r.json()
            if not profiles:
                raise VoiceEngineError(
                    "No voice profiles found in VoiceBox. "
                    "Please create or import a voice profile in the VoiceBox app first."
                )
            profile = profiles[0]
            logger.info(f"   🎤 Auto-selected profile: \"{profile['name']}\" (id={profile['id']})")
            return profile["id"]
        except VoiceEngineError:
            raise
        except Exception as e:
            raise VoiceEngineError(f"Failed to list VoiceBox profiles: {e}")

    def _select_profile_by_name(self, name: str) -> Optional[tuple]:
        """Look up a profile by display name. Returns (id, name) or None."""
        try:
            r = requests.get(f"{self.base_url}/profiles", timeout=10)
            r.raise_for_status()
            profiles = r.json()
            name_lower = name.strip().lower()
            for p in profiles:
                if name_lower in p.get("name", "").lower():
                    return p["id"], p["name"]
            # No match found — show available names to help user
            available = ", ".join(p.get("name", "?") for p in profiles)
            logger.warning(f"   ⚠️  Voice '{name}' not found. Available: {available}")
            return None
        except VoiceEngineError:
            raise
        except Exception as e:
            logger.warning(f"   ⚠️  Could not fetch profiles: {e}")
            return None

    def _generate_chunk(self, text: str) -> bytes:
        """
        Call POST /generate then GET /audio/{id} and return raw WAV bytes.
        Retries up to MAX_RETRIES times on transient failures.
        """
        text = text.strip()
        if not text:
            return b""

        payload = {
            "profile_id": self.profile_id,
            "text":       text,
            "language":   self.language,
        }

        # Estimate a generous timeout: ~4 seconds per 10 chars, min 120 s
        estimated_timeout = max(120, len(text) // 10 * 4)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug(f"   → POST /generate (attempt {attempt}) [{text[:60]}...]")
                r = requests.post(
                    f"{self.base_url}/generate",
                    json=payload,
                    timeout=estimated_timeout,   # scales with text length
                )

                if r.status_code == 202:
                    # Model is still downloading — wait and retry
                    detail = r.json().get("detail", {})
                    msg = detail.get("message", "Model downloading…") if isinstance(detail, dict) else str(detail)
                    logger.info(f"   ⏳ {msg} (retrying in {RETRY_DELAY_SEC}s)")
                    time.sleep(RETRY_DELAY_SEC)
                    continue

                r.raise_for_status()
                generation = r.json()
                generation_id = generation.get("id")
                duration = generation.get("duration", 0)
                logger.info(f"   🔊 Generated: id={generation_id}, duration={duration:.2f}s")

                # Download the audio
                audio_r = requests.get(
                    f"{self.base_url}/audio/{generation_id}",
                    timeout=30,
                )
                audio_r.raise_for_status()
                return audio_r.content

            except VoiceEngineError:
                raise
            except requests.exceptions.Timeout:
                logger.warning(f"   ⏱️  Request timed out (attempt {attempt}/{MAX_RETRIES})")
            except requests.exceptions.HTTPError as e:
                logger.warning(f"   ❌ HTTP error (attempt {attempt}/{MAX_RETRIES}): {e}")
            except Exception as e:
                logger.warning(f"   ❌ Unexpected error (attempt {attempt}/{MAX_RETRIES}): {e}")

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SEC)

        raise VoiceEngineError(
            f"Voice generation failed after {MAX_RETRIES} attempts. "
            f"Text: \"{text[:80]}...\""
        )

    # ------------------------------------------------------------------
    # Text splitting
    # ------------------------------------------------------------------

    @staticmethod
    def _split_text(text: str) -> list[str]:
        """
        Split *text* into chunks ≤ MAX_CHUNK_CHARS on sentence boundaries.
        Preserves natural pauses in the narration.
        """
        if len(text) <= MAX_CHUNK_CHARS:
            return [text]

        # Split on sentence-ending punctuation
        import re
        sentences = re.split(r'(?<=[.!?…])\s+', text)

        chunks: list[str] = []
        current = ""
        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= MAX_CHUNK_CHARS:
                current = (current + " " + sentence).strip()
            else:
                if current:
                    chunks.append(current)
                # If a single sentence exceeds the limit, hard-wrap it
                if len(sentence) > MAX_CHUNK_CHARS:
                    for part in textwrap.wrap(sentence, MAX_CHUNK_CHARS):
                        chunks.append(part)
                    current = ""
                else:
                    current = sentence

        if current:
            chunks.append(current)

        return chunks if chunks else [text]

    # ------------------------------------------------------------------
    # WAV concatenation
    # ------------------------------------------------------------------

    @staticmethod
    def _concatenate_wav(wav_parts: list[bytes]) -> bytes:
        """
        Concatenate a list of WAV byte-strings into a single WAV byte-string.
        All parts must share the same sample rate and number of channels.
        """
        # Filter out empty parts
        wav_parts = [p for p in wav_parts if len(p) > 44]  # 44 = WAV header size
        if not wav_parts:
            return b""
        if len(wav_parts) == 1:
            return wav_parts[0]

        # Read params from first file
        with wave.open(io.BytesIO(wav_parts[0])) as w:
            params = w.getparams()

        output_buf = io.BytesIO()
        with wave.open(output_buf, "wb") as out_wav:
            out_wav.setparams(params)
            for part in wav_parts:
                with wave.open(io.BytesIO(part)) as w:
                    out_wav.writeframes(w.readframes(w.getnframes()))

        return output_buf.getvalue()

    @staticmethod
    def _make_silence(params, duration_ms: int) -> bytes:
        """
        Create a WAV byte-string containing *duration_ms* ms of silence
        matching the given wave params (channels, sampwidth, framerate).
        """
        n_frames = int(params.framerate * duration_ms / 1000)
        silent_frames = b"\x00" * n_frames * params.nchannels * params.sampwidth

        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(params.nchannels)
            w.setsampwidth(params.sampwidth)
            w.setframerate(params.framerate)
            w.writeframes(silent_frames)
        return buf.getvalue()

