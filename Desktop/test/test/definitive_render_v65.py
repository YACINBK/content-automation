import subprocess
import os

def run_step(name, command):
    print(f"\n>>> RUNNING STEP: {name} ({command})")
    try:
        subprocess.run(command, shell=True, check=True)
        print(f">>> SUCCESS: {name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f">>> FAILED: {name} (Error: {e})")
        return False

def main():
    print("=====================================================")
    print("V6.5 DEFINITIVE RENDER :: CONSOLIDATED CONTROLLER")
    print("=====================================================")
    print("  - Only patches configs missing image_prompts.")
    print("  - Already-captioned videos are auto-skipped.")
    print("=====================================================")

    # 1. Safe patch — only fills in configs that are incomplete (skips complete ones)
    if not run_step("SAFE_PATCH", "python tmp_v65_patcher_fixed.py"):
        return

    # 2. Cleanup stale audio/master assets for un-captioned concepts
    if not run_step("SURGICAL_CLEANUP", "python tmp_v65_cleanup.py"):
        return

    # 3. Launch Factory Floor (auto-skips already-captioned projects)
    if not run_step("FACTORY_FLOOR", "python factory_floor.py"):
        return

    print("\n=====================================================")
    print("BATCH FULLY COMPLETE. ALL MASTER REELS CAPTIONED.")
    print("=====================================================")

if __name__ == "__main__":
    main()
