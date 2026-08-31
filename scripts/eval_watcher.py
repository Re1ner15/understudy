#!/usr/bin/env python3
"""Evaluation Harness for the Understudy Watcher Agent.

Benchmarks action item extraction against ground-truth fixtures,
measuring Precision, Recall, and F1 per transcript and overall.

Supports --mock mode for offline, billing-free deterministic evaluation.
"""

import os
import sys
import json
import argparse
import difflib
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Ensure project root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from understudy_agent.schemas import ActionItem, ActionItemBatch
except Exception:
    # Graceful fallback if google-adk / pydantic dependencies are in another environment
    from dataclasses import dataclass

    @dataclass
    class ActionItem:
        id: str
        text: str
        category: str
        assignee: Optional[str] = None
        due: Optional[str] = None
        source_quote: str = ""
        confidence: float = 1.0

    @dataclass
    class ActionItemBatch:
        items: list

# Common stopwords to remove during key noun and semantic fuzzy matching
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "so", "as", "at",
    "by", "for", "from", "in", "into", "of", "off", "on", "onto", "out",
    "over", "to", "up", "with", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "can", "could",
    "will", "would", "shall", "should", "may", "might", "must", "let",
    "lets", "i", "you", "he", "she", "it", "we", "they", "me", "him",
    "her", "us", "them", "my", "your", "his", "their", "our", "its",
    "this", "that", "these", "those", "just", "also", "please", "make",
    "sure", "want", "need", "like", "get", "got", "well", "all", "today",
    "morning", "afternoon", "right", "now", "here", "there"
}


# ----------------------------------------------------------------------
# Mock / Canned Extraction Data
# ----------------------------------------------------------------------

def get_canned_mock_eval_items(transcript_name: str) -> List[ActionItem]:
    """Returns realistic canned ActionItem extractions for evaluation fixtures."""
    name = transcript_name.lower()
    if "standup" in name:
        return [
            ActionItem(
                id="ai-1",
                text="Fix the redis caching memory leak on the worker node",
                category="task",
                assignee="Maya",
                due="today",
                source_quote="I will fix the redis caching memory leak on the worker node today so it doesn't crash tonight's batch jobs.",
                confidence=0.96,
            ),
            ActionItem(
                id="ai-2",
                text="Update runbook on cache cluster failover procedures",
                category="doc",
                assignee="Maya",
                due="this afternoon",
                source_quote="I'll update the runbook doc by this afternoon.",
                confidence=0.94,
            ),
            ActionItem(
                id="ai-3",
                text="Schedule architecture deep dive on Redis eviction policies for Wednesday at 3pm",
                category="calendar",
                assignee="David",
                due="Wednesday at 3pm",
                source_quote="Let's schedule an architecture deep dive on Redis eviction policies for Wednesday at 3pm with the backend team.",
                confidence=0.95,
            ),
            ActionItem(
                id="ai-4",
                text="Post updated deployment schedule to #releases Slack channel",
                category="slack",
                assignee="Priya",
                due="right after call",
                source_quote="I'll post the updated deployment schedule to the #releases Slack channel right after this call.",
                confidence=0.95,
            ),
        ]
    elif "sales" in name:
        return [
            ActionItem(
                id="ai-1",
                text="Email Rachel the SOC2 compliance report and enterprise pricing tier breakdown",
                category="email",
                assignee="Marcus",
                due="this afternoon",
                source_quote="I'll email you the SOC2 compliance report and enterprise pricing tier breakdown this afternoon, Rachel.",
                confidence=0.95,
            ),
            ActionItem(
                id="ai-2",
                text="Research webhook delivery latency metrics and benchmark against 99.99% SLA requirement",
                category="research",
                assignee="Elena",
                due=None,
                source_quote="I will research our webhook delivery latency metrics and benchmark them against your 99.99% SLA requirement",
                confidence=0.92,
            ),
            ActionItem(
                id="ai-3",
                text="Draft a custom proof-of-concept scope document for FintechCorp",
                category="doc",
                assignee="Elena",
                due="Thursday",
                source_quote="I'll draft a custom proof-of-concept scope document for FintechCorp outlining the pilot deliverables by Thursday.",
                confidence=0.94,
            ),
            ActionItem(
                id="ai-4",
                text="Schedule technical deep dive demo with SecOps team for next Tuesday at 11am",
                category="calendar",
                assignee="Marcus",
                due="next Tuesday at 11am",
                source_quote="Let's schedule a technical deep dive demo with your SecOps team for next Tuesday at 11am.",
                confidence=0.96,
            ),
        ]
    elif "one_on_one" in name or "1" in name:
        return [
            ActionItem(
                id="ai-1",
                text="Draft Q4 career development plan with specific skill milestones",
                category="doc",
                assignee="Liam",
                due="Friday",
                source_quote="I'll write up that career development plan doc by Friday.",
                confidence=0.93,
            ),
            ActionItem(
                id="ai-2",
                text="Email HR regarding travel budget approval for Liam to attend PyCon",
                category="email",
                assignee="Sarah",
                due="today",
                source_quote="I'll email HR today regarding travel budget approval for PyCon so we can lock in the early bird registration.",
                confidence=0.95,
            ),
            ActionItem(
                id="ai-3",
                text="Schedule bi-weekly mentorship recurring sync with Marcus",
                category="calendar",
                assignee="Sarah",
                due=None,
                source_quote="I will schedule a bi-weekly mentorship recurring sync with Marcus for you.",
                confidence=0.94,
            ),
            ActionItem(
                id="ai-4",
                text="Review and approve telemetry metrics refactor pull request",
                category="task",
                assignee="Sarah",
                due="end of day",
                source_quote="I'll review and approve your telemetry refactor pull request before end of day.",
                confidence=0.95,
            ),
        ]
    elif "planning" in name:
        return [
            ActionItem(
                id="ai-1",
                text="Research mobile onboarding drop-off patterns and benchmark competitor flows",
                category="research",
                assignee="Ben",
                due="Wednesday",
                source_quote="I'll pull together a competitive benchmark research brief by Wednesday.",
                confidence=0.93,
            ),
            ActionItem(
                id="ai-2",
                text="Finalize PRD specifications for multi-tenant workspace feature",
                category="doc",
                assignee="Jordan",
                due="tomorrow morning",
                source_quote="I will finalize the PRD specifications for the multi-tenant workspace feature by tomorrow morning.",
                confidence=0.95,
            ),
            ActionItem(
                id="ai-3",
                text="Create Jira sprint backlog tickets for auth migration milestone",
                category="task",
                assignee="Chloe",
                due=None,
                source_quote="I will create the Jira sprint backlog tickets for the auth migration milestone and break them down into subtasks.",
                confidence=0.94,
            ),
            ActionItem(
                id="ai-4",
                text="Share finalized sprint goals and timeline in #product-announcements Slack channel",
                category="slack",
                assignee="Jordan",
                due="Friday",
                source_quote="I'll share the finalized sprint goals and timeline in the #product-announcements Slack channel for the whole company.",
                confidence=0.95,
            ),
        ]
    else:
        # Generic fallback mock extraction
        return [
            ActionItem(
                id="ai-1",
                text=f"Action item extracted from {transcript_name}",
                category="task",
                assignee=None,
                source_quote="Discussion in transcript",
                confidence=0.9,
            )
        ]


