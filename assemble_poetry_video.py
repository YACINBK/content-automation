"""
Poetry Video Assembly - Image & Voice Synchronization
=====================================================

This module handles the final video assembly:
1. Analyzes voice narration to detect verse boundaries
2. Synchronizes images with corresponding verses
3. Adds smooth transitions between images
4. Exports final video ready for social media

Uses speech-to-text analysis for precise verse timing.
"""

import os
import logging
import textwrap
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip, AudioClip, concatenate_audioclips, CompositeAudioClip
from moviepy.audio.fx import AudioFadeIn, AudioFadeOut
from moviepy.video.fx import CrossFadeIn, CrossFadeOut
import numpy as np
import json
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Default subtitle fonts — tried in order, first existing file wins
# ---------------------------------------------------------------------------
_SUBTITLE_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\OLDENGL.TTF",    # Old English Text MT  (blackletter)
    r"C:\Windows\Fonts\FRSCRIPT.TTF",   # French Script MT     (calligraphic cursive)
    r"C:\Windows\Fonts\SCRIPTBL.TTF",   # Script MT Bold       (decorative)
    r"C:\Windows\Fonts\BOOKOS.TTF",     # Book Antiqua         (classical serif)
    r"C:\Windows\Fonts\georgiai.ttf",   # Georgia Italic       (elegant fallback)
    r"C:\Windows\Fonts\timesi.ttf",     # Times New Roman Italic (safe fallback)
]


def _resolve_default_font() -> Optional[str]:
    """Return the first subtitle font candidate that actually exists on disk."""
    for path in _SUBTITLE_FONT_CANDIDATES:
        if Path(path).exists():
            return path
    return None  # PIL will use its built-in bitmap font as last resort

