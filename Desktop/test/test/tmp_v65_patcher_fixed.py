"""
tmp_v65_patcher_fixed.py
Reads concepts.txt and generates a JSON config in configs/ for each concept.
SAFETY: Never overwrites a config that already has image_prompts (already rendered).
"""
import json
import os
import re
import sys

sys.path.append(os.getcwd())
from llm_handler import LLMHandler


def slug(text):
    """Convert a concept title to a safe filename slug. e.g. 'The Pharaoh's iPad' -> 'the_pharaohs_ipad'"""
    text = text.lower()
    text = re.sub(r"['\u2019]", "", text)        # remove apostrophes
    text = re.sub(r"[^a-z0-9]+", "_", text)      # replace non-alphanumeric with _
    return text.strip("_")


def parse_concepts(filepath=None):
    """
    Parses concepts.txt into a list of (slug, full_description) tuples.
    filepath defaults to NICHE_CONCEPTS_FILE env var, then legacy 'concepts.txt'.
    Format expected:
        Concept N: <Title>
        Subject: ...
        Modern Habit: ...
        Psychological Twist: ...
        (blank line between concepts)
    """
    if filepath is None:
        filepath = os.getenv("NICHE_CONCEPTS_FILE", "concepts.txt")
    concepts = []
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    blocks = re.split(r"\n{2,}", raw.strip())

    for block in blocks:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if not lines:
            continue

        # Extract title from first line "Concept N: Title"
        title_match = re.match(r"^Concept\s+\d+:\s*(.+)$", lines[0], re.IGNORECASE)
        if not title_match:
            continue

        title = title_match.group(1).strip()
        name = slug(title)
        description = "\n".join(lines)  # full block as description for LLM

        concepts.append((name, title, description))

    return concepts


def patch():
    concepts_file = os.getenv("NICHE_CONCEPTS_FILE", "concepts.txt")
    configs_dir   = os.getenv("NICHE_CONFIGS_DIR", "configs")

    if not os.path.exists(concepts_file):
        print(f"ERROR: {concepts_file} not found.")
        return

    os.makedirs(configs_dir, exist_ok=True)
    concepts = parse_concepts(concepts_file)

    if not concepts:
        print("ERROR: No concepts parsed from concepts.txt. Check the format.")
        return

    print(f"Found {len(concepts)} concepts in {concepts_file}.")
    llm = LLMHandler()

    for name, title, description in concepts:
        path = os.path.join(configs_dir, name + ".json")

        # SAFETY: Never overwrite a config that already has image_prompts (already rendered)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if existing.get("image_prompts"):
                print(f"   [SKIP] Already complete (has image_prompts): {name}")
                continue
            print(f"   [PATCH] Incomplete config, regenerating: {name}")
        else:
            print(f"   [NEW] Generating config for: {title}")

        script = llm.generate_script(description)
        if script:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(script, f, indent=2, ensure_ascii=False)
            print(f"   [OK] Saved: {path}")
        else:
            print(f"   [ERROR] LLM failed to generate script for: {name}")

    print("\nPatcher complete. Run factory_floor.py to produce the batch.")


if __name__ == "__main__":
    patch()
