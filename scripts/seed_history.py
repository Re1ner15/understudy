"""Seed past meetings (Firestore docs + transcripts + minutes) AND ingest their
transcripts + related emails into cross-meeting memory, so:
  - the History screen shows rich, believable past meetings, and
  - live recall surfaces context "from a past transcript" and "from an email".

Run with FIRESTORE_EMULATOR_HOST + GOOGLE_CLOUD_PROJECT set.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from understudy_agent import ledger, memory

ATTENDEES = ["Ranjit", "Matthew", "Priya"]

PAST_MEETINGS = [
    {
        "id": "m-pricing", "title": "Pricing Strategy", "date": "Aug 12",
        "transcript": [
            ("Priya", "Let's lock the Pro tier price before the launch — leadership wants a number today."),
            ("Ranjit", "Linear is at $29 per user on their standard tier, and it's their most popular plan."),
            ("Priya", "Notion's Plus is $10 but their Business tier is $20 with SSO gated above that."),
            ("Matthew", "Our feature set maps closest to Linear's standard — parity there makes sense."),
            ("Ranjit", "Agreed. For our Pro tier let's match Linear at $29 per user per month."),
            ("Priya", "Keep Starter free but cap it at 5 seats so teams upgrade when they grow."),
            ("Matthew", "And annual billing at two months free — roughly a 17% discount — to pull cash forward."),
            ("Ranjit", "Good. I'll get the pricing page updated; Priya, send the recap to leadership."),
        ],
        "minutes": {
            "decisions": [
                "Launch the Pro tier at $29/user/month, matching Linear's standard plan.",
                "Keep the Starter tier free with a 5-seat cap to drive top-of-funnel growth.",
                "Offer annual billing at ~17% off (two months free) to accelerate cash collection.",
            ],
            "topics": [
                {"heading": "Competitor pricing",
                 "notes": "Benchmarked against Notion (Plus $10 / Business $20, SSO gated above) and Linear ($29 standard). Our feature set maps closest to Linear's standard tier, so price parity there is defensible to customers."},
                {"heading": "Tier structure",
                 "notes": "Free Starter capped at 5 seats as an acquisition funnel; Pro at $29 as the primary revenue tier; Enterprise left for custom pricing with SSO/SCIM."},
                {"heading": "Billing & discounts",
                 "notes": "Introduce annual billing with two months free (~17%). Monthly stays available. No launch-week promo — hold price integrity."},
            ],
            "materialsShown": [
                "Slide: Competitor Pricing Matrix — Notion vs Linear vs Us",
                "Doc: Pro Tier Revenue Model v3 (ARR sensitivity)",
            ],
            "actionItems": [
                {"id": "h-pr-1", "text": "Update the pricing page to show the new $29 Pro tier", "category": "code", "assignee": "Ranjit", "due": "this week"},
                {"id": "h-pr-2", "text": "Draft the pricing FAQ for the sales team", "category": "doc", "assignee": "Matthew", "due": None},
                {"id": "h-pr-3", "text": "Send the pricing recap to leadership", "category": "email", "assignee": "Priya", "due": "today"},
            ],
        },
        "memory": [
            ("Decided the Pro tier will launch at $29 per user per month, matching Linear.", "decision"),
            ("Keep the Starter tier free with a 5-seat cap; annual billing gives two months free (~17% off).", "decision"),
            ("Discussed Notion Plus at $10 and Business at $20 versus Linear at $29 before choosing Pro pricing.", "transcript"),
        ],
    },
    {
        "id": "m-ux", "title": "UX Review", "date": "Aug 5",
        "transcript": [
            ("Priya", "The onboarding has too many steps right now — we're losing people at step four."),
            ("Ranjit", "Let's cut it down to three screens: sign-up, workspace, invite."),
            ("Matthew", "Usability test #4 showed the same drop-off — three screens tested much better."),
            ("Priya", "Perfect, three screens it is. I'll write the spec."),
            ("Ranjit", "The dashboard also feels cluttered, but that's a bigger job."),
            ("Matthew", "Let's defer the dashboard redesign to next quarter and focus on onboarding now."),
        ],
        "minutes": {
            "decisions": [
                "Redesign the onboarding flow down to three screens: sign-up, workspace, invite.",
                "Defer the full dashboard redesign to next quarter.",
            ],
            "topics": [
                {"heading": "Onboarding flow",
                 "notes": "Current flow loses users at step four. Agreed to reduce to three screens: sign-up, workspace setup, invite teammates. Usability test #4 supports the shorter flow."},
                {"heading": "Dashboard clutter",
                 "notes": "Dashboard information density is high but a redesign is out of scope this cycle. Deferred to next quarter to keep focus on onboarding conversion."},
            ],
            "materialsShown": [
                "Figma: Onboarding v2 — 3-screen flow",
                "Recording: Usability Test Session #4",
            ],
            "actionItems": [
                {"id": "h-ux-1", "text": "Write the one-page onboarding spec for the three screens", "category": "doc", "assignee": "Priya", "due": "this week"},
                {"id": "h-ux-2", "text": "Prototype the new invite screen in Figma", "category": "task", "assignee": "Matthew", "due": None},
            ],
        },
        "memory": [
            ("Agreed to redesign the onboarding flow down to three screens.", "decision"),
            ("Onboarding will be sign-up, workspace setup, and invite teammates — three screens total.", "transcript"),
            ("Deferred the dashboard redesign to next quarter to focus on onboarding conversion.", "decision"),
        ],
    },
    {
        "id": "m-launch", "title": "Launch Planning", "date": "Aug 8",
        "transcript": [
            ("Ranjit", "When are we committing to the public launch?"),
            ("Priya", "Let's ship by the end of the month — support and docs will be ready."),
            ("Ranjit", "Okay, end of month is the target. Let's freeze features a week before."),
            ("Matthew", "I'd do a staged rollout — 10 percent, then 50, then 100 — so we can catch issues."),
            ("Priya", "Agreed. I'll own the launch-day support rota."),
            ("Ranjit", "I'll wire up the rollout flags; Matthew, you take the announcement post."),
        ],
        "minutes": {
            "decisions": [
                "Ship the public launch by the end of the month.",
                "Freeze new features one week before launch.",
                "Roll out in stages: 10% → 50% → 100% of traffic.",
            ],
            "topics": [
                {"heading": "Launch timeline",
                 "notes": "Committed to shipping the public launch by end of month, with a feature freeze one week prior to stabilize the build."},
                {"heading": "Go / no-go criteria",
                 "notes": "Launch gated on: zero P0 bugs open, support docs published, and on-call rota staffed. A go/no-go review happens 48 hours before."},
                {"heading": "Rollout plan",
                 "notes": "Staged rollout behind flags — 10% then 50% then 100% — with a one-hour soak and error-rate check between each step."},
            ],
            "materialsShown": [
                "Doc: Launch Runbook v1",
                "Sheet: Go/No-Go Checklist",
            ],
            "actionItems": [
                {"id": "h-la-1", "text": "Set up the staged rollout feature flags", "category": "code", "assignee": "Ranjit", "due": None},
                {"id": "h-la-2", "text": "Prepare the launch announcement blog post", "category": "doc", "assignee": "Matthew", "due": "before launch"},
                {"id": "h-la-3", "text": "Coordinate the launch-day support rota", "category": "task", "assignee": "Priya", "due": None},
            ],
        },
        "memory": [
            ("Committed to shipping the public launch by the end of the month.", "commitment"),
            ("Launch will use a staged rollout: 10% then 50% then 100%, with a feature freeze one week prior.", "decision"),
        ],
    },
]

# Curated emails ingested into memory (kind='email').
EMAILS = [
    ("Email from Priya", "Aug 13", "Leadership confirmed the Pro tier at $29/user — please include it in the pricing recap and update the page.", "email"),
    ("Email from IT Vendor", "Aug 14", "Quote attached for two MacBook Pros for the new hires; the budget is approved, ship this week.", "email"),
    ("Email from Design", "Aug 6", "Onboarding mockups v2 attached — three screens (sign-up, workspace, invite) as discussed.", "email"),
]


def main():
    db = ledger.get_db()
    for mtg in PAST_MEETINGS:
        mref = db.collection("meetings").document(mtg["id"])
        mref.set({"id": mtg["id"], "title": mtg["title"], "date": mtg["date"], "status": "ended"})
        # transcript
        for i, (spk, txt) in enumerate(mtg["transcript"]):
            ts = f"1{i}:0{i}:00"[:8]
            mref.collection("transcript").document(f"tl-{mtg['id']}-{i}").set(
                {"id": f"tl-{mtg['id']}-{i}", "speaker": spk, "text": txt, "ts": ts}
            )
        # minutes (rich: attendees, decisions, topics, materials, action items)
        mn = mtg["minutes"]
        mref.collection("minutes").document("latest").set({
            "title": mtg["title"], "date": mtg["date"], "attendees": ATTENDEES,
            "topics": mn["topics"], "decisions": mn["decisions"],
            "materialsShown": mn.get("materialsShown", []),
            "actionItems": mn.get("actionItems", []),
        })
        # memory (decisions + transcript context)
        for text, kind in mtg["memory"]:
            memory.remember(mtg["id"], mtg["title"], mtg["date"], text, kind=kind)
        print(f"seeded meeting + memory: {mtg['title']} ({mtg['date']})")

    for title, date, text, kind in EMAILS:
        memory.remember(f"email-{abs(hash(text))%9999}", title, date, text, kind=kind)
        print(f"seeded email memory: {title} ({date})")

    total = len(list(db.collection("memory").stream()))
    print(f"\n✅ Seeded {len(PAST_MEETINGS)} past meetings + {len(EMAILS)} emails. Memory entries: {total}")


if __name__ == "__main__":
    main()
