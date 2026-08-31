"""Real Plane (plane.so) delivery for Understudy — Taskmaster work-item tracking.

Turns 'task' action items discussed in a meeting into real Plane work items, and
can advance their state (Todo -> In Progress -> Done) as commitments progress.

Gated by PLANE_ENABLED=true plus PLANE_API_KEY / PLANE_WORKSPACE / PLANE_PROJECT.
Uses only the stdlib + certifi (no new deps).
"""

import os
import json
import ssl
import logging
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List

import certifi

logger = logging.getLogger("understudy.plane")

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())
# Plane's API is behind Cloudflare, which 1010-blocks the default urllib UA.
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_states_cache: Optional[List[Dict[str, Any]]] = None


def is_plane_enabled() -> bool:
    enabled = os.getenv("PLANE_ENABLED", "").lower() in ("1", "true", "yes")
    return enabled and bool(_key()) and bool(_workspace()) and bool(_project())


def _base() -> str:
    return os.getenv("PLANE_BASE_URL", "https://api.plane.so").rstrip("/")


def _key() -> str:
    return os.getenv("PLANE_API_KEY", "").strip()


def _workspace() -> str:
    return os.getenv("PLANE_WORKSPACE", "").strip()


def _project() -> str:
    return os.getenv("PLANE_PROJECT", "").strip()


def issue_url(issue_id: str) -> str:
    return f"https://app.plane.so/{_workspace()}/projects/{_project()}/issues/{issue_id}"


def _request(method: str, path: str, body: Optional[dict] = None) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{_base()}{path}", data=data, method=method)
    req.add_header("X-API-Key", _key())
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", _UA)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"Plane {method} {path} -> {e.code}: {detail}") from e


def _proj_path(suffix: str = "") -> str:
    return f"/api/v1/workspaces/{_workspace()}/projects/{_project()}/{suffix}"


def get_states(force: bool = False) -> List[Dict[str, Any]]:
    """Fetches (and caches) the project's workflow states."""
    global _states_cache
    if _states_cache is not None and not force:
        return _states_cache
    res = _request("GET", _proj_path("states/"))
    _states_cache = res.get("results", res) if isinstance(res, dict) else res
    return _states_cache or []


def state_id_for_group(group: str) -> Optional[str]:
    """Returns a state id for a workflow group, e.g. 'unstarted' (Todo),
    'started' (In Progress), 'completed' (Done)."""
    for s in get_states():
        if s.get("group") == group:
            return s.get("id")
    return None


def create_issue(
    name: str,
    description_html: str = "",
    priority: str = "medium",
    group: str = "unstarted",
) -> Dict[str, Any]:
    """Creates a real Plane work item. Returns {id, sequenceId, url}."""
    body: Dict[str, Any] = {
        "name": name[:250],
        "description_html": description_html or "",
        "priority": priority,
    }
    state = state_id_for_group(group)
    if state:
        body["state"] = state
    res = _request("POST", _proj_path("issues/"), body)
    iid = res.get("id", "")
    logger.info(f"Created Plane issue {res.get('sequence_id')} ({iid})")
    return {"id": iid, "sequenceId": res.get("sequence_id"), "url": issue_url(iid)}


def set_issue_group(issue_id: str, group: str) -> None:
    """Moves an issue to a workflow group (e.g. 'started' or 'completed')."""
    state = state_id_for_group(group)
    if not state:
        return
    _request("PATCH", _proj_path(f"issues/{issue_id}/"), {"state": state})
    logger.info(f"Moved Plane issue {issue_id} -> {group}")
