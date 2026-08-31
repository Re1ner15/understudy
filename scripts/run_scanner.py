import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure understudy_agent package is discoverable
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

# Load .env
env_file = root_dir / "understudy_agent" / ".env"
load_dotenv(dotenv_path=env_file)
load_dotenv()

# Default emulator host if not set
if "FIRESTORE_EMULATOR_HOST" not in os.environ:
    os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"

from understudy_agent.scanner import scan_and_nudge

def main():
    print("==================================================")
    print("Understudy Follow-Up Nudge Scanner Starting...")
    print(f"Firestore Host: {os.getenv('FIRESTORE_EMULATOR_HOST')}")
    print(f"Slack Channel:  {os.getenv('SLACK_CHANNEL', '#under-study')}")
    print("==================================================")
    
    results = scan_and_nudge()
    
    print("\n--- Scan Results ---")
    if not results:
        print("No overdue commitments found.")
    else:
        for res in results:
            print(f" • [{res['id']}] {res['title']} -> {res['note']} (Nudge #{res['nudgeCount']})")
    print("==================================================")

if __name__ == "__main__":
    main()
