import math
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx

video_path = "a_symmetrical_2d_anime_scene_of_a_neon-lit_tokyo_s_20260212_231132_1.mp4"
music_path = "lo-fi-chillhop-track-70-bpm-minor-key.moody-rainy-night-in-a-neon-lit-city-reflective-and-slightly-melancholic.start-instantly-with-a-warm-detuned-piano-chord-and-a-simple-34-note-motif-with-soft-vinyl-crackle-and-.mp3"
out_path   = "result.mp4"

# Load music
music = AudioFileClip(music_path)
target_dur = music.duration

# Load short video
clip = VideoFileClip(video_path)

# Calculate repetitions needed
n = math.ceil(target_dur / clip.duration)

segments = []

for i in range(n):
    if i % 2 == 0:
        segment = clip
    else:
        segment = clip.with_effects([vfx.TimeMirror()])  # reverse

    segments.append(segment)

# Concatenate and trim to exact music duration
looped = concatenate_videoclips(segments, method="chain").subclipped(0, target_dur)

# Attach full music
final = looped.with_audio(music)

# Export
final.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=clip.fps)
