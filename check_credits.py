from elevenlabs.client import ElevenLabs
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ELEVEN_API_KEY") or "sk_f4f4c3bb0cda05786ce265d077751e701f04e678a5149502"
client = ElevenLabs(api_key=api_key)

try:
    user = client.user.get()
    subscription = client.user.get_subscription()
    print(f"📊 ElevenLabs Credit Balance: {subscription.character_count}/{subscription.character_limit}")
    print(f"⏳ Remaining: {subscription.character_limit - subscription.character_count}")
except Exception as e:
    print(f"❌ Error fetching balance: {e}")