# Ensure FFmpeg is in the path
os.environ["PATH"] += os.pathsep + r"C:\Users\bhrga\Downloads\ffmpeg-8.0.1-essentials_build\ffmpeg-8.0.1-essentials_build\bin"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class PoetryVideoAssembler:
    """Assembles poetry videos with verse-synchronized images."""
    
    def __init__(self, transition_duration: float = 0.5):
        """
        Initialize the video assembler.
        
        Args:
            transition_duration (float): Duration of crossfade transitions in seconds
        """
        self.transition_duration = transition_duration

    # ------------------------------------------------------------------
    # Background-music helper
    # ------------------------------------------------------------------
    def add_background_music(
        self,
        voice_audio,
        music_path: str,
        video_duration: float,
        music_volume_db: float = -15.0,
        fade_duration: float = 2.0,
    ):
        """
        Mix background music with the voice narration audio.

        The music track is looped to cover the full video, attenuated by
        *music_volume_db* decibels (negative = quieter), and faded in/out
        over *fade_duration* seconds.  The result is a CompositeAudioClip
        that retains the full clarity of the narration while adding an
        ambient musical backdrop.

        Args:
            voice_audio:      Existing AudioFileClip / CompositeAudioClip with narration.
            music_path (str): Path to the background music file (MP3 or WAV).
            video_duration (float): Total video duration in seconds.
            music_volume_db (float): Volume adjustment in dB (default -15 dB ≈ 18 % of full volume).
            fade_duration (float):  Fade-in and fade-out duration in seconds.

        Returns:
            CompositeAudioClip: Merged narration + music audio.
        """
        logging.info(f"🎵 Adding background music: {Path(music_path).name}")
        logging.info(f"   Volume: {music_volume_db:+.1f} dB  |  Fade: {fade_duration:.1f}s in/out")

        # Linear scale factor:  factor = 10^(dB/20)
        volume_factor = 10 ** (music_volume_db / 20.0)
        logging.info(f"   Linear scale factor: {volume_factor:.4f}")

        try:
            music_clip = AudioFileClip(music_path)

            # Loop to fill the full video duration
            if music_clip.duration < video_duration:
                music_clip = music_clip.with_end(video_duration).audio_loop(
                    duration=video_duration
                )
            else:
                music_clip = music_clip.with_end(video_duration)

            # Apply volume attenuation
            music_clip = music_clip.with_volume_scaled(volume_factor)

            # Fade in at the beginning, fade out at the end
            music_clip = music_clip.with_effects([
                AudioFadeIn(fade_duration),
                AudioFadeOut(fade_duration),
            ])

            # Composite: narration stays on top, music sits underneath
            combined = CompositeAudioClip([voice_audio, music_clip])
            logging.info("   ✅ Background music mixed successfully.")
            return combined

        except Exception as e:
            logging.warning(f"   ⚠️  Background music mixing failed: {e} — continuing without music.")
            return voice_audio

    # ------------------------------------------------------------------
    # Subtitle helpers
    # ------------------------------------------------------------------
    @staticmethod
    def render_subtitle_clip(
        text: str,
        resolution: Tuple[int, int],
        start_time: float,
        duration: float,
        font_path: Optional[str] = None,
        font_size: int = 60,
        text_color: Tuple[int, int, int, int] = (255, 255, 255, 245),
        stroke_color: Tuple[int, int, int, int] = (0, 0, 0, 180),
        stroke_width: int = 3,
        max_width_ratio: float = 0.80,
    ) -> ImageClip:
        """
        Render a single verse subtitle as a transparent RGBA overlay.

        The text is word-wrapped to *max_width_ratio* of the frame width,
        drawn with a dark stroke for legibility, and positioned at the
        vertical and horizontal centre of the frame.

        Args:
            text (str): Verse text to display.
            resolution (Tuple[int, int]): (width, height) of the video.
            start_time (float): When the clip starts in the final video.
            duration (float): How long the subtitle is visible.
            font_path (Optional[str]): Path to a TTF/OTF file. Falls back to
                _resolve_default_font() if None.
            font_size (int): Font size in pixels.
            text_color: RGBA fill colour for the text.
            stroke_color: RGBA colour of the text outline.
            stroke_width (int): Pixel width of the outline.
            max_width_ratio (float): Fraction of frame width used for line wrapping.

        Returns:
            ImageClip: A transparent clip positioned at the verse timing.
        """
        width, height = resolution
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # --- Load font ---
        resolved_font = font_path or _resolve_default_font()
        try:
            if resolved_font:
                font = ImageFont.truetype(resolved_font, font_size)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        # --- Word-wrap text ---
        max_chars_per_line = max(10, int(max_width_ratio * width / (font_size * 0.55)))
        wrapped = textwrap.fill(text, width=max_chars_per_line)
        lines = wrapped.splitlines()

        # --- Measure bounding box ---
        line_heights = []
        line_widths = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_widths.append(bbox[2] - bbox[0])
            line_heights.append(bbox[3] - bbox[1])

        line_spacing = int(font_size * 0.25)
        total_text_height = sum(line_heights) + line_spacing * (len(lines) - 1)
        max_line_width = max(line_widths) if line_widths else 0

        # --- Starting Y: vertically centred ---
        y_start = (height - total_text_height) // 2

        # --- Draw each line ---
        y = y_start
        for i, line in enumerate(lines):
            x = (width - line_widths[i]) // 2  # horizontally centred

            # Draw stroke (outline) by offsetting in 8 directions
            for dx in range(-stroke_width, stroke_width + 1):
                for dy in range(-stroke_width, stroke_width + 1):
                    if dx == 0 and dy == 0:
                        continue
                    draw.text((x + dx, y + dy), line, font=font, fill=stroke_color)

            # Draw main text
            draw.text((x, y), line, font=font, fill=text_color)
            y += line_heights[i] + line_spacing

        # --- Convert to numpy and create clip ---
        frame = np.array(img)  # shape (H, W, 4) RGBA
        clip = (ImageClip(frame, duration=duration)
                .with_start(start_time))
        return clip

    def add_subtitles(
        self,
        verses: List[str],
        timings: List[Tuple[float, float]],
        resolution: Tuple[int, int],
        font_path: Optional[str] = None,
        font_size: int = 60,
    ) -> List[ImageClip]:
        """
        Build a list of subtitle ImageClips, one per verse.

        Args:
            verses (List[str]): Verse texts in order.
            timings (List[Tuple[float, float]]): (start, end) seconds per verse.
            resolution (Tuple[int, int]): Video (width, height).
            font_path (Optional[str]): TTF path override.
            font_size (int): Font size in pixels.

        Returns:
            List[ImageClip]: Transparent subtitle clips ready to composite.
        """
        logging.info(f"📝 Adding subtitles ({len(verses)} verses)...")
        resolved = font_path or _resolve_default_font()
        if resolved:
            logging.info(f"   Font: {Path(resolved).name}  |  Size: {font_size}px")
        else:
            logging.warning("   No TTF font found — using PIL bitmap fallback.")

        subtitle_clips = []
        for i, (verse, (start, end)) in enumerate(zip(verses, timings)):
            duration = end - start
            if duration <= 0:
                continue
            clip = self.render_subtitle_clip(
                text=verse,
                resolution=resolution,
                start_time=start,
                duration=duration,
                font_path=resolved,
                font_size=font_size,
            )
            subtitle_clips.append(clip)
            logging.info(f"   Verse {i+1}: {start:.2f}s – {end:.2f}s ({duration:.2f}s)")

        logging.info(f"   ✅ {len(subtitle_clips)} subtitle clip(s) ready.")
        return subtitle_clips
    
    def calculate_verse_timings(self, audio_path: str, verses: List[str], 
                                total_duration: float,
                                verse_durations: Optional[List[float]] = None) -> List[Tuple[float, float]]:
        """
        Calculate timing for each verse.

        If *verse_durations* is provided (per-verse seconds from VoiceEngine.generate_verses),
        those exact values are used — no estimation needed.
        Otherwise, timing is proportionally estimated from character counts.

        Args:
            audio_path (str): Path to the narration audio file
            verses (List[str]): List of verse texts
            total_duration (float): Total duration of the audio in seconds
            verse_durations (Optional[List[float]]): Exact per-verse durations in seconds

        Returns:
            List[Tuple[float, float]]: List of (start_time, end_time) for each verse
        """
        logging.info("📊 Calculating verse timings...")

        if verse_durations and len(verse_durations) == len(verses):
            logging.info("   ✅ Using exact per-verse durations from voice engine.")
            timings = []
            current_time = 0.0
            for i, dur in enumerate(verse_durations):
                # Each image holds for the verse duration PLUS half the gap on each side
                # (gap_ms in generate_verses is 600ms → add 0.3s padding per verse)
                padded = dur + 0.3
                timings.append((current_time, current_time + padded))
                current_time += padded
                logging.info(f"  Verse {i+1}: {timings[-1][0]:.2f}s - {timings[-1][1]:.2f}s ({padded:.2f}s)")

            # Stretch last clip to fill total audio duration
            if timings and timings[-1][1] < total_duration:
                last = timings[-1]
                timings[-1] = (last[0], total_duration)
            return timings

        # --- Fallback: proportional estimation from character counts ---
        logging.info("   ⚠️  No per-verse durations — estimating from character counts.")
        char_counts = [len(verse) for verse in verses]
        total_chars = sum(char_counts)
        
        timings = []
        current_time = 0.0
        
        for i, char_count in enumerate(char_counts):
            verse_duration = (char_count / total_chars) * total_duration
            verse_duration = max(verse_duration, 2.0)
            
            start_time = current_time
            end_time = current_time + verse_duration
            
            timings.append((start_time, end_time))
            current_time = end_time
            
            logging.info(f"  Verse {i+1}: {start_time:.2f}s - {end_time:.2f}s ({verse_duration:.2f}s)")
        
        if current_time > total_duration:
            scale_factor = total_duration / current_time
            timings = [(start * scale_factor, end * scale_factor) for start, end in timings]
            logging.info(f"  ⚖️  Normalized timings to fit {total_duration:.2f}s")
        
        return timings
    
    def create_image_clip_with_transitions(self, image_path: str, duration: float,
                                           start_time: float, is_first: bool = False,
                                           is_last: bool = False) -> ImageClip:
        """
        Create an image clip with fade transitions.
        
        Args:
            image_path (str): Path to the image file
            duration (float): Duration to display the image
            start_time (float): When this clip starts in the final video
            is_first (bool): Whether this is the first clip (fade in)
            is_last (bool): Whether this is the last clip (fade out)
            
        Returns:
            ImageClip: Configured image clip
        """
        clip = ImageClip(image_path, duration=duration)
        
        # Add fade in for first clip
        if is_first:
            clip = clip.with_effects([CrossFadeIn(self.transition_duration)])
        
        # Add fade out for last clip
        if is_last:
            clip = clip.with_effects([CrossFadeOut(self.transition_duration)])
        
        # Set start time
        clip = clip.with_start(start_time)
        
        return clip
    
    def assemble_video(self, image_paths: List[str], audio_path: str,
                      verses: List[str], output_path: str,
                      resolution: Tuple[int, int] = (1080, 1920),
                      verse_durations: Optional[List[float]] = None,
                      music_path: Optional[str] = None,
                      music_volume_db: float = -10.0,
                      voice_volume_db: float = 5.0,
                      subtitles: bool = True,
                      font_path: Optional[str] = None,
                      font_size: int = 60) -> bool:
        """
        Assemble the final poetry video.

        Args:
            image_paths (List[str]): Paths to verse images (in order)
            audio_path (str): Path to narration audio
            verses (List[str]): List of verse texts (for timing calculation)
            output_path (str): Where to save the final video
            resolution (Tuple[int, int]): Video resolution (width, height) - default is vertical 9:16
            verse_durations (Optional[List[float]]): Exact per-verse durations in seconds
                from VoiceEngine.generate_verses(). When provided, timing is exact.
            music_path (Optional[str]): Path to background music file. If None, no music is added.
            music_volume_db (float): Background music volume in dB relative to unity (default -10 dB).
            voice_volume_db (float): Voice narration volume in dB relative to unity (default +5 dB).
            subtitles (bool): Whether to render verse subtitles (default True).
            font_path (Optional[str]): Path to a TTF font file for subtitles (auto-selected if None).
            font_size (int): Subtitle font size in pixels (default 60).

        Returns:
            bool: True if successful, False otherwise
        """
        logging.info("🎬 Starting video assembly...")
        logging.info(f"  Images: {len(image_paths)}")
        logging.info(f"  Audio: {audio_path}")
        logging.info(f"  Output: {output_path}")
        
        try:
            # Filter out None values (failed image generations)
            valid_images = [(i, path) for i, path in enumerate(image_paths) if path is not None]
            
            if not valid_images:
                logging.error("❌ No valid images to assemble")
                return False
            
            if len(valid_images) < len(image_paths):
                logging.warning(f"⚠️  Only {len(valid_images)}/{len(image_paths)} images available")
            
            # Load audio to get duration
            audio = AudioFileClip(audio_path)

            # --- ADD TAIL SLATE ---
            # We add 1.0s of silence to the end so the last image stays on screen
            # for a moment after the voice finishes.
            tail_duration = 1.0
            n_ch = audio.nchannels
            silent_tail = AudioClip(
                frame_function=lambda t: np.zeros(n_ch),
                duration=tail_duration,
                fps=audio.fps,
            )
            audio = concatenate_audioclips([audio, silent_tail])
            
            total_duration = audio.duration
            logging.info(f"  Total duration (with tail): {total_duration:.2f}s")

            # Apply voice volume boost
            if voice_volume_db != 0.0:
                voice_factor = 10 ** (voice_volume_db / 20.0)
                logging.info(f"  🎤 Voice volume: {voice_volume_db:+.1f} dB (factor {voice_factor:.4f})")
                audio = audio.with_volume_scaled(voice_factor)
            
            # Calculate verse timings (exact if verse_durations provided, estimated otherwise)
            timings = self.calculate_verse_timings(
                audio_path, verses, total_duration, verse_durations
            )
            
            # Create image clips with transitions, filling gaps for missing images
            clips = []
            
            # Map each verse index to a valid image path (reuse previous if missing)
            verse_to_image = {}
            last_valid_path = None
            
            # First pass: find a valid path to use as a starting point (in case first is missing)
            first_valid_path = None
            for path in image_paths:
                if path and Path(path).exists():
                    first_valid_path = path
                    break
            
            if not first_valid_path:
                logging.error("❌ No valid images found on disk to assemble")
                return False

            last_valid_path = first_valid_path
            for i, path in enumerate(image_paths):
                if path and Path(path).exists():
                    verse_to_image[i] = path
                    last_valid_path = path
                else:
                    if i > 0:
                        logging.warning(f"⚠️  Verse {i+1} missing image — reusing image from Verse {i}")
                    else:
                        logging.warning(f"⚠️  Verse {i+1} missing image — using first available image")
                    verse_to_image[i] = last_valid_path

            # Second pass: create the clips
            for i in range(len(verses)):
                start_time, end_time = timings[i]
                duration = end_time - start_time
                image_path = verse_to_image[i]

                is_first = (i == 0)
                is_last = (i == len(verses) - 1)

                logging.info(f"  Creating clip {i+1}: {Path(image_path).name} ({duration:.2f}s)")

                clip = self.create_image_clip_with_transitions(
                    image_path, duration, start_time, is_first, is_last
                )

                # Resize to target resolution
                clip = clip.resized(resolution)
                clips.append(clip)

            # ---- STEP 5 (part A): Subtitle Overlays ----
            if subtitles:
                logging.info("\n" + "="*60)
                logging.info("STEP 5 (A): SUBTITLE OVERLAYS")
                logging.info("="*60)
                try:
                    subtitle_clips = self.add_subtitles(
                        verses, timings, resolution,
                        font_path=font_path,
                        font_size=font_size,
                    )
                    clips.extend(subtitle_clips)
                except Exception as e:
                    logging.warning(f"   ⚠️  Subtitle rendering failed: {e} — continuing without subtitles.")

            # Composite all clips (images + subtitles)
            logging.info("  Compositing video clips...")
            final_video = CompositeVideoClip(clips, size=resolution)
            
            # Set final duration
            output_duration = total_duration
            
            # (Optional) Social media platforms sometimes prefer 5s+ videos
            MIN_ABS_DURATION = 5.0
            if output_duration < MIN_ABS_DURATION:
                pad_seconds = MIN_ABS_DURATION - output_duration
                logging.info(f"  ⏱️  Video too short — padding with {pad_seconds:.1f}s to reach {MIN_ABS_DURATION}s.")
                n_ch = audio.nchannels
                silent = AudioClip(
                    frame_function=lambda t: np.zeros(n_ch),
                    duration=pad_seconds,
                    fps=audio.fps,
                )
                audio = concatenate_audioclips([audio, silent])
                output_duration = MIN_ABS_DURATION

            # ---- STEP 5: Background Music Mixing ----
            if music_path:
                logging.info("\n" + "="*60)
                logging.info("STEP 5: BACKGROUND MUSIC MIXING")
                logging.info("="*60)
                audio = self.add_background_music(
                    audio,
                    music_path,
                    output_duration,
                    music_volume_db=music_volume_db,
                )

            final_video = final_video.with_audio(audio)
            final_video = final_video.with_duration(output_duration)
            
            # Export
            logging.info(f"  Exporting to {output_path}...")
            final_video.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                fps=30,
                preset="medium",
                bitrate="5000k"
            )
            
            logging.info(f"✅ Video assembly complete: {output_path}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Video assembly failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Test the video assembler."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Assemble poetry video from images and audio")
    parser.add_argument("--images", nargs='+', required=True, help="Paths to verse images")
    parser.add_argument("--audio", required=True, help="Path to narration audio")
    parser.add_argument("--verses", nargs='+', required=True, help="Verse texts for timing")
    parser.add_argument("--output", default="poetry_video.mp4", help="Output video path")
    parser.add_argument("--width", type=int, default=1080, help="Video width")
    parser.add_argument("--height", type=int, default=1920, help="Video height (9:16 for vertical)")
    
    args = parser.parse_args()
    
    assembler = PoetryVideoAssembler()
    success = assembler.assemble_video(
        args.images,
        args.audio,
        args.verses,
        args.output,
        (args.width, args.height)
    )
    
    if success:
        print(f"\n🎉 Success! Video saved to: {args.output}")
    else:
        print(f"\n❌ Failed to create video")


if __name__ == "__main__":
    main()
