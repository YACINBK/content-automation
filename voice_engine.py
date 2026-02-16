"""
ElevenLabs Voice Engine
=======================

Refactored module for generating high-quality AI narration for Lofi videos.
Handles authentication, text-to-speech conversion, and file saving.
"""

import os
import logging
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

# Add FFmpeg bin folder to PATH as per user setup
os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

# Curated Voice Mapping for Lofi Aesthetics
VOICE_MAP = {
    "george": "JBFqnCBsd6RMkjVDRZzb",  # Global default: Calm & Wise
    "adam": "pNInz6obpgUEW0qIEpYj",    # Deep, Resonant & Motivational
    "hope": "qC4fB4o5k50Y10u8u9u9",    # Soft, Poetic & Romantic
    "milo": "rb2T1Cqj6V1pVl7AEP9c",    # Meditative & Soothing
    "amara": "t0vP9HB4E9qS3AgYm9vV",   # Elegant & Soft Storytelling
    "guardian": "7N6rI70mHj0zhj8KDbyt" # NEW: Slow, Protective & Wise
}

class VoiceEngine:
    def __init__(self, api_key=None, voice_name_or_id="george"):
        """
        Initializes the ElevenLabs client.
        
        Args:
            api_key (str): ElevenLabs API Key.
            voice_name_or_id (str): A friendly name from VOICE_MAP (e.g., 'adam') or a raw ElevenLabs ID.
        """
        self.api_key = api_key or os.getenv("ELEVEN_API_KEY") or "sk_bf4b1259cd1c6c0a2cd04c2bf1b5d22d3a6c6b9e0d37bd86"
        self.client = ElevenLabs(api_key=self.api_key)
        
        # Resolve voice name to ID if it exists in the map, otherwise assume it's a raw ID
        clean_name = voice_name_or_id.lower().strip()
        self.voice_id = VOICE_MAP.get(clean_name, voice_name_or_id)
        
        if self.voice_id in VOICE_MAP.values():
            logging.info(f"🎙️ Voice Engine initialized with profile: {clean_name.capitalize()}")
        else:
            logging.info(f"🎙️ Voice Engine initialized with custom ID: {self.voice_id}")

    def generate(self, text, output_path, speed=0.8, stability=0.7, similarity=0.75):
        """
        Converts text to speech with optimized Lofi delivery settings.
        
        Args:
            text (str): The viral narration pitch.
            output_path (str): Where to save the resulting .mp3 file.
            speed (float): Speaking speed. 0.7 to 1.2. Default 0.8 (Slightly slower).
            stability (float): Emotional stability. Default 0.7 (Steady/Wise).
            similarity (float): Brand similarity. Default 0.75.
            
        Returns:
            str: Path to the generated audio file.
        """
        print(f"🎙️ Generating voice narration (Speed: {speed}, Stability: {stability}): \"{text[:50]}...\"")
        
        try:
            # Trigger conversion with custom settings
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
                voice_settings=VoiceSettings(
                    stability=stability,
                    similarity_boost=similarity,
                    style=0.0,
                    use_speaker_boost=True,
                    speed=speed
                )
            )
            
            # Save the generator content to a file
            with open(output_path, "wb") as f:
                for chunk in audio_generator:
                    if chunk:
                        f.write(chunk)
            
            print(f"✅ Voice-over saved to: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ Voice Generation Error: {e}")
            raise e

# Example usage for testing
if __name__ == "__main__":
    engine = VoiceEngine()
    engine.generate("This is a test of the viral lofi narration engine.", "test_voice.mp3")
