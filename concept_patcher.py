"""
concept_patcher.py
Universal Free-Form Concept Parser.
Allows the user to type freely. 
- If a block starts with 'Concept N: Title', it extracts that title.
- Otherwise, it takes the first line as the title.
- Supports multiple concepts separated by '---'.
- Never overwrites a config that is already in progress.
"""
import json
import os
import re
import sys

# Ensure we can import llm_handler from the same directory
sys.path.append(os.getcwd())
from llm_handler import LLMHandler

def slug(text):
    """Convert a concept title to a safe filename slug."""
    text = text.lower()
    text = re.sub(r"['\u2019]", "", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")

def parse_concepts():
    """
    Parses concepts.txt into a list of (slug, title, full_description) tuples.
    Supports:
    1. Explicit blocks: 'Concept 1: Title'
    2. Free-form: First line is title, rest is description.
    3. Separators: '---' between concepts.
    """
    filepath = os.getenv("NICHE_CONCEPTS_FILE", "concepts.txt")
    if not os.path.exists(filepath):
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read().strip()

    if not raw:
        return []

    # Split by standard separator
    blocks = re.split(r"\n---\n|\n===\n", raw)
    # If no separator found, check if it's one big block
    if len(blocks) == 1:
        # Fallback to double newline if they haven't used dashes yet
        blocks = re.split(r"\n{3,}", raw)

    parsed = []
    for block in blocks:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if not lines:
            continue

        first_line = lines[0]
        # Check if it follows the "Concept N: Title" pattern
        match = re.search(r"^Concept\s+\d+:\s*(.*)$", first_line, re.I)
        if match:
            title = match.group(1).strip()
            description = "\n".join(lines[1:])
        else:
            # Free-form mode: First line is title
            title = first_line
            description = "\n".join(lines[1:])

        if not title:
            continue

        parsed.append((slug(title), title, f"TITLE: {title}\nDESCRIPTION: {description}"))

    return parsed

def patch():
    concepts_file = os.getenv("NICHE_CONCEPTS_FILE", "concepts.txt")
    configs_dir   = os.getenv("NICHE_CONFIGS_DIR", "configs")

    os.makedirs(configs_dir, exist_ok=True)
    concepts = parse_concepts()

    if not concepts:
        print(f"⚠️ No concepts found in {concepts_file}. Make sure to add at least one line of text!")
        return

    print(f"🧩 Found {len(concepts)} Concept Blocks. Initializing Puzzle Pieces...")
    llm = LLMHandler()

    for name, title, description in concepts:
        path = os.path.join(configs_dir, name + ".json")

        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    existing = json.load(f)
                    if existing.get("narrative_script") and len(existing.get("narrative_script")) > 0:
                        print(f"   [SKIP] Config exists and is populated: {name}")
                        continue
                except Exception as e:
                    print(f"   [WARN] Could not parse existing config for {name}: {e}. Repatching.")
            print(f"   [REPATCH] Config shell found, updating: {name}")
        else:
            print(f"   [NEW] Assembling Puzzle for: {title}")

        # Assemble the narrative script from the Puzzle Assembler
        script_data = llm.generate_script(description)
        if script_data:
            # We ensure the niche-specific metadata is preserved/injected
            with open(path, "w", encoding="utf-8") as f:
                json.dump(script_data, f, indent=2, ensure_ascii=False)
            print(f"   [OK] {title} -> {name}.json")
        else:
            print(f"   [FAIL] LLM rejected concept: {name}")

if __name__ == "__main__":
    patch()
