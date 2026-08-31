import os
import sys
import time
import argparse
import tempfile
import datetime
from PIL import Image
import mss
import imagehash

from understudy_agent.schemas import ScreenContext
from understudy_agent.screen_analyzer import analyze_screenshot

# Note: macOS Screen Recording permission is required for mss screen capture.
# Grant permission in System Settings -> Privacy & Security -> Screen Recording.

DEFAULT_INTERVAL = 12.0
DEFAULT_THRESHOLD = 5
MAX_IMAGE_WIDTH = 1280

import requests

def on_screen_context(ctx: ScreenContext):
    """Clean seam called when a new or changed screen context is analyzed.
    
    Mirrors on_utterance from listener/listen.py so it can easily be wired
    to POST to an agent service or write directly to Firestore.
    """
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    server_url = os.getenv("AGENT_SERVER_URL", "http://localhost:8000").rstrip("/")
    meeting_id = os.getenv("MEETING_ID", "demo-meeting")
    endpoint = f"{server_url}/meetings/{meeting_id}/screen-context"

    posted = False
    try:
        resp = requests.post(
            endpoint,
            json=ctx.model_dump(),
            timeout=2.0,
        )
        if resp.status_code == 200:
            posted = True
            print(f"[{timestamp}] [SCREEN Synced] ({ctx.kind}) {ctx.summary}")
    except Exception:
        pass

    if not posted:
        print(f"[{timestamp}] [SCREEN] ({ctx.kind}) {ctx.summary}")
    for kp in ctx.keyPoints:
        print(f"  - {kp}")

def capture_primary_screen(sct: mss.MSS) -> Image.Image:
    """Captures the primary monitor and returns a PIL Image."""
    # sct.monitors[1] is the primary display; fallback to sct.monitors[0] if needed
    monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
    sct_img = sct.grab(monitor)
    return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

def downscale_image(img: Image.Image, max_width: int = MAX_IMAGE_WIDTH) -> Image.Image:
    """Downscales the image to max_width preserving aspect ratio."""
    if img.width > max_width:
        new_height = int(img.height * (max_width / img.width))
        return img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    return img

def watch_screen(
    interval: float = DEFAULT_INTERVAL,
    threshold: int = DEFAULT_THRESHOLD,
    mock: bool = False,
):
    """Continuously captures primary screen, compares perceptual hash against last frame,

    and analyzes changed frames with screen_analyzer.
    """
    print("=" * 60)
    print("Starting Understudy Screen Watcher")
    print(f"Interval: {interval}s | Hash Difference Threshold: {threshold} | Mock Mode: {mock}")
    print("Note: macOS Screen Recording permission is required.")
    print("Listening for visual changes... (Press Ctrl+C to stop)")
    print("=" * 60)

    last_hash = None

    with mss.MSS() as sct:
        while True:
            try:
                # 1. Capture screen
                img = capture_primary_screen(sct)
                current_hash = imagehash.phash(img)

                # 2. Change-detection via perceptual hash Hamming distance
                if last_hash is not None:
                    distance = current_hash - last_hash
                    if distance <= threshold:
                        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] Screen unchanged (Hamming distance: {distance} <= {threshold}). Skipping analysis.")
                        time.sleep(interval)
                        continue
                    else:
                        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] Visual change detected (Hamming distance: {distance} > {threshold}). Analyzing...")
                else:
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] Initial frame captured. Analyzing...")

                # 3. Downscale frame before analysis
                downscaled = downscale_image(img, MAX_IMAGE_WIDTH)

                # 4. Save to temporary PNG file
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_path = tmp.name
                
                try:
                    downscaled.save(tmp_path, format="PNG")

                    # 5. Multimodal analysis
                    ctx = analyze_screenshot(tmp_path, mock=mock)

                    # 6. Trigger clean seam
                    on_screen_context(ctx)

                    # 7. Update last hash only after successful analysis
                    last_hash = current_hash
                finally:
                    if os.path.exists(tmp_path):
                        try:
                            os.remove(tmp_path)
                        except OSError:
                            pass

                time.sleep(interval)

            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"Error during screen capture/analysis: {e}", file=sys.stderr)
                time.sleep(interval)

def main():
    parser = argparse.ArgumentParser(description="Understudy Screen Watcher")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode without calling Gemini API",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.getenv("SCREEN_INTERVAL", DEFAULT_INTERVAL)),
        help=f"Capture interval in seconds (default: {DEFAULT_INTERVAL}s or env SCREEN_INTERVAL)",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=int(os.getenv("HASH_THRESHOLD", DEFAULT_THRESHOLD)),
        help=f"Perceptual hash distance threshold (default: {DEFAULT_THRESHOLD} or env HASH_THRESHOLD)",
    )
    args = parser.parse_args()

    try:
        watch_screen(interval=args.interval, threshold=args.threshold, mock=args.mock)
    except KeyboardInterrupt:
        print("\nStopping Screen Watcher...")
    finally:
        print("Screen Watcher stopped cleanly.")

if __name__ == "__main__":
    main()
