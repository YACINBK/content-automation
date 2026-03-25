import os
from llm_handler import LLMHandler
from dotenv import load_dotenv

load_dotenv(override=True)

llm = LLMHandler()
# Use the verified working model
llm.MODEL_NAME = "stepfun/step-3.5-flash:free" 

print(f"Testing FULL script generation with {llm.MODEL_NAME}...")
prompt = "Spartan warrior scrolling TikTok"

try:
    # This calls _call_llm with the massive system prompt
    res = llm.generate_script(prompt)
    if res:
        print("✅ SUCCESS! Script generated.")
        import json
        print(json.dumps(res, indent=2))
    else:
        print("❌ FAILED: Received None from LLM.")
except Exception as e:
    print(f"❌ ERROR: {e}")
