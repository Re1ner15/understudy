import os
import sys
import argparse
import tempfile
from PIL import Image
import mss

from understudy_agent.screen_analyzer import analyze_screenshot

def main():
    parser = argparse.ArgumentParser(description="Test screen watcher capture and analysis")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock screen context instead of calling Gemini API",
    )
    args = parser.parse_args()

    print(f"Capturing current screen once (mock={args.mock})...")
    with mss.MSS() as sct:
        monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    # Downscale if needed
    if img.width > 1280:
        new_height = int(img.height * (1280 / img.width))
        img = img.resize((1280, new_height), Image.Resampling.LANCZOS)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        img.save(tmp_path, format="PNG")
        print(f"Saved temporary screenshot to {tmp_path}")
        print("Running analyze_screenshot...")
        ctx = analyze_screenshot(tmp_path, mock=args.mock)

        print("\n" + "=" * 60)
        print("ScreenContext Result:")
        print("=" * 60)
        print(f"Kind:       {ctx.kind}")
        print(f"Summary:    {ctx.summary}")
        print(f"Timestamp:  {ctx.ts}")
        print("Key Points:")
        for pt in ctx.keyPoints:
            print(f"  - {pt}")
        print("=" * 60)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

if __name__ == "__main__":
    main()
