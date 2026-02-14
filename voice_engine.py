"""
ElevenLabs Voice Engine
=======================

Refactored module for generating high-quality AI narration for Lofi videos.
Handles authentication, text-to-speech conversion, and file saving.
"""

import os
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

# Add FFmpeg bin folder to PATH as per user setup
os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

class VoiceEngine:
    def __init__(self, api_key=None, voice_id="JBFqnCBsd6RMkjVDRZzb"):
        """
        Initializes the ElevenLabs client.
        
        Args:
            api_key (str): ElevenLabs API Key. Defaults to env variable or hardcoded fallback.
            voice_id (str): The ID of the voice to use for narration.
        """
        self.api_key = api_key or os.getenv("ELEVEN_API_KEY") or "sk_bf4b1259cd1c6c0a2cd04c2bf1b5d22d3a6c6b9e0d37bd86"
        self.client = ElevenLabs(api_key=self.api_key)
        self.voice_id = voice_id

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
