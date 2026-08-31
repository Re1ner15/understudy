import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

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

from understudy_agent.slack_app import start_socket_mode

def main():
    print("==================================================", flush=True)
    print("Understudy Slack Socket Mode Agent Starting...", flush=True)
    print(f"Firestore Host: {os.getenv('FIRESTORE_EMULATOR_HOST')}", flush=True)
    print(f"Slack Channel:  {os.getenv('SLACK_CHANNEL', '#under-study')}", flush=True)
    print("==================================================", flush=True)
    try:
        start_socket_mode()
    except KeyboardInterrupt:
        print("\nStopping Slack Socket Mode Agent.", flush=True)

if __name__ == "__main__":
    main()

