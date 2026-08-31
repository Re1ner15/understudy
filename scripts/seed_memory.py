"""Seed cross-meeting memory with a few past decisions/commitments so recall
has history to surface during the demo. Run with FIRESTORE_EMULATOR_HOST + project set.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from understudy_agent import memory

PAST = [
    ("m-pricing", "Pricing Strategy", "Aug 12",
     "Decided the Pro tier will launch at $29 per user per month, matching Linear.", "decision"),
    ("m-ux", "UX Review", "Aug 5",
     "Agreed to redesign the onboarding flow down to three screens.", "decision"),
    ("m-launch", "Launch Planning", "Aug 8",
     "Committed to shipping the public launch by the end of the month.", "commitment"),
    ("m-pricing", "Pricing Strategy", "Aug 12",
     "Priya owns sending the pricing recap to the leadership team after each review.", "commitment"),
    ("m-website", "Website Revamp", "Jul 29",
     "Decided the marketing site copy and pricing page must be refreshed before launch.", "decision"),
]

if __name__ == "__main__":
    for mid, title, date, text, kind in PAST:
        memory.remember(mid, title, date, text, kind=kind)
        print(f"remembered: [{title} · {date}] {text[:60]}")
    print(f"\n✅ Seeded {len(PAST)} memory entries.")
