"""
Poetry Video Automation Pipeline - Main Orchestrator
====================================================

This script orchestrates the complete poetry video generation pipeline:
1. Poetry Selection: Uses LLM to select famous poetry based on topic
2. Image Generation: Creates verse-specific images with oil painting style
3. Voice Narration: Generates expressive voice-over of the poetry
4. Video Assembly: Synchronizes images with voice timing
5. Music Mixing: Overlays background music at a configurable volume level

Workflow:
Topic -> Poetry Engine -> Image Generator + Voice Engine -> Video Assembler -> Music Mixer -> Final Video

Created for automated poetry video content creation.
"""

import os
import json
import logging
import argparse
import sys
from datetime import datetime
from pathlib import Path

from poetry_engine import PoetryEngine
from image_generator import ImageGenerator, sanitize_filename
from voice_engine import VoiceEngine
from assemble_poetry_video import PoetryVideoAssembler
from assemble_silent import assemble_silent_video

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Directory Configuration
FINAL_VIDEOS_FOLDER = "final_videos"
METADATA_FOLDER = "metadata"


def main():
    """Main orchestration function."""
    parser = argparse.ArgumentParser(
        description="Poetry Video Automation - Generate artistic videos from famous poetry"
    )
    parser.add_argument(
        "--topic", 
        help="Theme/topic for poetry selection (e.g., 'solitude', 'love', 'nature')"
    )
    parser.add_argument(
        "--poem-text",
        help="Raw poem text to process (skips topic-based selection)"
    )
    parser.add_argument(
        "--poem-file",
        help="Path to a .txt file containing the poem (alternative to --poem-text, avoids shell quoting issues)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate poetry and prompts only (no images/voice/video)"
    )
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Skip image generation (for testing voice/assembly)"
    )
    parser.add_argument(
        "--skip-voice",
        action="store_true",
        help="Skip voice generation (for testing images/assembly)"
    )
    parser.add_argument(
        "--retry-images",
        action="store_true",
        help="Enable automatic retry for failed image generations"
    )
    parser.add_argument(
        "--session-name",
        help="Override the session name (useful for resuming a specific session)"
    )
    parser.add_argument(
        "--manual-json",
        help="Path to a JSON file containing manual verses and prompts (skips LLM selection)"
    )
    parser.add_argument(
        "--resolution",
        default="1080x1920",
        help="Video resolution (WIDTHxHEIGHT), default 1080x1920 (9:16 vertical)"
    )
    parser.add_argument(
        "--include-people",
        action="store_true",
        help="Include human subjects in the generated imagery (portraits, figures)"
    )
    parser.add_argument(
        "--romance",
        action="store_true",
        help="👩‍❤️‍👨 New: Enforce a super romantic and flirty aesthetic for imagery"
    )
    parser.add_argument(
        "--voice",
        default=None,
        metavar="NAME",
        help="Voice profile name to use (e.g. 'nathan' or 'morini'). Defaults to first available."
    )
    parser.add_argument(
        "--music",
        default=None,
        metavar="PATH",
        help="Path to a background music file (MP3/WAV) to mix into the final video."
    )
    parser.add_argument(
        "--music-volume",
        type=float,
        default=-10.0,
        dest="music_volume",
        metavar="DB",
        help="Background music volume in dB relative to unity (default: -10 dB)."
    )
    parser.add_argument(
        "--voice-volume",
        type=float,
        default=5.0,
        dest="voice_volume",
        metavar="DB",
        help="Voice narration volume in dB relative to unity (default: +5 dB)."
    )
    parser.add_argument(
        "--subtitles",
        action="store_true",
        default=True,
        help="Render verse subtitles centred in the frame (default: on)."
    )
    parser.add_argument(
        "--no-subtitles",
        action="store_false",
        dest="subtitles",
        help="Disable subtitle rendering."
    )
    parser.add_argument(
        "--font",
        default=None,
        dest="font_path",
        metavar="PATH",
        help="Path to a TTF font file for subtitles (auto-selected if not given)."
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=60,
        dest="font_size",
        metavar="PX",
        help="Subtitle font size in pixels (default: 60)."
    )
    parser.add_argument(
        "--drive-folder",
        default="1euAsq1h5JyAOt88VfbBZzOetCESNqPdN",
        dest="drive_folder",
        metavar="FOLDER",
        help="Google Drive folder NAME or ID to upload the final video and metadata into. "
             "Defaults to LofiYume folder."
    )
    parser.add_argument(
        "--delete-local",
        action="store_true",
        dest="delete_local",
        help="Delete local video and metadata files after a successful Drive upload. "
             "Only takes effect when --drive-folder is also set."
    )
    args = parser.parse_args()
    
    # Load poem from file if --poem-file is given (overrides --poem-text)
    if args.poem_file:
        try:
            with open(args.poem_file, 'r', encoding='utf-8') as f:
                args.poem_text = f.read()
            logging.info(f"📄 Loaded poem from file: {args.poem_file} ({len(args.poem_text)} chars)")
        except Exception as e:
            logging.error(f"❌ Could not read --poem-file '{args.poem_file}': {e}")
            sys.exit(1)

    # Validation
    if not args.topic and not args.poem_text and not args.manual_json and not args.session_name:
        logging.error("❌ You must provide either --topic, --poem-text, --manual-json, or --session-name")
        sys.exit(1)

    # Parse resolution
    try:
        width, height = map(int, args.resolution.split('x'))
    except:
        logging.error("❌ Invalid resolution format. Use WIDTHxHEIGHT (e.g., 1080x1920)")
        sys.exit(1)
    
    # Create output directories
    Path(FINAL_VIDEOS_FOLDER).mkdir(exist_ok=True)
    Path(METADATA_FOLDER).mkdir(exist_ok=True)
    
    # Generate timestamp for this session
    if args.session_name:
        session_name = args.session_name
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_source = args.topic or "custom_poem"
        topic_slug = sanitize_filename(name_source)
        session_name = f"{topic_slug}_{timestamp}"
    
    logging.info("="*70)
    logging.info("🎭 POETRY VIDEO AUTOMATION PIPELINE")
    logging.info("="*70)
    if args.topic:
        logging.info(f"📌 Topic: {args.topic}")
    if args.poem_text:
        logging.info(f"📜 Custom Poem: Provided ({len(args.poem_text)} chars)")
    logging.info(f"🕒 Session: {session_name}")
    if args.music:
        logging.info(f"🎵 Background Music: {Path(args.music).name} @ {args.music_volume:+.1f} dB")
    logging.info(f"🎤 Voice Volume: {args.voice_volume:+.1f} dB")
    logging.info(f"📝 Subtitles: {'ON' if args.subtitles else 'OFF'}"
                 + (f"  |  Font: {Path(args.font_path).name}" if args.font_path else "")
                 + f"  |  Size: {args.font_size}px")
    logging.info("="*70)
    
    # ========================================================================
    # STEP 1: POETRY SELECTION (OR MANUAL LOAD)
    # ========================================================================
    logging.info("\n" + "="*70)
    logging.info("STEP 1: POETRY SELECTION/PROCESSING")
    logging.info("="*70)
    
    poetry_engine = PoetryEngine()
    
    if args.manual_json:
        logging.info(f"📂 Loading manual verses from: {args.manual_json}")
        try:
            with open(args.manual_json, 'r', encoding='utf-8') as f:
                poetry_data = json.load(f)
            # Ensure styled prompts are present
            if 'styled_image_prompts' not in poetry_data:
                style = "early century oil painting, soft warm lighting, textured oil paint effect, muted earth tones, classical European illustration, nostalgic mood, detailed brush strokes, museum painting style"
                poetry_data['styled_image_prompts'] = [f"{p}, {style}" for p in poetry_data['image_prompts']]
        except Exception as e:
            logging.error(f"❌ Failed to load manual JSON: {e}")
            sys.exit(1)
    elif args.poem_text:
        logging.info("📝 Processing raw poem text...")
        poetry_data = poetry_engine.process_raw_poem(args.poem_text, include_people=args.include_people, romance=args.romance)
    elif args.session_name and (Path(METADATA_FOLDER) / f"{args.session_name}_metadata.json").exists():
        metadata_path = Path(METADATA_FOLDER) / f"{args.session_name}_metadata.json"
        logging.info(f"📂 Resuming existing session. Loading metadata from: {metadata_path}")
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                poetry_data = json.load(f)
        except Exception as e:
            logging.error(f"❌ Failed to load session metadata: {e}")
            sys.exit(1)
    else:
        if not args.topic:
            logging.error("❌ No topic provided and no existing session found to resume.")
            sys.exit(1)
        poetry_data = poetry_engine.select_poetry(args.topic, include_people=args.include_people, romance=args.romance)
    
    if not poetry_data:
        logging.error("❌ Failed to acquire poetry. Exiting.")
        sys.exit(1)
    
    logging.info(f"\n✅ Selected Poetry:")
    logging.info(f"   Poet: {poetry_data['poet']}")
    logging.info(f"   Poem: {poetry_data['poem_title']}")
    logging.info(f"   Verses: {len(poetry_data['verses'])}")
    full_text = poetry_data.get('full_text') or "\n".join(poetry_data.get('verses', []))
    logging.info(f"\n📜 Full Text:\n{full_text}\n")
    
    # Save metadata
    metadata_path = Path(METADATA_FOLDER) / f"{session_name}_metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(poetry_data, f, indent=2, ensure_ascii=False)
    logging.info(f"💾 Metadata saved: {metadata_path}")
    
    if args.dry_run:
        logging.info("\n🏁 Dry run complete. Exiting.")
        logging.info(f"   Review metadata at: {metadata_path}")
        return
    
    # ========================================================================
    # STEP 2: IMAGE GENERATION
    # ========================================================================
    image_paths = []
    
    if not args.skip_images:
        logging.info("\n" + "="*70)
        logging.info("STEP 2: IMAGE GENERATION")
        logging.info("="*70)
        
        image_generator = ImageGenerator()
        image_paths = image_generator.generate_images(
            poetry_data['styled_image_prompts'],
            session_name,
            base_prompts=poetry_data.get('image_prompts'),
        )
        
        # Retry failed images if enabled
        if args.retry_images:
            image_paths = image_generator.retry_failed(
                poetry_data['styled_image_prompts'],
                image_paths,
                session_name
            )
    else:
        # Discover existing images if skipping generation
        logging.info("\n⏩ Skipping image generation. Discovering existing images...")
        session_slug = sanitize_filename(session_name)
        potential_files = list(Path("outputs/images").glob(f"{session_slug}_*verse_*.jpg"))
        potential_files.sort() # Simple sort, might need more robust sorting for verse order
        
        # More robust discovery: match exactly by verse number
        image_paths = [None] * len(poetry_data['verses'])
        for i in range(1, len(poetry_data['verses']) + 1):
            # Find the latest file for this verse
            verse_files = list(Path("outputs/images").glob(f"{session_slug}_*verse_{i}*.jpg"))
            if verse_files:
                verse_files.sort(key=os.path.getmtime)
                image_paths[i-1] = str(verse_files[-1])
        
        logging.info(f"🔎 Discovered {sum(1 for p in image_paths if p)}/{len(image_paths)} images.")
        
        # Auto-retry any missing images rather than leaving them as blank frames
        missing_indices = [i for i, p in enumerate(image_paths) if p is None]
        if missing_indices:
            logging.info(f"🔄 {len(missing_indices)} image(s) missing — generating now: verses {[i+1 for i in missing_indices]}")
            image_generator = ImageGenerator()
            for idx in missing_indices:
                prompt = poetry_data['styled_image_prompts'][idx]
                logging.info(f"   🖼️  Generating missing verse {idx+1}...")
                result_paths = image_generator.generate_images([prompt], session_name)
                if result_paths and result_paths[0]:
                    image_paths[idx] = result_paths[0]
                    logging.info(f"   ✅ Verse {idx+1} image ready: {Path(result_paths[0]).name}")
                else:
                    logging.warning(f"   ⚠️  Verse {idx+1} image still failed — will be blank in video.")

    # Update metadata with image paths
    poetry_data['image_paths'] = image_paths
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(poetry_data, f, indent=2, ensure_ascii=False)
    
    successful_images = sum(1 for p in image_paths if p is not None)
    if successful_images == 0:
        logging.error("❌ No images available. Cannot proceed.")
        return
    
    logging.info(f"\n✅ Images ready: {successful_images}/{len(image_paths)}")
    
    # ========================================================================
    # STEP 3: VOICE NARRATION
    # ========================================================================
    voice_path = None
    
    if not args.skip_voice:
        logging.info("\n" + "="*70)
        logging.info("STEP 3: VOICE NARRATION")
        logging.info("="*70)
        
        try:
            voice_engine = VoiceEngine(profile_name=args.voice)
            voice_path = f"voice_{session_name}.wav"

            verses = poetry_data.get('verses', [])
            if not verses:
                logging.error("❌ No verses found in poetry data.")
                return

            def _try_split_shot(n_parts: int) -> list | None:
                """
                Split verses into n_parts equal chunks, call generate_whole()
                on each chunk separately, then merge the WAV files and
                concatenate the duration lists into one unified result.
                Returns the merged verse_durations list, or None on failure.
                """
                import math, io, wave as _wave
                chunk_size = math.ceil(len(verses) / n_parts)
                chunks = [verses[i:i + chunk_size]
                          for i in range(0, len(verses), chunk_size)]
                logging.info(f"   📦 Split into {len(chunks)} chunk(s) of "
                             f"≤{chunk_size} verse(s) each.")

                all_durations: list[float] = []
                wav_parts: list[bytes] = []

                for part_idx, chunk in enumerate(chunks, start=1):
                    tmp_path = f"{voice_path}.part{part_idx}.wav"
                    logging.info(f"   🎙️  Chunk {part_idx}/{len(chunks)}: "
                                 f"{len(chunk)} verse(s)…")
                    try:
                        durations = voice_engine.generate_whole(chunk, tmp_path)
                    except Exception as exc:
                        logging.warning(f"   ❌ Chunk {part_idx} failed: {exc}")
                        return None

                    all_durations.extend(durations)
                    with open(tmp_path, "rb") as fh:
                        wav_parts.append(fh.read())
                    import os as _os
                    try:
                        _os.remove(tmp_path)
                    except OSError:
                        pass

                # Concatenate all WAV parts into the final voice_path
                merged = voice_engine._concatenate_wav(wav_parts)
                with open(voice_path, "wb") as fh:
                    fh.write(merged)
                return all_durations

            # ----------------------------------------------------------------
            # Attempt 1 — 1-shot (entire poem)
            # ----------------------------------------------------------------
            logging.info(f"🎙️  Attempt 1/3 — single-shot ({len(verses)} verses)…")
            verse_durations = None
            try:
                verse_durations = voice_engine.generate_whole(verses, voice_path)
            except Exception as e1:
                logging.warning(f"   ⚠️  Single-shot failed: {e1}")

            # ----------------------------------------------------------------
            # Attempt 2 — 2-shot (poem split in half)
            # ----------------------------------------------------------------
            if verse_durations is None:
                logging.info(f"🔄  Attempt 2/3 — two-shot (split in 2)…")
                verse_durations = _try_split_shot(2)
                if verse_durations is None:
                    logging.warning("   ⚠️  Two-shot failed.")

            # ----------------------------------------------------------------
            # Attempt 3 — 3-shot (poem split in thirds)
            # ----------------------------------------------------------------
            if verse_durations is None:
                logging.info(f"🔄  Attempt 3/3 — three-shot (split in 3)…")
                verse_durations = _try_split_shot(3)
                if verse_durations is None:
                    logging.warning("   ⚠️  Three-shot failed.")

            # ----------------------------------------------------------------
            # Persist result or fall back to silent assembly
            # ----------------------------------------------------------------
            if verse_durations is not None:
                poetry_data['voice_path'] = voice_path
                poetry_data['verse_durations'] = verse_durations
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(poetry_data, f, indent=2, ensure_ascii=False)

                logging.info(f"✅ Voice narration complete: {voice_path}")
                for i, d in enumerate(verse_durations, 1):
                    logging.info(f"   Verse {i}: {d:.2f}s")
            else:
                logging.warning("⚠️  All voice attempts failed. "
                                "Falling back to silent video assembly.")
                voice_path = None

        except Exception as e:
            logging.error(f"❌ Voice engine initialization failed: {e}")
            logging.warning("⚠️  Falling back to silent video assembly.")
            voice_path = None
    else:
        # Discover existing voice file
        logging.info(f"\n⏩ Skipping voice generation. Discovering existing voice...")
        for ext in ("wav", "mp3"):
            candidate = f"voice_{session_name}.{ext}"
            if Path(candidate).exists():
                voice_path = candidate
                break
        else:
            voice_path = None

        if not voice_path:
            logging.warning(f"⚠️ Voice file not found. Video assembly will be skipped.")
        else:
            logging.info(f"🎙️  Voice file discovered: {voice_path}")
            poetry_data['voice_path'] = voice_path
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(poetry_data, f, indent=2, ensure_ascii=False)
    
    # ========================================================================
    # STEP 4: VIDEO ASSEMBLY
    # ========================================================================
    if successful_images > 0:
        logging.info("\n" + "="*70)
        logging.info("STEP 4: VIDEO ASSEMBLY")
        logging.info("="*70)
        
        output_video_path = Path(FINAL_VIDEOS_FOLDER) / f"{session_name}.mp4"
        
        if voice_path:
            # Standard assembly with voice synchronization
            assembler = PoetryVideoAssembler(transition_duration=0.5)
            success = assembler.assemble_video(
                image_paths,
                voice_path,
                poetry_data['verses'],
                str(output_video_path),
                (width, height),
                verse_durations=poetry_data.get('verse_durations'),
                music_path=args.music,
                music_volume_db=args.music_volume,
                voice_volume_db=args.voice_volume,
                subtitles=args.subtitles,
                font_path=args.font_path,
                font_size=args.font_size,
            )
        else:
            # Fallback to silent assembly (6 seconds per image)
            logging.info("🔇 No voice recording available. Defaulting to SILENT assembly...")
            # We use the metadata file we just saved
            success = assemble_silent_video(
                str(metadata_path),
                output_name=f"{session_name}_silent.mp4",
                resolution=(width, height),
                duration_per_image=6.0,
                music_path=args.music,
                music_volume_db=args.music_volume,
                subtitles=args.subtitles,
                font_path=args.font_path,
                font_size=args.font_size,
            )
            # Update output path based on silent naming convention
            if success:
                output_video_path = Path(FINAL_VIDEOS_FOLDER) / f"{session_name}_silent.mp4"
        
        if success:
            # Metadata is updated inside both assembly methods
            logging.info(f"\n✅ Video assembly complete!")
        else:
            logging.error(f"\n❌ Video assembly failed")
            sys.exit(1)
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    logging.info("\n" + "="*70)
    logging.info("🎉 PIPELINE COMPLETE")
    logging.info("="*70)
    logging.info(f"📜 Poetry: '{poetry_data['poem_title']}' by {poetry_data['poet']}")
    
    if not args.skip_images:
        successful_images = sum(1 for p in image_paths if p is not None)
        logging.info(f"🖼️  Images: {successful_images}/{len(image_paths)} generated")
    
    if voice_path:
        logging.info(f"🎙️  Voice: {voice_path}")
    
    if not args.skip_images and voice_path:
        logging.info(f"🎬 Final Video: {output_video_path}")
        logging.info(f"   Resolution: {width}x{height}")
    
    logging.info(f"\n📊 Session Metadata: {metadata_path}")
    logging.info("="*70)

    # ========================================================================
    # STEP 5: GOOGLE DRIVE UPLOAD  (only when --drive-folder is provided)
    # ========================================================================
    if args.drive_folder and success:
        logging.info("\n" + "="*70)
        logging.info("STEP 5: GOOGLE DRIVE UPLOAD")
        logging.info("="*70)
        try:
            from drive_uploader import DriveUploader
            uploader = DriveUploader()
            folder_id = uploader.get_or_create_folder(args.drive_folder)

            # Upload the final video
            video_url = uploader.upload_file(
                str(output_video_path), folder_id, "video/mp4"
            )
            logging.info(f"☁️  Video → {video_url}")

            # Upload the metadata JSON
            meta_url = uploader.upload_file(
                str(metadata_path), folder_id, "application/json"
            )
            logging.info(f"☁️  Metadata → {meta_url}")

            # Optionally clean up local copies
            if args.delete_local:
                uploader.delete_local(str(output_video_path))
                uploader.delete_local(str(metadata_path))
                logging.info("🗑️  Local video and metadata deleted.")

            logging.info("✅ Google Drive upload complete.")
            logging.info("="*70)

        except Exception as drive_err:
            logging.error(f"❌ Google Drive upload failed: {drive_err}")
            logging.warning("⚠️  Local files are preserved.")


if __name__ == "__main__":
    main()
