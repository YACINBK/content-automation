import asyncio
import edge_tts
import json

async def generate_audio_and_timestamps(text, output_audio="voiceover.mp3", output_json="timestamps.json"):
    # We use a deep, serious voice (perfect for the whistleblower vibe)
    voice = "en-US-ChristopherNeural"
    communicate = edge_tts.Communicate(text, voice)
    
    word_timestamps = []
    
    with open(output_audio, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
                
            # THIS is the magic. Edge-TTS tells us exactly when it says each word!
            elif chunk["type"] == "WordBoundary":
                # Convert the offset (100-nanosecond units) to seconds
                start_time = chunk["offset"] / 10000000.0
                duration = chunk["duration"] / 10000000.0
                
                word_timestamps.append({
                    "text": chunk["text"],
                    "start": start_time,
                    "end": start_time + duration
                })
                
    # Save the timestamps to a JSON file so your MoviePy caption engine can read it
    with open(output_json, "w") as json_file:
        json.dump(word_timestamps, json_file, indent=4)
        
    print(f"Audio saved to {output_audio}")
    print(f"Timestamps saved to {output_json} without using Whisper!")

# Run it
if __name__ == "__main__":
    script_text = "Your brain is hijacked by the algorithm."
    asyncio.run(generate_audio_and_timestamps(script_text))