# ----------------------------------------------------------------------
# Fuzzy Matching Engine
# ----------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """Lowercases text and strips non-alphanumeric characters."""
    return re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()


def extract_keywords(text: str) -> set[str]:
    """Extracts informative nouns and keyword tokens, omitting common stopwords."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def compute_item_similarity(expected: Dict[str, Any], extracted: ActionItem) -> float:
    """Calculates fuzzy similarity between an expected item and an extracted item.

    Matches on:
    1. Category (must match exactly or heavily penalized).
    2. Key noun / keyword overlap (Jaccard similarity + token containment).
    3. Sequence similarity ratio on normalized text.
    4. Assignee consistency.
    """
    # 1. Strict Category Match
    expected_cat = expected.get("category", "").lower().strip()
    extracted_cat = extracted.category.lower().strip()
    if expected_cat != extracted_cat:
        return 0.0

    # 2. Text Keyword and Semantic Overlap
    exp_text = expected.get("text", "")
    ext_text = extracted.text

    exp_clean = normalize_text(exp_text)
    ext_clean = normalize_text(ext_text)

    exp_keywords = extract_keywords(exp_text)
    ext_keywords = extract_keywords(ext_text)

    if not exp_keywords or not ext_keywords:
        # Fallback to direct string similarity if keyword sets are empty
        return difflib.SequenceMatcher(None, exp_clean, ext_clean).ratio()

    overlap = len(exp_keywords & ext_keywords)
    union = len(exp_keywords | ext_keywords)
    min_len = min(len(exp_keywords), len(ext_keywords))

    jaccard = overlap / union if union > 0 else 0.0
    containment = overlap / min_len if min_len > 0 else 0.0
    seq_ratio = difflib.SequenceMatcher(None, exp_clean, ext_clean).ratio()

    # Blend semantic keyword overlap and full phrase alignment
    text_score = (0.40 * jaccard) + (0.35 * containment) + (0.25 * seq_ratio)

    # 3. Assignee matching adjustment
    exp_assignee = expected.get("assignee")
    ext_assignee = extracted.assignee

    if exp_assignee and ext_assignee:
        exp_a_clean = exp_assignee.lower().strip()
        ext_a_clean = ext_assignee.lower().strip()
        if exp_a_clean in ext_a_clean or ext_a_clean in exp_a_clean:
            text_score += 0.08
        else:
            text_score -= 0.15

    return max(0.0, min(1.0, text_score))


def match_action_items(
    expected_items: List[Dict[str, Any]],
    extracted_items: List[ActionItem],
    threshold: float = 0.35,
) -> Tuple[List[Tuple[Dict[str, Any], ActionItem, float]], List[Dict[str, Any]], List[ActionItem]]:
    """Performs greedy optimal bipartite matching between expected and extracted items."""
    # Compute pairwise similarity matrix
    candidates = []
    for exp_idx, exp in enumerate(expected_items):
        for ext_idx, ext in enumerate(extracted_items):
            score = compute_item_similarity(exp, ext)
            if score >= threshold:
                candidates.append((score, exp_idx, ext_idx))

    # Sort pairs by descending similarity score
    candidates.sort(key=lambda x: x[0], reverse=True)

    matched_pairs: List[Tuple[Dict[str, Any], ActionItem, float]] = []
    matched_exp_indices = set()
    matched_ext_indices = set()

    for score, exp_idx, ext_idx in candidates:
        if exp_idx not in matched_exp_indices and ext_idx not in matched_ext_indices:
            matched_exp_indices.add(exp_idx)
            matched_ext_indices.add(ext_idx)
            matched_pairs.append((expected_items[exp_idx], extracted_items[ext_idx], score))

    unmatched_expected = [
        exp for i, exp in enumerate(expected_items) if i not in matched_exp_indices
    ]
    unmatched_extracted = [
        ext for j, ext in enumerate(extracted_items) if j not in matched_ext_indices
    ]

    return matched_pairs, unmatched_expected, unmatched_extracted


# ----------------------------------------------------------------------
# Metrics Calculation
# ----------------------------------------------------------------------

def calculate_metrics(tp: int, fp: int, fn: int) -> Tuple[float, float, float]:
    """Calculates Precision, Recall, and F1 given TP, FP, FN counts."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if (tp + fn) == 0 else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if (tp + fp) == 0 else 0.0)
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


