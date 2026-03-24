import subprocess
import os
import time

configs = [
    "configs/nasa_launch_failure.json",
    "configs/radar_operator.json",
    "configs/bomb_squad.json",
    "configs/victorian_ghost.json",
    "configs/dialup_it_tech.json",
    "configs/apex_predator.json",
    "configs/air_traffic_controller.json",
    "configs/subway_surfer_philosopher.json",
    "configs/warden_of_tomorrow.json",
    "configs/starving_chef.json"
]

def run_production():
    for config in configs:
        if not os.path.exists(config):
            print(f"ΓÜá∩╕Å Skipping {config}: File not found.")
            continue
            
        print(f"≡ƒÜÇ Igniting Production: {config}")
        try:
            # Run the engine
            result = subprocess.run(
                ["python", "voicebox_story_engine.py", "--config", config],
                capture_output=False, 
                text=True
            )
            
            if result.returncode == 0:
                print(f"Γ£à Successfully produced: {config}")
            else:
                print(f"Γ¥î Production failed for: {config}")
                
            print("Γî¢ Cooling down for 10 seconds...")
            time.sleep(10)
            
        except Exception as e:
            print(f"Γ¥î Error running {config}: {e}")

if __name__ == "__main__":
    run_production()
