import os
from pydub import AudioSegment
from pydub.effects import high_pass_filter, normalize, compress_dynamic_range
from audio_fx_engine import process_audio

os.environ["VOICE_FILTER"] = "brutalist"
os.environ["FFMPEG_PATH"] = r"C:\ffmpeg\bin\ffmpeg.exe"
print("Testing process_audio...")
out_path = process_audio("./niches/architect_of_mind/niche_output/production_the_dopamine_fast_how_2026_algorithmic_infinite_scrolling_drains_your_agency_and_the_stoic_mental_firewall_required_to_reclaim_your_focus/audio_00.wav")
print("Done. Check size:", out_path)
import os as os2
print("Size:", os2.path.getsize(out_path))