# ----------------------------------------------------------------------
# Watcher Agent Execution
# ----------------------------------------------------------------------

async def run_live_watcher(transcript: str) -> List[ActionItem]:
    """Runs the live Watcher LLM Agent using Google ADK InMemoryRunner."""
    from google.adk.runners import InMemoryRunner
    from understudy_agent.watcher import watcher

    runner = InMemoryRunner(agent=watcher)
    events = await runner.run_debug(transcript)

    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    try:
                        batch = ActionItemBatch.model_validate_json(part.text)
                        return batch.items
                    except Exception:
                        pass
        if hasattr(event, "output") and event.output is not None:
            if isinstance(event.output, ActionItemBatch):
                return event.output.items
            elif isinstance(event.output, str):
                try:
                    batch = ActionItemBatch.model_validate_json(event.output)
                    return batch.items
                except Exception:
                    pass
    return []


# ----------------------------------------------------------------------
# Main Runner & CLI
# ----------------------------------------------------------------------

def load_eval_fixtures(eval_dir: Path) -> List[Tuple[str, str, List[Dict[str, Any]]]]:
    """Finds and loads all paired *.txt and *.expected.json fixtures in eval_dir."""
    fixtures = []
    txt_files = sorted(eval_dir.glob("*.txt"))
    for txt_path in txt_files:
        stem = txt_path.stem
        expected_path = txt_path.with_suffix(".expected.json")
        if not expected_path.exists():
            continue

        with open(txt_path, "r", encoding="utf-8") as f:
            transcript = f.read()

        with open(expected_path, "r", encoding="utf-8") as f:
            expected_items = json.load(f)

        fixtures.append((stem, transcript, expected_items))

    return fixtures


