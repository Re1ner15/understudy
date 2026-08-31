"""One-shot demo reset for a clean recording run.

- Clears the live board (demo-meeting): actions, transcript, clarifications,
  audit, screenContext, minutes; leaves a fresh 'live' meeting doc, not capturing.
- Deletes all commitments (they only come from prior live runs).
- Deletes ad-hoc concluded meetings (past-*), keeps curated history (m-*).
- Wipes the memory collection, then re-seeds curated history + emails via seed_history.
- Closes Understudy GitHub PRs + issues and deletes understudy/* branches.
- Deletes every issue in the Plane demo project.

Run with the same env as the server (venv/bin/python, FIRESTORE_EMULATOR_HOST, etc.).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from understudy_agent import ledger, github_delivery, plane_delivery

LIVE = "demo-meeting"
KEEP_MEETINGS = {"m-pricing", "m-ux", "m-launch"}


def reset_firestore():
    db = ledger.get_db()

    # 1. Clear the live board and reset it to a fresh, non-capturing meeting.
    ledger.clear_meeting_data(LIVE)
    db.collection("meetings").document(LIVE).set(
        {"id": LIVE, "title": "Weekly Sync", "status": "live", "capturing": False}
    )
    print(f"cleared live board + reset {LIVE} (not capturing)")

    # 2. Delete all commitments.
    n = 0
    for d in db.collection("commitments").stream():
        d.reference.delete()
        n += 1
    print(f"deleted {n} commitments")

    # 3. Delete ad-hoc concluded meetings (keep curated history).
    n = 0
    for d in db.collection("meetings").stream():
        mid = d.id
        if mid == LIVE or mid in KEEP_MEETINGS:
            continue
        ledger.clear_meeting_data(mid)
        d.reference.delete()
        n += 1
    print(f"deleted {n} ad-hoc past meetings")

    # 4. Wipe memory (re-seeded below for deterministic recall).
    n = 0
    for d in db.collection("memory").stream():
        d.reference.delete()
        n += 1
    print(f"wiped {n} memory entries")


def reseed_memory():
    import importlib
    seed = importlib.import_module("scripts.seed_history")
    seed.main()


def reset_github():
    if not github_delivery.is_github_enabled():
        print("github disabled — skipping")
        return
    repo = github_delivery._repo()
    api = github_delivery.API
    req = github_delivery._request

    # Close open PRs (they show up in the pulls endpoint, incl. drafts).
    pulls = req("GET", f"{api}/repos/{repo}/pulls?state=open&per_page=100") or []
    for pr in pulls:
        req("PATCH", f"{api}/repos/{repo}/pulls/{pr['number']}", {"state": "closed"})
    print(f"closed {len(pulls)} PRs")

    # Delete understudy/* branches.
    branches = req("GET", f"{api}/repos/{repo}/branches?per_page=100") or []
    delb = 0
    for b in branches:
        name = b.get("name", "")
        if name.startswith("understudy/"):
            try:
                req("DELETE", f"{api}/repos/{repo}/git/refs/heads/{name}")
                delb += 1
            except Exception as e:
                print(f"  branch {name} delete failed: {e}")
    print(f"deleted {delb} understudy/* branches")

    # Close open issues (skip anything that is actually a PR).
    issues = req("GET", f"{api}/repos/{repo}/issues?state=open&per_page=100") or []
    ni = 0
    for iss in issues:
        if "pull_request" in iss:
            continue
        req("PATCH", f"{api}/repos/{repo}/issues/{iss['number']}", {"state": "closed"})
        ni += 1
    print(f"closed {ni} issues")


def reset_plane():
    if not plane_delivery.is_plane_enabled():
        print("plane disabled — skipping")
        return
    req = plane_delivery._request
    pp = plane_delivery._proj_path
    res = req("GET", pp("issues/?per_page=100"))
    issues = res.get("results", res) if isinstance(res, dict) else res
    issues = issues or []
    n = 0
    for iss in issues:
        iid = iss.get("id")
        if not iid:
            continue
        try:
            req("DELETE", pp(f"issues/{iid}/"))
            n += 1
        except Exception as e:
            print(f"  plane issue {iid} delete failed: {e}")
    print(f"deleted {n} Plane issues")


def main():
    print("=== Firestore ===")
    reset_firestore()
    print("\n=== Re-seed curated history + memory ===")
    reseed_memory()
    print("\n=== GitHub ===")
    reset_github()
    print("\n=== Plane ===")
    reset_plane()
    print("\n✅ Demo reset complete — clean recording state.")


if __name__ == "__main__":
    main()
