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
    Loads the niche profile and constructs the full environment dict
    that will be injected into subprocess calls.
    """
    niche_dir = NICHES_DIR / niche_name

    if not niche_dir.exists():
        print(f"✨ Initializing niche: {niche_name}")
        niche_dir.mkdir(parents=True, exist_ok=True)

    concepts_file = niche_dir / "concepts.txt"
    if not concepts_file.exists():
        concepts_file.write_text(
            f"# {niche_name} concepts\n# Add blocks beginning with 'Concept 1: Title'\n",
            encoding="utf-8"
        )

    configs_dir   = niche_dir / "configs"
    workspace_dir = niche_dir / "niche_output"
    captioned_dir = niche_dir / "niche_output_captioned"
    assets_dir    = niche_dir / "assets"
    prompts_dir   = niche_dir / "prompts"

    # Ensure niche directories exist
    for directory in (configs_dir, workspace_dir, captioned_dir, assets_dir, prompts_dir):
        directory.mkdir(parents=True, exist_ok=True)

    # Load per-niche branding profile
    niche_env_file = niche_dir / "niche.env"
    niche_profile = {}
    if niche_env_file.exists():
        niche_profile = dotenv_values(str(niche_env_file))
    else:
        print(f"⚠️  Warning: No niche.env found at {niche_env_file}. Using defaults.")

    if not niche_env_file.exists():
        niche_env_file.write_text(
            "\n".join([
                f"NICHE_NAME={niche_name.replace('_', ' ').title()}",
                f"GDRIVE_FOLDER={niche_name}",
                f"ONEDRIVE_SUBFOLDER={niche_name}",
                "VISUAL_PROFILE=none",
                "VOICE_FILTER=none",
                "",
            ]),
            encoding="utf-8"
        )
        niche_profile = dotenv_values(str(niche_env_file))

    persona_file = prompts_dir / "persona.txt"
    if not persona_file.exists():
        persona_file.write_text(
            "You are a professional short-form documentary creator.\n",
            encoding="utf-8"
        )

    aesthetic_file = prompts_dir / "aesthetic.txt"
    if not aesthetic_file.exists():
        aesthetic_file.write_text(
            ", cinematic high-quality video, vertical 9:16 aspect ratio.",
            encoding="utf-8"
        )

    # Start from current environment (inherits global .env already loaded by parent, API keys, etc.)
    env = os.environ.copy()

    # Inject absolute niche-specific paths so every engine resolves the right workspace
    env["NICHE_CONCEPTS_FILE"] = str(concepts_file.resolve())
    env["NICHE_CONFIGS_DIR"]   = str(configs_dir.resolve())
    env["NICHE_WORKSPACE_DIR"] = str(workspace_dir.resolve())
    env["NICHE_CAPTIONED_DIR"] = str(captioned_dir.resolve())
    env["NICHE_ASSETS_DIR"]    = str(assets_dir.resolve())
    env["NICHE_PROMPTS_DIR"]   = str(prompts_dir.resolve())
    env["VISUAL_PROFILE"]      = niche_profile.get("VISUAL_PROFILE", "none")
    env["VOICE_FILTER"]        = niche_profile.get("VOICE_FILTER", "none")
    voice_profile_id = (
        niche_profile.get("VOICEBOX_PROFILE_ID")
        or env.get("VOICEBOX_PROFILE_ID")
        or env.get("DEFAULT_VOICE_ID")
    )
    if voice_profile_id:
        env["VOICEBOX_PROFILE_ID"] = voice_profile_id

    # --- OneDrive Resolution ---
    # ONEDRIVE_BASE: the root OneDrive root drive path (set in global .env or defaults to institution drive)
    onedrive_base = env.get(
        "ONEDRIVE_BASE",
        r"D:\OneDrive - Ministere de l'Enseignement Superieur et de la Recherche Scientifique"
    )
    # ONEDRIVE_SUBFOLDER: the per-niche subfolder name (set in niche.env)
    onedrive_subfolder = niche_profile.get("ONEDRIVE_SUBFOLDER", niche_name)
    onedrive_full = os.path.join(onedrive_base, onedrive_subfolder)
    env["ONEDRIVE_BASE"]      = onedrive_base
    env["ONEDRIVE_SUBFOLDER"] = onedrive_subfolder

    # --- Google Drive Resolution ---
    # GDRIVE_FOLDER: per-niche folder name to create/locate in Google Drive
    gdrive_folder = niche_profile.get("GDRIVE_FOLDER", niche_name.replace("_", " ").title())
    env["GDRIVE_FOLDER"] = gdrive_folder

    print(f"\n{'='*60}")
    print(f"🚀 NICHE ENGINE STARTUP")
    print(f"{'='*60}")
    print(f"   Niche          : {niche_profile.get('NICHE_NAME', niche_name)}")
    print(f"   Concepts File  : {concepts_file}")
    print(f"   Configs Dir    : {configs_dir}")
    print(f"   Factory Output : {workspace_dir}")
    print(f"   Captioned Dir  : {captioned_dir}")
    print(f"   OneDrive Path  : {onedrive_full}")
    print(f"   G-Drive Folder : {gdrive_folder}")
    print(f"{'='*60}\n")

    return env


def run_stage(script_name, env, label):
    """Executes a pipeline stage script with the injected niche environment."""
    script_path = ROOT / script_name
    if not script_path.exists():
        print(f"❌ ERROR: Script not found: {script_path}")
        sys.exit(1)

    print(f"\n▶️  STAGE: {label}")
    print(f"   Running: python {script_name}\n")

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
        description="Dark Productivity Content Engine — Niche CLI",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--niche",   type=str, help="Target niche name (e.g. dark_productivity)")
    parser.add_argument("--patch",   action="store_true", help="Generate JSON configs from concepts.txt")
    parser.add_argument("--factory", action="store_true", help="Run the video factory")
    parser.add_argument("--upload",  action="store_true", help="Upload completed videos to YouTube + Cloud")
    parser.add_argument("--all",     action="store_true", help="Full pipeline: patch → factory → upload")
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
        run_stage("tmp_v65_patcher_fixed.py", env, "PATCH — Generating configs from concepts.txt")
        run_stage("factory_floor.py",         env, "FACTORY — Rendering videos")
        run_stage("upload_scheduler.py",      env, "UPLOAD — Distributing to YouTube + Cloud")
    else:
        if args.patch:
            run_stage("tmp_v65_patcher_fixed.py", env, "PATCH — Generating configs from concepts.txt")
        if args.factory:
            run_stage("factory_floor.py",         env, "FACTORY — Rendering videos")
        if args.upload:
            run_stage("upload_scheduler.py",      env, "UPLOAD — Distributing to YouTube + Cloud")

        if not any([args.patch, args.factory, args.upload]):
            print("⚠️  No action specified. Use --patch, --factory, --upload, or --all.")
            parser.print_help()


if __name__ == "__main__":
    main()