def main():
    parser = argparse.ArgumentParser(
        description="Understudy Watcher Evaluation Harness - Benchmarks Action Item Extraction."
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode with deterministic canned outputs (billing-free).",
    )
    parser.add_argument(
        "--eval-dir",
        type=str,
        default=str(ROOT_DIR / "understudy_agent" / "fixtures" / "eval"),
        help="Path to evaluation fixtures directory.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.35,
        help="Similarity score threshold for fuzzy matching (default: 0.35).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Display detailed match and item breakdown for each transcript.",
    )

    args = parser.parse_args()

    eval_dir = Path(args.eval_dir)
    if not eval_dir.exists():
        print(f"❌ Error: Evaluation fixtures directory '{eval_dir}' does not exist.")
        sys.exit(1)

    fixtures = load_eval_fixtures(eval_dir)
    if not fixtures:
        print(f"❌ Error: No paired *.txt and *.expected.json files found in '{eval_dir}'.")
        sys.exit(1)

    mode_str = "MOCK (Billing-free)" if args.mock else "LIVE (Gemini LLM Agent)"
    print("=" * 84)
    print(f"🔍 UNDERSTUDY WATCHER EVALUATION HARNESS")
    print(f"Mode:              {mode_str}")
    print(f"Fixtures Dir:      {eval_dir}")
    print(f"Match Threshold:   {args.threshold}")
    print("=" * 84)

    results = []
    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_expected = 0
    total_extracted = 0

    import asyncio

    for name, transcript, expected_items in fixtures:
        if args.mock:
            extracted_items = get_canned_mock_eval_items(name)
        else:
            extracted_items = asyncio.run(run_live_watcher(transcript))

        matched_pairs, unmatched_exp, unmatched_ext = match_action_items(
            expected_items, extracted_items, threshold=args.threshold
        )

        tp = len(matched_pairs)
        fp = len(unmatched_ext)
        fn = len(unmatched_exp)

        precision, recall, f1 = calculate_metrics(tp, fp, fn)

        results.append({
            "name": name,
            "expected_count": len(expected_items),
            "extracted_count": len(extracted_items),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "matched_pairs": matched_pairs,
            "unmatched_exp": unmatched_exp,
            "unmatched_ext": unmatched_ext,
        })

        total_tp += tp
        total_fp += fp
        total_fn += fn
        total_expected += len(expected_items)
        total_extracted += len(extracted_items)

    # Print summary table
    print()
    header = f"| {'Transcript':<18} | {'Exp':<5} | {'Ext':<5} | {'TP':<4} | {'FP':<4} | {'FN':<4} | {'Precision':<10} | {'Recall':<10} | {'F1 Score':<10} |"
    divider = f"|{'-' * 20}|{'-' * 7}|{'-' * 7}|{'-' * 6}|{'-' * 6}|{'-' * 6}|{'-' * 12}|{'-' * 12}|{'-' * 12}|"

    print(divider)
    print(header)
    print(divider)

    for r in results:
        prec_str = f"{r['precision'] * 100:>6.1f}%"
        rec_str = f"{r['recall'] * 100:>6.1f}%"
        f1_str = f"{r['f1'] * 100:>6.1f}%"
        row = f"| {r['name']:<18} | {r['expected_count']:<5} | {r['extracted_count']:<5} | {r['tp']:<4} | {r['fp']:<4} | {r['fn']:<4} | {prec_str:<10} | {rec_str:<10} | {f1_str:<10} |"
        print(row)

    print(divider)

    # Micro-average overall metrics
    overall_prec, overall_rec, overall_f1 = calculate_metrics(total_tp, total_fp, total_fn)
    overall_row = f"| {'OVERALL (Micro)':<18} | {total_expected:<5} | {total_extracted:<5} | {total_tp:<4} | {total_fp:<4} | {total_fn:<4} | {overall_prec * 100:>6.1f}%     | {overall_rec * 100:>6.1f}%     | {overall_f1 * 100:>6.1f}%     |"
    print(overall_row)
    print(divider)

    # Verbose breakdown if requested
    if args.verbose:
        print("\n" + "=" * 84)
        print("📋 DETAILED EXTRACTION & MATCH BREAKDOWN")
        print("=" * 84)
        for r in results:
            print(f"\n--- [{r['name'].upper()}] ---")
            print(f"Matched Pairs ({len(r['matched_pairs'])}):")
            for exp, ext, score in r["matched_pairs"]:
                print(f"  ✅ [{score:.2f}] Category: {ext.category:<8} | Assignee: {ext.assignee or '-'}")
                print(f"      Expected:  {exp.get('text')}")
                print(f"      Extracted: {ext.text}")

            if r["unmatched_ext"]:
                print(f"False Positives ({len(r['unmatched_ext'])}):")
                for ext in r["unmatched_ext"]:
                    print(f"  ⚠️  [{ext.category}] {ext.text} (Assignee: {ext.assignee or '-'})")

            if r["unmatched_exp"]:
                print(f"False Negatives ({len(r['unmatched_exp'])}):")
                for exp in r["unmatched_exp"]:
                    print(f"  ❌ [{exp.get('category')}] {exp.get('text')} (Assignee: {exp.get('assignee') or '-'})")

    print("\n✅ Evaluation run completed successfully.")


if __name__ == "__main__":
    main()
