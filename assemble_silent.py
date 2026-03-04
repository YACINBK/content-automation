import json
import logging
import argparse
import os
from pathlib import Path
from moviepy import ImageClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip, CompositeVideoClip
from moviepy.audio.fx import AudioFadeIn, AudioFadeOut
from moviepy.video.fx import CrossFadeIn, CrossFadeOut
from assemble_poetry_video import PoetryVideoAssembler, _resolve_default_font

# Ensure FFmpeg is in the path
os.environ["PATH"] += os.pathsep + r"C:\Users\bhrga\Downloads\ffmpeg-8.0.1-essentials_build\ffmpeg-8.0.1-essentials_build\bin"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def assemble_silent_video(
    metadata_path,
    output_name=None,
    resolution=(1080, 1920),
    duration_per_image=6.0,
    music_path=None,
    music_volume_db=-15.0,
    subtitles=True,
    font_path=None,
    font_size=60,
    drive_folder="1euAsq1h5JyAOt88VfbBZzOetCESNqPdN",
    delete_local=False,
):
    logging.info(f"🎬 Assembling SILENT video from: {metadata_path}")
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    image_paths = data.get('image_paths', [])
    if not image_paths:
        logging.error("❌ No image paths found in metadata.")
        return False
        
    clips = []
    transition_duration = 0.5
    
    for i, img_path in enumerate(image_paths):
        if not img_path or not Path(img_path).exists():
            logging.warning(f"⚠️ Image not found: {img_path}")
            continue
            
        logging.info(f"  Adding clip {i+1}: {img_path}")
        clip = ImageClip(img_path, duration=duration_per_image)
        
        # Add transitions
        if i == 0:
            clip = clip.with_effects([CrossFadeIn(transition_duration)])
        if i == len(image_paths) - 1:
            clip = clip.with_effects([CrossFadeOut(transition_duration)])
            
        clip = clip.resized(resolution)
        clips.append(clip)
    
    if not clips:
        logging.error("❌ No valid clips to assemble.")
        return False

    # ---- Subtitle Overlays (optional) ----
    if subtitles:
        verses = data.get('verses', [])
        if verses:
            logging.info("📝 Adding subtitles to silent video...")
            # Build per-image timings from duration_per_image
            valid_image_count = len(clips)
            timings = [
                (i * duration_per_image, (i + 1) * duration_per_image)
                for i in range(min(len(verses), valid_image_count))
            ]
            assembler = PoetryVideoAssembler()
            try:
                subtitle_clips = assembler.add_subtitles(
                    verses[:len(timings)], timings, resolution,
                    font_path=font_path, font_size=font_size,
                )
                # Composite images + subtitles together
                all_clips = concatenate_videoclips(clips, method="compose")
                from moviepy import CompositeVideoClip
                final_video = CompositeVideoClip(
                    [all_clips] + subtitle_clips, size=resolution
                )
            except Exception as e:
                logging.warning(f"   ⚠️  Subtitle rendering failed: {e} — continuing without subtitles.")
                final_video = concatenate_videoclips(clips, method="compose")
        else:
            final_video = concatenate_videoclips(clips, method="compose")
    else:
        final_video = concatenate_videoclips(clips, method="compose")

    # ---- Background Music Mixing (optional) ----
    if music_path:
        logging.info(f"🎵 Adding background music: {Path(music_path).name}")
        volume_factor = 10 ** (music_volume_db / 20.0)
        logging.info(f"   Volume: {music_volume_db:+.1f} dB  (factor {volume_factor:.4f})")
        try:
            video_duration = final_video.duration
            music_clip = AudioFileClip(music_path)

            if music_clip.duration < video_duration:
                music_clip = music_clip.with_end(video_duration).audio_loop(duration=video_duration)
            else:
                music_clip = music_clip.with_end(video_duration)

            music_clip = music_clip.with_volume_scaled(volume_factor)
            music_clip = music_clip.with_effects([
                AudioFadeIn(2.0),
                AudioFadeOut(2.0),
            ])

            final_video = final_video.with_audio(music_clip)
            logging.info("   ✅ Background music attached to silent video.")
        except Exception as e:
            logging.warning(f"   ⚠️  Music mixing failed: {e} — exporting without music.")

    # Determine output path
    if not output_name:
        output_name = Path(metadata_path).stem.replace("_metadata", "") + "_silent.mp4"
    
    output_dir = Path("final_videos")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / output_name
    
    logging.info(f"  Exporting to {output_path}...")
    final_video.write_videofile(
        str(output_path),
        codec="libx264",
        fps=30,
        preset="medium",
        bitrate="5000k"
    )
    
    logging.info(f"✅ Silent video complete: {output_path}")
    
    # Update metadata
    data['final_video'] = str(output_path)
    data['voice_path'] = None
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    # ---- Google Drive Upload (optional) ----
    if drive_folder:
        logging.info("\n" + "="*70)
        logging.info("☁️  UPLOADING SILENT VIDEO TO DRIVE")
        logging.info("="*70)
        try:
            from drive_uploader import DriveUploader
            uploader = DriveUploader()
            folder_id = uploader.get_or_create_folder(drive_folder)

            # Upload the final video
            video_url = uploader.upload_file(
                str(output_path), folder_id, "video/mp4"
            )
            logging.info(f"☁️  Video → {video_url}")

            # Upload the metadata JSON
            meta_url = uploader.upload_file(
                str(metadata_path), folder_id, "application/json"
            )
            logging.info(f"☁️  Metadata → {meta_url}")

            # Optionally clean up local copies
            if delete_local:
                uploader.delete_local(str(output_path))
                uploader.delete_local(str(metadata_path))
                logging.info("🗑️  Local silent video and metadata deleted.")

            logging.info("✅ Google Drive upload complete.")
            logging.info("="*70)

        except Exception as drive_err:
            logging.error(f"❌ Google Drive upload failed: {drive_err}")
            logging.warning("⚠️  Local files are preserved.")

    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assemble a silent poetry video from metadata")
    parser.add_argument("--metadata", required=True, help="Path to the metadata JSON file")
    parser.add_argument("--output", help="Custom name for the output mp4 file")
    parser.add_argument("--duration", type=float, default=6.0, help="Duration per image")
    parser.add_argument("--music", default=None, help="Path to background music file")
    parser.add_argument("--music-volume", type=float, default=-15.0,
                        dest="music_volume", help="Music volume in dB (default -15)")
    parser.add_argument("--subtitles", action="store_true", default=True,
                        help="Render verse subtitles (default: on)")
    parser.add_argument("--no-subtitles", action="store_false", dest="subtitles",
                        help="Disable subtitle rendering")
    parser.add_argument("--font", default=None, dest="font_path",
                        help="Path to a TTF font file for subtitles")
    parser.add_argument("--font-size", type=int, default=60, dest="font_size",
                        help="Subtitle font size in pixels (default 60)")
    parser.add_argument("--drive-folder", default="1euAsq1h5JyAOt88VfbBZzOetCESNqPdN", dest="drive_folder",
                        help="Google Drive folder NAME or ID to upload results (default: LofiYume)")
    parser.add_argument("--delete-local", action="store_true", dest="delete_local",
                        help="Delete local files after successful upload")

    args = parser.parse_args()
    assemble_silent_video(
        args.metadata,
        args.output,
        duration_per_image=args.duration,
        music_path=args.music,
        music_volume_db=args.music_volume,
        subtitles=args.subtitles,
        font_path=args.font_path,
        font_size=args.font_size,
        drive_folder=args.drive_folder,
        delete_local=args.delete_local,
    )
