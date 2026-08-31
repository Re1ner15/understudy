import os
import re
import json
import time
import asyncio
import logging
from typing import Any
from dotenv import load_dotenv
from google import genai
from understudy_agent.config import GEMMA_MODEL_ID

# Load environment configuration
load_dotenv("understudy_agent/.env")
load_dotenv()

logger = logging.getLogger(__name__)

# Lazy initialization for Google GenAI client
_client: genai.Client | None = None

def get_genai_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


# --- Mock / Heuristic Evaluation ---

ACTIONABLE_PATTERNS = [
    r"\bi('ll| will| can| am going to|'m going to)\b",
    r"\bwe('ll| will| can| should|'re going to)\b",
    r"\blet('s| us| me)\b",
    r"\b(please|can you|could you|would you)\b",
    r"\b(action item|to-?do|follow-?up|take an item|assign)\b",
    r"\b(email|ping|slack|schedule|calendar|draft|create|file|deploy|review|update|investigate|reach out)\b",
    r"\b(by tomorrow|by friday|by monday|by next week|by eod|end of day)\b",
]

NON_ACTIONABLE_PATTERNS = [
    r"^how was your weekend",
    r"^(hi|hello|hey|good morning|good afternoon|good evening)\b",
    r"^(how are you|how's it going|what's up|how're things)\b",
    r"^(thanks|thank you|sounds good|makes sense|cool|awesome|great|got it|yep|yeah|no problem)\b",
    r"\b(weather|weekend|lunch|coffee|movie|game last night)\b",
]


def _mock_is_actionable(utterance: str) -> dict[str, Any]:
    """Deterministic, zero-cost classification for testing and dry-runs."""
    cleaned = utterance.strip().lower()
    if not cleaned:
        return {"actionable": False, "confidence": 0.0}

    # Check for direct chatter / small talk patterns first
    is_chatter = any(re.search(pat, cleaned) for pat in NON_ACTIONABLE_PATTERNS)
    # Check for explicit actionable patterns
    has_action = any(re.search(pat, cleaned) for pat in ACTIONABLE_PATTERNS)

    if has_action and not is_chatter:
        return {"actionable": True, "confidence": 0.95}
    elif is_chatter and not has_action:
        return {"actionable": False, "confidence": 0.05}
    elif has_action and is_chatter:
        # e.g., "Good morning, I'll email the vendor"
        # If there's an explicit commitment verb, prioritize actionable
        if re.search(r"\bi('ll| will| can|'m going to)\b|\b(email|schedule|ping|slack|create|draft|file)\b", cleaned):
            return {"actionable": True, "confidence": 0.90}
        return {"actionable": False, "confidence": 0.15}
    else:
        # Default conservative stance: non-actionable
        return {"actionable": False, "confidence": 0.10}


def _build_gemma_prompt(utterance: str) -> str:
    return (
        "You are a fast, lightweight gate filter for a meeting assistant. "
        "Your job is to determine whether a transcribed utterance contains an actionable commitment, "
        "decision, task assignment, or follow-up item that requires tracking.\n\n"
        f'Utterance: "{utterance}"\n\n'
        "Instructions:\n"
        '- "actionable": true if the utterance contains a commitment (e.g., "I\'ll email X", "Can you schedule Y", "Let\'s write the doc"), '
        'false if it is small talk, greeting, question, chatter, or passive discussion.\n'
        '- "confidence": a float between 0.0 and 1.0 indicating confidence.\n'
        'Respond ONLY with valid JSON in the format: {"actionable": true, "confidence": 0.95}'
    )


def _parse_filter_response(response_text: str) -> dict[str, Any]:
    """Extract and validate JSON containing 'actionable' and 'confidence'."""
    text = response_text.strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(f"Could not find JSON object in model response: {text}")

    data = json.loads(match.group(0))
    actionable = bool(data.get("actionable", False))
    confidence = float(data.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))

    return {"actionable": actionable, "confidence": confidence}


def is_actionable(
    utterance: str,
    mock: bool = False,
    model_id: str | None = None,
) -> dict[str, Any]:
    """Classify whether a transcript utterance is actionable.

    Args:
        utterance: The transcribed line of text from the meeting.
        mock: If True, uses local canned heuristic logic without making API calls.
        model_id: Gemma model ID override (defaults to GEMMA_MODEL_ID or 'gemma-2-9b-it').

    Returns:
        A dict with format: {"actionable": bool, "confidence": float}
    """
    if mock:
        return _mock_is_actionable(utterance)

    target_model = model_id or GEMMA_MODEL_ID
    client = get_genai_client()
    prompt = _build_gemma_prompt(utterance)

    retries = [1.0, 2.0, 4.0, 8.0]
    last_err: Exception | None = None

    for attempt in range(len(retries) + 1):
        try:
            response = client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )
            return _parse_filter_response(response.text or "")
        except Exception as e:
            last_err = e
            err_str = str(e)
            is_transient = any(
                code in err_str
                for code in ["429", "503", "500", "UNAVAILABLE", "Too Many Requests", "RESOURCE_EXHAUSTED"]
            )
            if attempt < len(retries) and is_transient:
                sleep_time = retries[attempt]
                logger.warning(
                    f"is_actionable attempt {attempt + 1} failed ({err_str}). Retrying in {sleep_time}s..."
                )
                time.sleep(sleep_time)
            else:
                break

    raise RuntimeError(f"is_actionable failed after retries: {last_err}") from last_err


async def async_is_actionable(
    utterance: str,
    mock: bool = False,
    model_id: str | None = None,
) -> dict[str, Any]:
    """Asynchronous version of is_actionable."""
    if mock:
        return _mock_is_actionable(utterance)

    target_model = model_id or GEMMA_MODEL_ID
    client = get_genai_client()
    prompt = _build_gemma_prompt(utterance)

    retries = [1.0, 2.0, 4.0, 8.0]
    last_err: Exception | None = None

    for attempt in range(len(retries) + 1):
        try:
            response = await client.aio.models.generate_content(
                model=target_model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )
            return _parse_filter_response(response.text or "")
        except Exception as e:
            last_err = e
            err_str = str(e)
            is_transient = any(
                code in err_str
                for code in ["429", "503", "500", "UNAVAILABLE", "Too Many Requests", "RESOURCE_EXHAUSTED"]
            )
            if attempt < len(retries) and is_transient:
                sleep_time = retries[attempt]
                logger.warning(
                    f"async_is_actionable attempt {attempt + 1} failed ({err_str}). Retrying in {sleep_time}s..."
                )
                await asyncio.sleep(sleep_time)
            else:
                break

    raise RuntimeError(f"async_is_actionable failed after retries: {last_err}") from last_err
