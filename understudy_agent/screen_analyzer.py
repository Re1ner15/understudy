import os
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

from understudy_agent.config import MODEL_ID
from understudy_agent.schemas import ScreenContext

# Load environment
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

_client = None

def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client()
    return _client

def get_mock_screen_context() -> ScreenContext:
    """Returns a canned ScreenContext for testing without calling Gemini."""
    return ScreenContext(
        kind="slide",
        summary="Architecture roadmap and checkout API specification overview slide",
        keyPoints=[
            "Tier 2 milestone: Screen awareness & meeting minutes generation",
            "Checkout endpoints contract delivery expected by Friday",
            "Design review sync booked for Thursday at 2:00 PM",
        ],
        ts=datetime.now().strftime("%H:%M:%S"),
    )

ANALYSIS_PROMPT = """Analyze this screenshot from an active meeting or work session.
Identify what is being displayed and extract key information.

Determine:
1. kind: One of 'slide', 'website', 'doc', 'code', 'app', 'other'.
2. summary: A concise 1-2 sentence description of what is currently on the screen.
3. keyPoints: 2-4 salient bullet points of the important text, diagrams, numbers, or topics visible.
4. ts: The current local time in HH:MM:SS format.

Be concise, accurate, and focus on details relevant to meeting attendees."""

def analyze_screenshot(image_path: str, mock: bool = False) -> ScreenContext:
    """Analyzes a screenshot using Gemini multimodal structured output or returns a mock.
    
    Args:
        image_path: Path to the screenshot image file (PNG/JPEG).
        mock: If True, returns a canned ScreenContext without making Gemini API calls.
        
    Returns:
        ScreenContext: Structured representation of what is on screen.
    """
    if mock or os.getenv("MOCK_GEMINI", "").lower() in ("true", "1", "yes"):
        return get_mock_screen_context()

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Screenshot file not found: {image_path}")

    # Determine mime type
    ext = os.path.splitext(image_path)[1].lower()
    mime_type = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    client = get_client()
    retries = [2, 5, 15, 30]

    for attempt in range(len(retries) + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type,
                    ),
                    ANALYSIS_PROMPT,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ScreenContext,
                ),
            )
            return ScreenContext.model_validate_json(response.text)
        except Exception as e:
            err_str = str(e)
            if attempt < len(retries) and (
                "503" in err_str
                or "429" in err_str
                or "UNAVAILABLE" in err_str
                or "Too Many Requests" in err_str
                or "RESOURCE_EXHAUSTED" in err_str
            ):
                print(f"Gemini API rate limit/transient error ({err_str}), retrying in {retries[attempt]}s...")
                time.sleep(retries[attempt])
            else:
                raise e

    raise RuntimeError("analyze_screenshot: exhausted retries")
