import re
from typing import Optional, Union, Dict, Any, List
from understudy_agent.schemas import GuardrailResult, ActionItem, LiveAction

# ----------------------------------------------------------------------
# Rule-Based PII & Secret Detection Patterns
# ----------------------------------------------------------------------

# Emails: standard RFC-compliant pattern
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)

# Phone Numbers: require real phone formatting (separators / parens / +country)
# so bare digit runs inside UUIDs, PR ids, or keys don't false-positive.
PHONE_PATTERN = re.compile(
    r"(?:\+\d{1,3}[\s.-]?)?(?:\(\d{3}\)\s?|\d{3}[\s.-])\d{3}[\s.-]\d{4}\b"
)

# High-entropy API Keys / Tokens / Secrets
SECRET_PATTERNS = [
    # Google API Key (e.g. AIzaSy...)
    (re.compile(r"\bAIza[0-9A-Za-z-_]{35}\b"), "Google API key (AIza...)"),
    # OpenAI / Anthropic / general sk- tokens
    (re.compile(r"\bsk-(?:proj-)?[a-zA-Z0-9_\-]{20,}\b"), "OpenAI/API secret key (sk-...)"),
    # GitHub Personal Access Tokens
    (re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36,}\b"), "GitHub access token (gh*_)"),
    # AWS Access Key ID
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "AWS Access Key ID (AKIA/ASIA...)"),
    # Private Key blocks
    (re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"), "Private key block"),
    # Bearer / Auth tokens
    (re.compile(r"\bBearer\s+[A-Za-z0-9\-_\.=]{20,}\b", re.IGNORECASE), "Bearer authorization token"),
    # Generic key / secret / password assignments
    (
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-\.]{8,}['\"]?"
        ),
        "Secret/API key or password credential assignment",
    ),
    # US Social Security Number
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "Social Security Number (SSN)"),
    # Credit Card numbers (13-19 digits with spaces or hyphens)
    (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "Credit card number"),
]

# ----------------------------------------------------------------------
# Rule-Based Prompt Injection & Unsafe Command Patterns
# ----------------------------------------------------------------------

INJECTION_PATTERNS = [
    # Override / ignore instructions
    (
        re.compile(
            r"(?i)\b(?:ignore|disregard|forget|override)\s+(?:all\s+)?(?:previous|prior|above|former|earlier)\s+(?:instructions|rules|prompts|system\s+prompts|context|constraints)\b"
        ),
        "Prompt injection: instruction to ignore/override prior instructions",
    ),
    (
        re.compile(r"(?i)\b(?:ignore\s+that\s+and|forget\s+that\s+and)\s+(?:email|send|post|delete|execute|run)\b"),
        "Prompt injection: conversational bypass directive ('ignore that and...')",
    ),
    (
        re.compile(r"(?i)\b(?:ignore\s+previous|disregard\s+previous)\b"),
        "Prompt injection: instruction to ignore previous context",
    ),
    (
        re.compile(r"(?i)\bdo\s+not\s+follow\s+(?:previous|prior)\s+instructions\b"),
        "Prompt injection: directive to disregard instructions",
    ),
    # Mass broadcasting / Uncontrolled blast
    (
        re.compile(
            r"(?i)\b(?:email|mail|blast|message|ping|slack|send)\s+(?:(?:an?\s+)?(?:email|message|note|update|blast)\s+)?(?:to\s+)?(?:the\s+)?(?:whole|all|entire|every)\s+(?:company|org|organization|team|employees|everyone|everybody|all-hands)\b"
        ),
        "This would message the entire company/org — confirm the audience before it goes out",
    ),
    (
        re.compile(r"(?i)\b(?:email|message|blast|send\s+(?:an?\s+)?(?:email|message))\s+(?:to\s+)?(?:everyone|everybody|all)\b"),
        "This would email everyone — confirm the recipients before sending",
    ),
    (
        re.compile(r"(?i)\b(?:slack|ping)\s+@(?:everyone|channel|here)\b"),
        "Mass broadcast risk: wide Slack broadcast tag (@everyone / @channel)",
    ),
    # Data exfiltration / External transmission
    (
        re.compile(
            r"(?i)\b(?:send|exfiltrate|forward|leak|upload|post)\s+(?:all\s+)?(?:data|secrets|keys|passwords|database|creds|credentials|tokens|files|customer\s+data|everything)\s+(?:to\s+)?(?:external|<external>|attacker|public|dropbox|pastebin)"
        ),
        "Exfiltration risk: directive to send data or secrets to external recipient",
    ),
    (
        re.compile(r"(?i)\bsend\s+(?:all\s+)?(?:data\s+)?to\s+<external>"),
        "Exfiltration risk: directive to send to <external>",
    ),
    (
        re.compile(r"(?i)\b(?:exfiltrate|data\s+leakage)\b"),
        "Exfiltration risk: exfiltration keyword",
    ),
    # Sharing credentials by INTENT — catches "post the production API key in the
    # channel" even when no literal key value is spoken, so the guardrail holds it.
    (
        re.compile(
            r"(?i)\b(?:post|share|send|email|drop|paste|put|publish|upload|expose|reveal)\b[^.\n]{0,40}?\b(?:api[\s_-]?keys?|secrets?|passwords?|credentials?|access[\s_-]?tokens?|private[\s_-]?keys?)\b"
        ),
        "This would share a credential (API key / secret / password) — held for your review before it goes anywhere",
    ),
    # Jailbreak / System Prompt manipulation
    (
        re.compile(
            r"(?i)\b(?:you\s+are\s+now|act\s+as)\s+(?:in\s+)?(?:developer\s+mode|dan|jailbreak|unrestricted|sudo\s+mode|admin\s+mode)\b"
        ),
        "Jailbreak attempt: persona/developer mode override",
    ),
    (
        re.compile(r"(?i)\b(?:system\s+override|admin\s+override|developer\s+override)\b"),
        "System override attempt",
    ),
    (
        re.compile(r"(?i)\b(?:tool\s+poisoning|poison\s+the\s+tool|bypass\s+guardrails?|disable\s+safety)\b"),
        "Tool poisoning / guardrail bypass attempt",
    ),
    # Dangerous system commands
    (
        re.compile(r"(?i)\b(?:rm\s+-rf|drop\s+database|format\s+c:|delete\s+from\s+users)\b"),
        "Destructive command execution attempt",
    ),
]


