"""
run.py — Single Entry Point for the Dark Productivity Content Engine.
Loads the correct niche workspace, injects all paths into the environment,
then executes the requested pipeline stage.

Usage:
    python run.py --niche dark_productivity --patch      # Generate JSON configs from concepts.txt
    python run.py --niche dark_productivity --factory    # Run the video factory
    python run.py --niche dark_productivity --upload     # Upload completed videos to YouTube + Cloud
    python run.py --niche dark_productivity --all        # Full pipeline: patch → factory → upload
    python run.py --list                                 # List all available niches
"""

import os
import sys

# Force UTF-8 encoding for Windows console to handle emojis and arrows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import argparse
import subprocess
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).parent.resolve()
NICHES_DIR = ROOT / "niches"


def list_niches():
    if not NICHES_DIR.exists():
        print("No niches/ directory found. Run `python migrate.py` first.")
        return
    niches = [d.name for d in NICHES_DIR.iterdir() if d.is_dir()]
    if not niches:
        print("No niches found in niches/ directory.")
        return
    print("Available niches:")
    for n in sorted(niches):
        niche_dir = NICHES_DIR / n
        concepts_path = niche_dir / "concepts.txt"
        captioned_dir = niche_dir / "niche_output_captioned"
        captioned_count = len(list(captioned_dir.glob("*_Captioned.mp4"))) if captioned_dir.exists() else 0
        status = f"{captioned_count} videos captioned" if captioned_count else "no output yet"
        print(f"   • {n:<30} ({status})")


