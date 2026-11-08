from __future__ import annotations

import json
from pathlib import Path


def test_skill_has_positive_negative_and_ordering_evals() -> None:
    root = Path(".agents/skills/sparkollama-private-chat")
    manifest = (root / "SKILL.md").read_text(encoding="utf-8")
    cases = json.loads((root / "evals/cases.json").read_text(encoding="utf-8"))["cases"]
    assert "description:" in manifest and "[TODO" not in manifest
    assert any(case["should_invoke"] for case in cases)
    assert any(not case["should_invoke"] for case in cases)
    assert any("expected_tools" in case or "expected_first_tool" in case for case in cases)
