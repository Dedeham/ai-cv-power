"""Tests for the local evidence gate applied to LLM-authored draft artifacts."""

from __future__ import annotations

import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.resume_draft import ResumeDraftError, validate_draft

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def load(*parts: str) -> dict:
    return json.loads(FIXTURES.joinpath(*parts).read_text(encoding="utf-8"))


class ResumeDraftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.matching = load("evidence-matching", "expected-matching.json")
        self.draft = load("resume-draft", "synthetic-draft.json")

    def test_grounded_draft_is_valid(self) -> None:
        validate_draft(self.draft, self.matching)

    def test_rejects_unsupported_requirement_even_if_claim_has_an_evidence_id(self) -> None:
        draft = copy.deepcopy(self.draft)
        draft["claims"][0]["requirement_refs"] = ["req-002"]
        with self.assertRaisesRegex(ResumeDraftError, "not permitted"):
            validate_draft(draft, self.matching)

    def test_rejects_claim_that_smuggles_a_metric_or_unrelated_evidence(self) -> None:
        draft = copy.deepcopy(self.draft)
        draft["claims"][0]["evidence_refs"] = ["ev-team-result"]
        with self.assertRaisesRegex(ResumeDraftError, "not permitted"):
            validate_draft(draft, self.matching)

    def test_cli_walkthrough(self) -> None:
        command = ["python3", "tools/resume_draft.py", "--draft", str(FIXTURES / "resume-draft" / "synthetic-draft.json"), "--matching", str(FIXTURES / "evidence-matching" / "expected-matching.json")]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