def build_niche_env(niche_name):
    """
    Loads the niche profile and constructs the full environment dict.
    Viper Mode: Auto-initializes missing niches with sane defaults.
    """
    niche_dir = NICHES_DIR / niche_name
    
    # 1. INITIALIZE DIRECTORY STRUCTURE
    if not niche_dir.exists():
        print(f"✨ Initializing NEW Niche: {niche_name}")
        niche_dir.mkdir(parents=True, exist_ok=True)

    # Core Folders
    configs_dir   = niche_dir / "configs"
    workspace_dir = niche_dir / "niche_output"
    captioned_dir = niche_dir / "niche_output_captioned"
    assets_dir    = niche_dir / "assets"
    prompts_dir   = niche_dir / "prompts"

    for d in [configs_dir, workspace_dir, captioned_dir, assets_dir, prompts_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # 2. INITIALIZE CONCEPTS.TXT
    concepts_file = niche_dir / "concepts.txt"
    if not concepts_file.exists():
        print(f"   📝 Creating concepts.txt template...")
        with open(concepts_file, "w", encoding="utf-8") as f:
            f.write(f"# {niche_name} Concepts List\n# Format: Concept 1: Title\nConcept 1: The Beginning\n")

    # 3. INITIALIZE NICHE.ENV (Algorithmic Defaults)
    niche_env_file = niche_dir / "niche.env"
    if not niche_env_file.exists():
        print(f"   ⚙️  Generating clean niche.env defaults...")
        env_content = f"""NICHE_NAME={niche_name.replace('_', ' ').title()}
GDRIVE_FOLDER={niche_name}
ONEDRIVE_SUBFOLDER={niche_name}
VISUAL_PROFILE=none
VOICE_FILTER=none

# --- STRATEGY PUZZLE PIECES ---
META_HOOK_NAME=Record
META_STATUS_TEMPLATE=STATUS: {{status}}
META_TITLE_FORMAT={{title}} | {{hook_name}} {{hook_num}}
META_DESC_FORMAT=SUBJECT: {{subject}}\\n{{status_line}}\\n\\n#documentary #facts #shorts
UPLOAD_SLOTS=13:00, 18:00, 01:00
"""
        with open(niche_env_file, "w", encoding="utf-8") as f:
            f.write(env_content)

    # 4. INITIALIZE PROMPT FRAGMENTS
    persona_file = prompts_dir / "persona.txt"
    if not persona_file.exists():
        print(f"   🧩 Creating default persona.txt...")
        with open(persona_file, "w", encoding="utf-8") as f:
            f.write("[SYSTEM ROLE: THE EXPERT CREATOR]\nYou are a professional content strategist and narrator specializing in high-impact short-form storytelling.\n")

    aesthetic_file = prompts_dir / "aesthetic.txt"
    if not aesthetic_file.exists():
        print(f"   🎨 Creating default aesthetic.txt...")
        with open(aesthetic_file, "w", encoding="utf-8") as f:
            f.write(", cinematic high-quality video, 4k resolution, sharp focus, natural lighting, 9:16 vertical aspect ratio.")

    # Load per-niche branding profile for injection
    niche_profile = dotenv_values(str(niche_env_file))

    # Start from current environment
    env = os.environ.copy()

    # Inject absolute niche-specific paths
    env["NICHE_CONCEPTS_FILE"] = str(concepts_file.resolve())
    env["NICHE_CONFIGS_DIR"]   = str(configs_dir.resolve())
    env["NICHE_WORKSPACE_DIR"] = str(workspace_dir.resolve())
    env["NICHE_CAPTIONED_DIR"] = str(captioned_dir.resolve())
    env["NICHE_ASSETS_DIR"]    = str(assets_dir.resolve())

    # --- OneDrive Resolution ---
    onedrive_base = env.get(
        "ONEDRIVE_BASE",
        r"D:\OneDrive - Ministere de l'Enseignement Superieur et de la Recherche Scientifique"
    )
    onedrive_subfolder = niche_profile.get("ONEDRIVE_SUBFOLDER", niche_name)
    onedrive_full = os.path.join(onedrive_base, onedrive_subfolder)
    env["ONEDRIVE_BASE"]      = onedrive_base
    env["ONEDRIVE_SUBFOLDER"] = onedrive_subfolder

    # --- Google Drive Resolution ---
    gdrive_folder = niche_profile.get("GDRIVE_FOLDER", niche_name.replace("_", " ").title())
    env["GDRIVE_FOLDER"] = gdrive_folder

    print(f"\n{'='*60}")
    print(f"🚀 NICHE ENGINE STARTUP")
    print(f"{'='*60}")
    print(f"   Name           : {niche_profile.get('NICHE_NAME', niche_name)}")
    print(f"   OneDrive       : {onedrive_full}")
    print(f"   G-Drive        : {gdrive_folder}")
    print(f"{'='*60}\n")

    return env


def run_stage(script_name, env, label):
    """Executes a pipeline stage script with the injected niche environment."""
    script_path = ROOT / "engine" / script_name
    if not script_path.exists():
        print(f"❌ ERROR: Script not found: {script_path}")
        sys.exit(1)

    print(f"\n▶️  STAGE: {label}")
    print(f"   Running: python engine/{script_name}\n")

    # Add engine directory to PYTHONPATH so imports within engine/ resolve correctly
    env["PYTHONPATH"] = str(ROOT / "engine") + os.pathsep + env.get("PYTHONPATH", "")

    # Run the engine script from the project root so all relative imports work correctly
    result = subprocess.run(
        [sys.executable, str(script_path)],
        env=env,
        cwd=str(ROOT)  # Always run from root so engine imports resolve correctly
    )

    if result.returncode != 0:
        print(f"\n❌ Stage '{label}' exited with code {result.returncode}. Check output above.")
        sys.exit(result.returncode)

    print(f"\n✅ Stage '{label}' completed successfully.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Universal Content Engine — Niche CLI",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--niche",   type=str, help="Target niche name (e.g. dark_productivity)")
    parser.add_argument("--patch",   action="store_true", help="Generate JSON configs from concepts.txt")
    parser.add_argument("--scrape",  action="store_true", help="Scrape clips using Universal AI Visual Architect")
    parser.add_argument("--factory", action="store_true", help="Run the video factory")
    parser.add_argument("--upload",  action="store_true", help="Upload completed videos to YouTube + Cloud")
    parser.add_argument("--all",     action="store_true", help="Full pipeline: patch → scrape → factory → upload")
    parser.add_argument("--list",    action="store_true", help="List all available niches")

    args = parser.parse_args()

    if args.list:
        list_niches()
        return

    if not args.niche:
        parser.print_help()
        sys.exit(1)

    # Validate and build niche environment
    env = build_niche_env(args.niche)

    if args.all:
        run_stage("concept_patcher.py",   env, "PATCH — Generating configs from concepts.txt")
        run_stage("scraping_manager.py",  env, "SCRAPE — Universal AI Visual Architect Scraper")
        run_stage("factory_floor.py",     env, "FACTORY — Rendering videos")
        run_stage("upload_scheduler.py",  env, "UPLOAD — Distributing to YouTube + Cloud")
    else:
        if args.patch:
            run_stage("concept_patcher.py",   env, "PATCH — Generating configs from concepts.txt")
        if args.scrape:
            # We run scraping_manager.py which by default runs in HEADED mode
            run_stage("scraping_manager.py",  env, "SCRAPE — Universal AI Visual Architect Scraper")
        if args.factory:
            run_stage("factory_floor.py",     env, "FACTORY — Rendering videos")
        if args.upload:
            run_stage("upload_scheduler.py",  env, "UPLOAD — Distributing to YouTube + Cloud")

        if not any([args.patch, args.scrape, args.factory, args.upload]):
            print("⚠️  No action specified. Use --patch, --factory, --upload, or --all.")
            parser.print_help()


if __name__ == "__main__":
    main()
