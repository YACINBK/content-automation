"""
migrate.py — One-time migration script.
Safely moves the current dark_productivity niche data into the niches/ workspace structure.
SAFE: Does not delete anything until the copy is verified. Prints a full manifest before proceeding.
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
NICHE_NAME = "dark_productivity"

NICHE_DIR = os.path.join(ROOT, "niches", NICHE_NAME)

# --- SOURCE → DESTINATION MAP ---
MIGRATIONS = [
    (os.path.join(ROOT, "concepts.txt"),           os.path.join(NICHE_DIR, "concepts.txt")),
    (os.path.join(ROOT, "configs"),                 os.path.join(NICHE_DIR, "configs")),
    (os.path.join(ROOT, "niche_output"),            os.path.join(NICHE_DIR, "niche_output")),
    (os.path.join(ROOT, "niche_output_captioned"),  os.path.join(NICHE_DIR, "niche_output_captioned")),
    (os.path.join(ROOT, "upload_log.json"),         os.path.join(NICHE_DIR, "niche_output_captioned", "upload_log.json")),
]

NICHE_ENV_CONTENT = """\
# niche.env — Dark Productivity branding profile
# Loaded by run.py at runtime. Do NOT commit secrets here.

NICHE_NAME=Dark Productivity
GDRIVE_FOLDER=Niche
ONEDRIVE_SUBFOLDER=DarkProductivity
"""

def migrate():
    print("=" * 60)
    print(f"MIGRATION: Moving '{NICHE_NAME}' data into niches/ workspace")
    print("=" * 60)

    # Validate sources exist
    missing = []
    for src, _ in MIGRATIONS:
        if not os.path.exists(src):
            missing.append(src)

    if missing:
        print("\n⚠️  The following sources were not found (they may already be migrated):")
        for m in missing:
            print(f"   - {m}")
        existing = [src for src, _ in MIGRATIONS if os.path.exists(src)]
        if not existing:
            print("\n✅ Nothing to migrate — workspace appears to already be set up.")
            return

    # Print full manifest
    print("\n📋 MIGRATION MANIFEST (copy only, nothing deleted yet):")
    for src, dst in MIGRATIONS:
        if os.path.exists(src):
            print(f"   {src}")
            print(f"   → {dst}\n")

    confirm = input("Proceed with migration? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        return

    os.makedirs(NICHE_DIR, exist_ok=True)

    for src, dst in MIGRATIONS:
        if not os.path.exists(src):
            print(f"   [SKIP] Not found (skipping): {src}")
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src):
            if os.path.exists(dst):
                print(f"   [SKIP] Already exists at destination: {dst}")
            else:
                shutil.copytree(src, dst)
                print(f"   [OK] Copied dir:  {os.path.basename(src)} → {dst}")
        else:
            shutil.copy2(src, dst)
            print(f"   [OK] Copied file: {os.path.basename(src)} → {dst}")

    # Write niche.env
    niche_env_path = os.path.join(NICHE_DIR, "niche.env")
    if not os.path.exists(niche_env_path):
        with open(niche_env_path, "w", encoding="utf-8") as f:
            f.write(NICHE_ENV_CONTENT)
        print(f"\n   [OK] Created niche.env at {niche_env_path}")

    # Verification pass
    print("\n🔍 VERIFICATION:")
    all_ok = True
    for src, dst in MIGRATIONS:
        if not os.path.exists(src):
            continue
        if os.path.exists(dst):
            print(f"   ✅ {dst}")
        else:
            print(f"   ❌ MISSING: {dst}")
            all_ok = False

    if not all_ok:
        print("\n⚠️  Some files failed to copy. DO NOT delete originals yet.")
        return

    print("\n✅ All data verified at destination.")
    print("\n⚠️  REMINDER: The original files at the root level are still present.")
    print("   You may manually delete them once you confirm `python run.py --niche dark_productivity --factory` works correctly.")
    print("   DO NOT delete them yet.\n")

if __name__ == "__main__":
    migrate()
