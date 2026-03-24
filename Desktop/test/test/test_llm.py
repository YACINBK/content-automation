import json
from llm_handler import LLMHandler

llm = LLMHandler()
prompt = "Spartan warrior scrolling TikTok"
res = llm.generate_concept(prompt)

if isinstance(res, str):
    print("WARNING: Returned raw string instead of dict")
    print(res)
else:
    print(json.dumps(res, indent=2))
