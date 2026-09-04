"""
Guards the AI-security hardening in the extraction prompt.

This doesn't call the real Gemini API (that's what evals/run_evals.py's
prompt_injection_attempt case is for) - it just verifies the prompt template
itself still contains the untrusted-data framing and delimiters, so a future
edit to extraction.py can't silently strip this protection without a test
failing.
"""
from app.services.extraction import EXTRACTION_PROMPT


def test_prompt_frames_contract_text_as_untrusted_data():
    rendered = EXTRACTION_PROMPT.format(contract_text="anything")
    assert "untrusted" in rendered.lower()


def test_prompt_delimits_contract_text_clearly():
    rendered = EXTRACTION_PROMPT.format(contract_text="anything")
    assert "<contract_text>" in rendered
    assert "</contract_text>" in rendered


def test_prompt_warns_about_embedded_instructions():
    rendered = EXTRACTION_PROMPT.format(contract_text="anything")
    # Doesn't need to match exact wording - just confirms the model is told
    # that instruction-like text inside the document isn't a real instruction
    assert "ignore previous instructions" in rendered.lower() or "instruction" in rendered.lower()
