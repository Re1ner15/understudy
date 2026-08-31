import sys
import argparse
from pathlib import Path

# Ensure workspace root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from understudy_agent.gemma_filter import is_actionable


def run_tests(mock: bool = True, model_id: str | None = None) -> bool:
    test_cases = [
        # Explicit required acceptance cases
        ("I'll email the vendor", True),
        ("how was your weekend", False),
        
        # Additional actionable cases
        ("Can you schedule a follow-up with design by Thursday?", True),
        ("I will draft the technical architecture doc today.", True),
        ("Let's ping Slack channel #dev-alerts about the deploy status.", True),
        ("We should create a Jira ticket for this auth bug.", True),
        ("I'm going to review the pull request before EOD.", True),
        
        # Additional non-actionable chatter cases
        ("The weather is really nice today.", False),
        ("Good morning everyone, glad you could make it.", False),
        ("Yeah I totally agree with that point.", False),
        ("Thanks everyone for joining, see you next time!", False),
        ("Did anyone watch the game last night?", False),
    ]

    print("=" * 80)
    mode_str = "MOCK (Local heuristic)" if mock else f"LIVE (Model: {model_id or 'default'})"
    print(f"🧪 Testing Gemma First-Pass Filter [{mode_str}]")
    print("=" * 80)
    print(f"{'Utterance':<50} | {'Expected':<10} | {'Actual':<10} | {'Conf':<6} | {'Status'}")
    print("-" * 80)

    all_passed = True

    for utterance, expected in test_cases:
        try:
            result = is_actionable(utterance, mock=mock, model_id=model_id)
            actual = result.get("actionable")
            conf = result.get("confidence", 0.0)

            status = "✅ PASS" if actual == expected else "❌ FAIL"
            if actual != expected:
                all_passed = False

            display_utt = (utterance[:47] + "...") if len(utterance) > 50 else utterance
            print(f"{display_utt:<50} | {str(expected):<10} | {str(actual):<10} | {conf:<6.2f} | {status}")
        except Exception as e:
            print(f"{utterance:<50} | {str(expected):<10} | {'ERROR':<10} | {'N/A':<6} | ❌ ERROR: {e}")
            all_passed = False

    print("-" * 80)
    
    # Specific assertions for acceptance verification
    vendor_result = is_actionable("I'll email the vendor", mock=mock, model_id=model_id)
    weekend_result = is_actionable("how was your weekend", mock=mock, model_id=model_id)

    assert vendor_result["actionable"] is True, f"Expected 'I\\'ll email the vendor' to be actionable, got {vendor_result}"
    assert weekend_result["actionable"] is False, f"Expected 'how was your weekend' to be non-actionable, got {weekend_result}"

    if all_passed:
        print("🎉 All test cases passed successfully!")
    else:
        print("❌ Some test cases failed.")

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Test Gemma First-Pass Filter")
    parser.add_argument(
        "--mock",
        action="store_true",
        default=False,
        help="Use mock canned path (no live LLM / Vertex call)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Gemma model ID override (for live calls)",
    )
    parser.add_argument(
        "--utterance",
        type=str,
        default=None,
        help="Test a single utterance",
    )

    args = parser.parse_args()

    if args.utterance:
        res = is_actionable(args.utterance, mock=args.mock, model_id=args.model)
        print(f"Utterance: {args.utterance}")
        print(f"Result:    Actionable = {res['actionable']} (confidence = {res['confidence']:.2f})")
        sys.exit(0)

    success = run_tests(mock=args.mock, model_id=args.model)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
