"""Real GitHub delivery for Understudy.

Gated by GITHUB_ENABLED=true and a token in GITHUB_TOKEN. Targets the repo in
GITHUB_REPO ("owner/name"). Used to turn code/dev action items discussed in a
meeting into a real GitHub issue and a draft pull request (held for approval).

Only uses the standard library + certifi so it adds no new dependencies.
"""

import os
import json
import base64
import logging
import ssl
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any

import certifi

logger = logging.getLogger("understudy.github")

API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())


def is_github_enabled() -> bool:
    """True when real GitHub delivery is turned on and a token is present."""
    enabled = os.getenv("GITHUB_ENABLED", "").lower() in ("1", "true", "yes")
    return enabled and bool(_token())


def _token() -> str:
    return os.getenv("GITHUB_TOKEN", "").strip()


def _repo() -> str:
    return os.getenv("GITHUB_REPO", "").strip()  # "owner/name"


def target_file() -> str:
    """Which file a PR edits by default (kept simple/reliable for the demo)."""
    return os.getenv("GITHUB_TARGET_FILE", "index.html").strip()


def _request(method: str, url: str, body: Optional[dict] = None) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_token()}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "understudy-agent")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"GitHub {method} {url} -> {e.code}: {detail}") from e


# ---------------------------------------------------------------- issues

def create_issue(title: str, body: str, labels: Optional[List[str]] = None) -> Dict[str, Any]:
    """Creates a real GitHub issue. Returns {number, url}."""
    payload: Dict[str, Any] = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    res = _request("POST", f"{API}/repos/{_repo()}/issues", payload)
    logger.info(f"Created GitHub issue #{res.get('number')} -> {res.get('html_url')}")
    return {"number": res.get("number"), "url": res.get("html_url")}


# ------------------------------------------------------------------ repo

def get_default_branch() -> str:
    res = _request("GET", f"{API}/repos/{_repo()}")
    return res.get("default_branch", "main")


def _branch_head_sha(branch: str) -> str:
    res = _request("GET", f"{API}/repos/{_repo()}/git/ref/heads/{branch}")
    return res["object"]["sha"]


def get_file(path: str, ref: Optional[str] = None) -> Dict[str, Any]:
    """Returns {content, sha} for a file (content decoded to text)."""
    url = f"{API}/repos/{_repo()}/contents/{path}"
    if ref:
        url += f"?ref={ref}"
    res = _request("GET", url)
    content = base64.b64decode(res.get("content", "")).decode("utf-8", errors="replace")
    return {"content": content, "sha": res.get("sha")}


def create_branch(new_branch: str, from_sha: str) -> None:
    _request(
        "POST",
        f"{API}/repos/{_repo()}/git/refs",
        {"ref": f"refs/heads/{new_branch}", "sha": from_sha},
    )
    logger.info(f"Created branch '{new_branch}' at {from_sha[:7]}")


def update_file(path: str, new_content: str, message: str, branch: str, sha: str) -> None:
    _request(
        "PUT",
        f"{API}/repos/{_repo()}/contents/{path}",
        {
            "message": message,
            "content": base64.b64encode(new_content.encode()).decode(),
            "branch": branch,
            "sha": sha,
        },
    )
    logger.info(f"Committed change to '{path}' on '{branch}'")


def open_pull_request(title: str, body: str, head: str, base: str, draft: bool = True) -> Dict[str, Any]:
    """Opens a PR (draft by default). Returns {number, url, nodeId}."""
    res = _request(
        "POST",
        f"{API}/repos/{_repo()}/pulls",
        {"title": title, "body": body, "head": head, "base": base, "draft": draft},
    )
    logger.info(f"Opened {'draft ' if draft else ''}PR #{res.get('number')} -> {res.get('html_url')}")
    return {"number": res.get("number"), "url": res.get("html_url"), "nodeId": res.get("node_id")}


def mark_pr_ready(node_id: str) -> None:
    """Converts a draft PR to ready-for-review (GraphQL)."""
    query = (
        "mutation($id:ID!){markPullRequestReadyForReview(input:{pullRequestId:$id})"
        "{pullRequest{isDraft number}}}"
    )
    res = _request("POST", GRAPHQL, {"query": query, "variables": {"id": node_id}})
    if res.get("errors"):
        raise RuntimeError(f"GraphQL markPullRequestReadyForReview failed: {res['errors']}")
    logger.info(f"Marked PR ready for review (node {node_id[:12]}...)")
