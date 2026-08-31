import os
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

from understudy_agent.ledger import (
    get_db,
    get_commitments,
    update_commitment_follow_up,
)
from understudy_agent.slack_app import post_nudge
from understudy_agent.tracing import span

# Load environment
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

def is_overdue_or_past_due(commitment: Dict[str, Any]) -> bool:
    """Evaluates whether an open/in_progress/overdue commitment is overdue/past due."""
    status = commitment.get("status", "open")
    if status not in ["open", "in_progress", "overdue"]:
        return False
        
    if status == "overdue":
        return True

    due_raw = commitment.get("due")
    if not due_raw:
        return False

    due = due_raw.strip().lower()

    if "overdue" in due or "past due" in due or "yesterday" in due:
        return True

    # "this morning" when current hour is afternoon/evening
    if "this morning" in due:
        now = datetime.now()
        if now.hour >= 12:
            return True

    # Check for relative/absolute date patterns like "Aug 24", "2026-08-24"
    # Example months
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    match = re.search(r'([a-z]{3})\s+(\d{1,2})', due)
    if match:
        mon_str, day_str = match.groups()
        if mon_str in months:
            try:
                mon_idx = months.index(mon_str) + 1
                now = datetime.now()
                # Use current year
                due_date = datetime(now.year, mon_idx, int(day_str))
                # If date is before today
                if due_date.date() < now.date():
                    return True
            except Exception:
                pass

    return False

def scan_and_nudge(channel: Optional[str] = None) -> List[Dict[str, Any]]:
    """Scans Firestore commitments for overdue/open items, sends Slack nudges,

    and updates followUp info and escalation status in the Firestore ledger.
    """
    with span("scanner.scan_and_nudge", scope="commitments") as scan_span:
        print("🔍 Scanning Firestore commitments for overdue items...")
        commitments = get_commitments(status_filter=["open", "in_progress", "overdue"])
        print(f"Found {len(commitments)} candidate commitments.")

        nudged_items: List[Dict[str, Any]] = []

        for item in commitments:
            cid = item.get("id")
            title = item.get("title", "")
            status = item.get("status", "")
            due = item.get("due", "")

            if not is_overdue_or_past_due(item):
                continue

            print(f"👉 Nudging commitment '{cid}': '{title}' (Status: {status}, Due: {due})")
            
            with span(
                "scanner.nudge",
                commitmentId=cid,
                title=title,
                status=status,
                due=due,
                assignee=item.get("assignee"),
            ) as nudge_span:
                # 1. Post nudge to Slack
                try:
                    post_nudge(item, channel=channel)
                except Exception as e:
                    nudge_span.set_status("error", str(e))
                    print(f"❌ Failed to post nudge for {cid} to Slack: {e}")
                    continue

                # 2. Update followUp info in Firestore
                follow_up = item.get("followUp") or {}
                current_nudge_count = follow_up.get("nudgeCount", 0) or 0
                new_nudge_count = current_nudge_count + 1
                last_nudge = datetime.now().strftime("%b %d, %H:%M")

                new_follow_up = dict(follow_up)
                new_follow_up["nudgeCount"] = new_nudge_count
                new_follow_up["lastNudge"] = last_nudge

                if new_nudge_count >= 3:
                    new_follow_up["note"] = "Escalated"
                    new_follow_up["actionType"] = "escalate"
                    print(f"⚠️ Commitment {cid} has reached {new_nudge_count} nudges -> Escalated!")
                else:
                    new_follow_up["note"] = f"Chased {new_nudge_count}×"

                # Update Firestore
                update_commitment_follow_up(
                    commitment_id=cid,
                    follow_up=new_follow_up,
                    status="overdue",
                )

                nudged_items.append({
                    "id": cid,
                    "title": title,
                    "nudgeCount": new_nudge_count,
                    "note": new_follow_up["note"],
                    "status": "overdue",
                })

        scan_span.set_attribute("nudgedCount", len(nudged_items))
        print(f"✅ Scanner finished: {len(nudged_items)} commitments nudged.")
        return nudged_items


if __name__ == "__main__":
    scan_and_nudge()
