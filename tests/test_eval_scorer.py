"""
Tests for the eval scoring logic itself, using hand-built synthetic
ExtractionResult objects - no real Gemini API calls. This verifies the
scoring harness is correct independent of actual model quality, so when
evals/run_evals.py reports a score against the real API, we can trust the
number reflects real extraction accuracy and not a bug in how we grade it.
"""
from datetime import date, datetime

from evals.dataset import EvalCase, ExpectedObligation
from evals.scorer import score_case, summarize
from app.services.extraction import ExtractedObligation, ExtractionResult


def make_obligation(deadline_str, description, penalty=None):
    return ExtractedObligation(
        description=description,
        deadline=datetime.fromisoformat(deadline_str),
        penalty_amount=penalty,
    )


def test_exact_match_passes():
    case = EvalCase(
        name="test",
        contract_text="...",
        expected_obligations=[
            ExpectedObligation(deadline=date(2027, 3, 15), penalty_amount=5000.0, description_keywords=["deliver"])
        ],
    )
    result = ExtractionResult(obligations=[
        make_obligation("2027-03-15T00:00:00", "Vendor must deliver the goods", penalty=5000.0)
    ])
    scored = score_case(case, result)
    assert scored.passed is True
    assert scored.recall == 1.0
    assert scored.matched_count == 1


def test_wrong_deadline_fails():
    case = EvalCase(
        name="test",
        contract_text="...",
        expected_obligations=[ExpectedObligation(deadline=date(2027, 3, 15))],
    )
    result = ExtractionResult(obligations=[
        make_obligation("2027-03-16T00:00:00", "Vendor must deliver the goods")  # off by one day
    ])
    scored = score_case(case, result)
    assert scored.passed is False
    assert scored.recall == 0.0


def test_wrong_penalty_fails():
    case = EvalCase(
        name="test",
        contract_text="...",
        expected_obligations=[ExpectedObligation(deadline=date(2027, 3, 15), penalty_amount=5000.0)],
    )
    result = ExtractionResult(obligations=[
        make_obligation("2027-03-15T00:00:00", "Deliver goods", penalty=1000.0)  # wrong amount
    ])
    scored = score_case(case, result)
    assert scored.passed is False


def test_missing_keyword_fails():
    case = EvalCase(
        name="test",
        contract_text="...",
        expected_obligations=[ExpectedObligation(deadline=date(2027, 3, 15), description_keywords=["audit"])],
    )
    result = ExtractionResult(obligations=[
        make_obligation("2027-03-15T00:00:00", "Vendor must deliver the goods")  # no "audit" mention
    ])
    scored = score_case(case, result)
    assert scored.passed is False


def test_partial_recall_on_multiple_expected():
    case = EvalCase(
        name="test",
        contract_text="...",
        expected_obligations=[
            ExpectedObligation(deadline=date(2027, 1, 1)),
            ExpectedObligation(deadline=date(2027, 2, 1)),
        ],
    )
    # Only one of the two expected obligations shows up in the extraction
    result = ExtractionResult(obligations=[
        make_obligation("2027-01-01T00:00:00", "First obligation"),
    ])
    scored = score_case(case, result)
    assert scored.matched_count == 1
    assert scored.recall == 0.5
    assert scored.passed is False  # partial recall still counts as a failed case


def test_expect_empty_passes_when_nothing_extracted():
    case = EvalCase(name="test", contract_text="...", expect_empty=True)
    result = ExtractionResult(obligations=[])
    scored = score_case(case, result)
    assert scored.passed is True


def test_expect_empty_fails_on_hallucination():
    case = EvalCase(name="test", contract_text="...", expect_empty=True)
    result = ExtractionResult(obligations=[
        make_obligation("2027-01-01T00:00:00", "Hallucinated obligation that shouldn't exist")
    ])
    scored = score_case(case, result)
    assert scored.passed is False
    assert "FALSE POSITIVE" in scored.notes


def test_extra_obligations_do_not_block_a_pass():
    """Extra extracted obligations beyond what's expected are noted but
    don't fail the case on their own - recall (finding what's expected)
    is the hard requirement; over-extraction is a softer signal."""
    case = EvalCase(
        name="test",
        contract_text="...",
        expected_obligations=[ExpectedObligation(deadline=date(2027, 1, 1))],
    )
    result = ExtractionResult(obligations=[
        make_obligation("2027-01-01T00:00:00", "Expected obligation"),
        make_obligation("2027-06-01T00:00:00", "Some extra obligation not in the expected set"),
    ])
    scored = score_case(case, result)
    assert scored.passed is True
    assert scored.extra_extracted == 1


def test_summarize_aggregates_correctly():
    case_a = EvalCase(name="a", contract_text="...", expected_obligations=[ExpectedObligation(deadline=date(2027, 1, 1))])
    case_b = EvalCase(name="b", contract_text="...", expect_empty=True, is_adversarial=True)

    result_a = ExtractionResult(obligations=[make_obligation("2027-01-01T00:00:00", "Match")])
    result_b = ExtractionResult(obligations=[])

    scored = [score_case(case_a, result_a), score_case(case_b, result_b)]
    summary = summarize(scored)

    assert summary.total_cases == 2
    assert summary.passed_cases == 2
    assert summary.mean_recall == 1.0
    assert summary.adversarial_cases == 1
    assert summary.adversarial_passed == 1
