import os
import json
import sys
sys.path.insert(0, os.path.dirname(__file__))

from llm_handler import LLMHandler
from dotenv import load_dotenv

load_dotenv(override=True)

CILIAN_PROFILE_ID = "66cee046-6d00-4055-9cfe-4fe9ca8637c9"
OUTPUT_CONFIG = "configs/cleopatras_beauty_filter.json"

concept = """Concept: Cleopatra's Beauty Filter
Subject: Cleopatra, the historical peak of human beauty and seduction. Commanded empires with her appearance.
Modern Habit: Experiencing severe ego-collapse and body dysmorphia while staring into an augmented-reality beauty filter that tells her her face is statistically asymmetrical.
Psychological Twist: Organic human beauty cannot compete with mathematically [weaponized] [pixels]. The screen is rewriting her biological [baseline] for self-worth."""

print("=" * 60)
print("🧠 Generating: Cleopatra's Beauty Filter")
print("=" * 60)

llm = LLMHandler()
script_json = llm.generate_script(concept)

if not script_json:
    print("❌ LLM failed. Check your API key and model.")
    sys.exit(1)

# Inject the correct Cilian profile ID
script_json["profile_id"] = CILIAN_PROFILE_ID

os.makedirs("configs", exist_ok=True)
with open(OUTPUT_CONFIG, "w", encoding="utf-8") as f:
    json.dump(script_json, f, indent=4, ensure_ascii=False)

print(f"\n✅ Config saved: {OUTPUT_CONFIG}")
print(f"   Profile ID: {CILIAN_PROFILE_ID}")
print("\n📋 Generated Script Preview:")
print(f"   Title: {script_json.get('title', 'N/A')}")
print("\n   Narrative:")
for i, line in enumerate(script_json.get("narrative_script", []), 1):
    print(f"   Scene {i}: {line[:80]}...")
