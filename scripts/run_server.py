import os
import sys
from pathlib import Path
import uvicorn
from dotenv import load_dotenv

# Ensure root dir on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Load .env
env_file = root_dir / "understudy_agent" / ".env"
load_dotenv(dotenv_path=env_file)
load_dotenv()

# Default emulator host if not set
if "FIRESTORE_EMULATOR_HOST" not in os.environ:
    os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
if "GOOGLE_CLOUD_PROJECT" not in os.environ:
    os.environ["GOOGLE_CLOUD_PROJECT"] = "demo-understudy"

def main():
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting Understudy Agent Server on {host}:{port}...")
    print(f"Mock Agent Mode: {os.getenv('MOCK_AGENT', '0')}")
    print(f"Firestore Emulator: {os.getenv('FIRESTORE_EMULATOR_HOST')}")
    uvicorn.run("understudy_agent.server:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    main()
