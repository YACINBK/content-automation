import os
import json
import re
import time
from llm_handler import LLMHandler

CONFIGS_DIR = "configs"
CONCEPTS_FILE = "concepts.txt"

def sanitize_filename(concept_text):
    """Extracts the 'Concept X: Title' line to create a safe project name."""
    first_line = concept_text.split('\n')[0]
    # Remove "Concept X:"
    title = re.sub(r'(?i)concept\s*\d+:\s*', '', first_line)
    words = title.split()[:5]
    short_name = "_".join(words).lower()
    safe_name = re.sub(r'[^a-z0-9_]', '', short_name)
    return safe_name

def read_concepts():
    if not os.path.exists(CONCEPTS_FILE):
        return []
        
    with open(CONCEPTS_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by double newline or the *** delimiter
    raw_blocks = re.split(r'\n\s*\n|\*\*\*', content)
    
    # Filter out empty blocks and clean up whitespace
    concepts = [block.strip() for block in raw_blocks if len(block.strip()) > 10]
    return concepts

def generate_batches():
    print("=" * 60)
    print("🧠 DARK PRODUCTIVITY — BATCH CONCEPT GENERATOR")
    print("=" * 60)

    os.makedirs(CONFIGS_DIR, exist_ok=True)
    concepts = read_concepts()

    if not concepts:
        print("ℹ️ No concepts found in concepts.txt.")
        return

    llm = LLMHandler()
    print(f"📂 Found {len(concepts)} concept(s) to process.\n")

    for concept in concepts:
        safe_name = sanitize_filename(concept)
        output_file = os.path.join(CONFIGS_DIR, f"{safe_name}.json")
        
        if os.path.exists(output_file):
            print(f"   ⏩ Skipping '{safe_name}' (already exists).")
            continue
            
        print(f"   🤖 Generating script for: {concept}...")
        try:
            script_json = llm.generate_script(concept)
            
            if not script_json:
                print(f"   ❌ LLM failed to return valid JSON for: {concept}")
                continue
                
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(script_json, f, indent=4, ensure_ascii=False)
            
            print(f"   ✅ Saved to: {output_file}")
            
            # Rate limit mitigation for OpenRouter/Meta
            time.sleep(2) 
            
        except Exception as e:
            print(f"   ❌ Fatal error processing '{concept}': {e}")

    print("\n🏁 Batch generation complete.")

if __name__ == "__main__":
    generate_batches()
