"""
Runs the eval dataset against the real extraction service and prints a
scored report.

Usage:
    python -m evals.run_evals

Requires a real GOOGLE_API_KEY in .env - this makes actual Gemini calls
and is meant to be run manually when the extraction prompt/logic changes,
to measure whether accuracy improved or regressed. Not part of the
automated pytest suite (which never makes real API calls).
"""
import sys

from evals.dataset import EVAL_CASES
from evals.scorer import score_case, summarize
from app.services.extraction import extract_obligations_from_text, ExtractionResult


def run() -> int:
    print(f"Running {len(EVAL_CASES)} eval case(s) against the live extraction service...\n")
    print("=" * 70)

    case_results = []
    for case in EVAL_CASES:
        try:
            result: ExtractionResult = extract_obligations_from_text(case.contract_text)
        except Exception as e:
            print(f"[ERROR] {case.name}: extraction call failed - {e}")
            continue

        scored = score_case(case, result)
        case_results.append(scored)

        status = "PASS" if scored.passed else "FAIL"
        adversarial_tag = " [ADVERSARIAL]" if scored.is_adversarial else ""
        print(f"[{status}]{adversarial_tag} {scored.name}")
        print(f"    Expected: {scored.expected_count} | Matched: {scored.matched_count} | Recall: {scored.recall:.0%}")
        if scored.notes:
            print(f"    Notes: {scored.notes}")
        print()

    summary = summarize(case_results)

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Cases passed:        {summary.passed_cases}/{summary.total_cases}")
    print(f"Mean recall:         {summary.mean_recall:.1%}")
    print(f"Adversarial cases:   {summary.adversarial_passed}/{summary.adversarial_cases} passed")
    print()

    if summary.passed_cases < summary.total_cases:
        print("Some cases failed - review notes above before trusting extraction on real contracts.")
        return 1

    print("All eval cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