def scan_for_pii(text: Optional[str]) -> Dict[str, Any]:
    """Scans text for PII (emails, phone numbers) and secrets/API keys.
    
    Returns:
        Dict with 'safe': bool, 'reasons': list[str]
    """
    if not text:
        return {"safe": True, "reasons": []}

    # Strip URLs first — delivery artifacts embed Plane/GitHub links whose UUIDs
    # and ids would otherwise false-positive as phone numbers/secrets.
    text = re.sub(r"https?://\S+", " ", text)

    reasons: List[str] = []

    # 1. Check for API keys and secrets
    for pattern, description in SECRET_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            reasons.append(f"Looks like it contains a real credential ({description}) — confirm before sharing")

    # 2. Check for email addresses in content
    email_matches = EMAIL_PATTERN.findall(text)
    if email_matches:
        reasons.append(f"Contains a personal email address ({', '.join(set(email_matches[:2]))}) — confirm before sending")

    # 3. Check for phone numbers
    phone_matches = PHONE_PATTERN.findall(text)
    if phone_matches:
        reasons.append(f"Contains what looks like a phone number ({', '.join(set(phone_matches[:2]))}) — confirm before sharing")

    is_safe = (len(reasons) == 0)
    return {"safe": is_safe, "reasons": reasons}


def detect_injection(transcript_text: Optional[str]) -> Dict[str, Any]:
    """Scans transcript or action text for prompt injection, jailbreak attempts,
    mass broadcasting, or data exfiltration directives.
    
    Returns:
        Dict with 'safe': bool, 'reasons': list[str]
    """
    if not transcript_text:
        return {"safe": True, "reasons": []}

    reasons: List[str] = []

    for pattern, description in INJECTION_PATTERNS:
        if pattern.search(transcript_text):
            reasons.append(description)

    is_safe = (len(reasons) == 0)
    return {"safe": is_safe, "reasons": reasons}


def guard_action(
    action: Union[ActionItem, LiveAction, Dict[str, Any], str],
    artifact: Optional[str] = None,
    transcript: Optional[str] = None,
) -> GuardrailResult:
    """Evaluates an action and optional drafted artifact/transcript against
    Model Armor safety rules (PII, secret leak, prompt injection, broadcast risks).
    
    Returns:
        GuardrailResult(safe=bool, reasons=list[str])
    """
    reasons: List[str] = []

    # Extract text components from action
    action_text = ""
    source_quote = ""
    action_artifact = ""

    if isinstance(action, ActionItem):
        action_text = action.text
        source_quote = action.source_quote
    elif isinstance(action, LiveAction):
        action_text = action.title
        source_quote = action.reasoning
        action_artifact = action.artifact or ""
    elif isinstance(action, dict):
        action_text = action.get("text") or action.get("title") or ""
        source_quote = action.get("source_quote") or action.get("sourceQuote") or action.get("reasoning") or ""
        action_artifact = action.get("artifact") or ""
    elif isinstance(action, str):
        action_text = action

    # Scope the checks to THIS action's own content (title, the sentence it came
    # from, and its drafted output) — NOT the whole meeting transcript. Otherwise
    # one risky phrase anywhere in the meeting would flag every single action.
    combined = "\n".join(t for t in (action_text, source_quote, action_artifact, artifact) if t)

    injection_res = detect_injection(combined)
    if not injection_res["safe"]:
        reasons.extend(injection_res["reasons"])

    pii_res = scan_for_pii(combined)
    if not pii_res["safe"]:
        reasons.extend(pii_res["reasons"])

    # De-duplicate while preserving order.
    seen = set()
    reasons = [r for r in reasons if not (r in seen or seen.add(r))]

    is_safe = (len(reasons) == 0)
    return GuardrailResult(safe=is_safe, reasons=reasons)
