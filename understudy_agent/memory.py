"""Cross-meeting semantic memory for Understudy.

Embeds meeting decisions/commitments (Vertex text-embeddings) and stores them in
Firestore. On new action items it recalls semantically-related past context —
"3 weeks ago you decided X" — so Understudy carries context across meetings.

Recall uses in-memory cosine similarity over stored vectors (reliable on the
Firestore emulator, which lacks vector search; swap to findNearest on real
Firestore later).
"""

import math
import logging
from typing import List, Dict, Any, Optional

from understudy_agent import ledger

logger = logging.getLogger("understudy.memory")

EMBED_MODEL = "text-embedding-005"
_client = None


def _genai_client():
    global _client
    if _client is None:
        from understudy_agent.tools.gemini_json import client as gj_client
        _client = gj_client
    return _client


def embed(text: str) -> List[float]:
    """Returns a 768-dim embedding for text (empty list on failure)."""
    try:
        r = _genai_client().models.embed_content(model=EMBED_MODEL, contents=[text])
        return list(r.embeddings[0].values)
    except Exception as e:
        logger.warning(f"embed failed: {e}")
        return []


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def remember(meeting_id: str, meeting_title: str, date: str, text: str, kind: str = "decision") -> None:
    """Stores a memory entry (with embedding) in the top-level 'memory' collection."""
    vec = embed(text)
    if not vec:
        return
    db = ledger.get_db()
    doc_id = f"mem-{abs(hash((meeting_id, text))) % (10**12)}"
    db.collection("memory").document(doc_id).set({
        "id": doc_id,
        "meetingId": meeting_id,
        "meetingTitle": meeting_title,
        "date": date,
        "text": text,
        "kind": kind,
        "embedding": vec,
    })


def recall(query: str, top_k: int = 2, exclude_meeting: Optional[str] = None, min_score: float = 0.62) -> List[Dict[str, Any]]:
    """Returns the most semantically-similar past memory entries to query."""
    qv = embed(query)
    if not qv:
        return []
    db = ledger.get_db()
    hits = []
    for d in db.collection("memory").stream():
        m = d.to_dict()
        if exclude_meeting and m.get("meetingId") == exclude_meeting:
            continue
        score = _cosine(qv, m.get("embedding", []))
        if score >= min_score:
            hits.append({
                "text": m.get("text"),
                "meetingTitle": m.get("meetingTitle"),
                "date": m.get("date"),
                "kind": m.get("kind"),
                "score": round(score, 3),
            })
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:top_k]
