"""Tests for deterministic reviewed-evidence matching."""

from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from tools.evidence_matching import EvidenceMatchingError, main, match_reviewed_artifacts, validate_matching_result
from tools.job_intake import source_sha256


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def load_json(*parts: str) -> dict:
    return json.loads((FIXTURES.joinpath(*parts)).read_text(encoding="utf-8"))


def load_job_source() -> str:
    return (FIXTURES / "job-intake" / "synthetic-job-description.txt").read_text(encoding="utf-8")


class EvidenceMatchingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidate_review = load_json("evidence-matching", "synthetic-reviewed-candidate.json")
        self.job_review = load_json("job-intake", "valid-review.json")

    def match(self, *, existing_resume: dict | None = None) -> dict:
        return match_reviewed_artifacts(
            self.candidate_review,
            self.job_review,
            job_source_text=load_job_source(),
            existing_resume=existing_resume,
        )

    def test_preserves_reviewed_ids_and_source_references_and_reports_all_states(self) -> None:
        result = self.match()
        validate_matching_result(result)
        self.assertEqual(result, load_json("evidence-matching", "expected-matching.json"))

        records = {record["id"]: record for record in result["requirement_matrix"]}
        self.assertEqual(records["req-001"]["evidence_state"], "supported")
        self.assertEqual(records["req-001"]["coverage_state"], "missing")
        self.assertEqual(records["req-001"]["evidence_refs"], ["ev-pipelines"])
        self.assertEqual(records["req-004"]["evidence_state"], "needs_confirmation")
        self.assertEqual(records["req-004"]["evidence_refs"], ["ev-pipelines", "ev-sql"])
        self.assertEqual(records["req-002"]["evidence_state"], "unsupported")
        self.assertEqual(records["req-002"]["evidence_refs"], [])
        self.assertEqual(records["req-005"]["permitted_action"], "exclude_claim")
        self.assertNotIn("ev-rejected-tool", {item["id"] for item in result["evidence_ledger"]})
        self.assertEqual(
            {item["evidence_id"] for item in result["evidence_source_references"]},
            {"ev-pipelines", "ev-sql", "ev-team-result", "ev-date"},
        )
        self.assertEqual(
            {item["requirement_id"] for item in result["requirement_source_references"]},
            set(records),
        )
        self.assertEqual(result["coverage_report"]["supported_but_missing"], [{"requirement_id": "req-001", "evidence_refs": ["ev-pipelines"]}])

    def test_existing_claim_map_marks_only_evidence_grounded_requirement_as_represented(self) -> None:
        result = self.match(existing_resume=load_json("evidence-matching", "existing-resume.json"))

        record = next(item for item in result["requirement_matrix"] if item["id"] == "req-001")
        self.assertEqual(record["coverage_state"], "represented")
        self.assertEqual(result["coverage_report"]["represented"][0]["claim_ids"], ["claim-pipelines"])

    def test_rejected_tool_cannot_support_a_requirement(self) -> None:
        result = self.match()
        record = next(item for item in result["requirement_matrix"] if item["id"] == "req-004")

        self.assertNotIn("ev-rejected-tool", record["evidence_refs"])
        self.assertIn("workflow orchestration", record["question"])

    def test_unsupported_skill_metric_date_and_ownership_claims_stay_excluded(self) -> None:
        source = "\n".join([
            "Use AWS.",
            "Improve conversion by 25 percent.",
            "Have experience from 2020 to 2023.",
            "Lead a team improvement.",
        ])
        exact_terms = ["AWS", "25 percent", "2020 to 2023", "Lead"]
        requirements = [
            {
                "id": f"req-adversarial-{position}",
                "text": line,
                "priority": "high",
                "exact_terms": [term],
                "evidence_state": "needs_confirmation",
                "coverage_state": "not_applicable",
                "permitted_action": "ask_question",
                "question": "Does the reviewed candidate evidence ledger support this requirement?",
            }
            for position, (line, term) in enumerate(zip(source.splitlines(), exact_terms), start=1)
        ]
        job_review = {
            "schema_version": "job-intake-review/v1",
            "source": {"label": "synthetic-adversarial.txt", "sha256": source_sha256(source), "line_count": 4},
            "review_status": "reviewed",
            "requirement_matrix": requirements,
            "requirement_categories": [
                {"requirement_id": requirement["id"], "category": "must_have"}
                for requirement in requirements
            ],
            "source_references": [
                {"requirement_id": requirement["id"], "start_line": position, "end_line": position}
                for position, requirement in enumerate(requirements, start=1)
            ],
            "domain_terms": [],
            "seniority_signals": [],
        }
        result = match_reviewed_artifacts(self.candidate_review, job_review, job_source_text=source)

        self.assertTrue(all(item["evidence_state"] == "unsupported" for item in result["requirement_matrix"]))
        self.assertTrue(all(item["evidence_refs"] == [] for item in result["requirement_matrix"]))
        self.assertTrue(all(item["permitted_action"] == "exclude_claim" for item in result["requirement_matrix"]))

    def test_validation_rejects_unsupported_requirement_with_evidence(self) -> None:
        result = self.match()
        record = next(item for item in result["requirement_matrix"] if item["id"] == "req-002")
        record["evidence_refs"] = ["ev-pipelines"]

        with self.assertRaisesRegex(EvidenceMatchingError, "unsupported"):
            validate_matching_result(result)

    def test_cli_walkthrough_creates_and_validates_a_local_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "matching.json"
            candidate = FIXTURES / "evidence-matching" / "synthetic-reviewed-candidate.json"
            job_source = FIXTURES / "job-intake" / "synthetic-job-description.txt"
            job_review = FIXTURES / "job-intake" / "valid-review.json"
            self.assertEqual(
                main(["match", "--candidate-review", str(candidate), "--job-source", str(job_source), "--job-review", str(job_review), "--output", str(output)]),
                0,
            )
            self.assertEqual(main(["validate", "--input", str(output)]), 0)

    def test_cli_returns_nonzero_for_unreviewed_candidate_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            candidate = copy.deepcopy(self.candidate_review)
            candidate["review_status"] = "pending"
            candidate_path = temporary / "candidate.json"
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = main([
                    "match", "--candidate-review", str(candidate_path),
                    "--job-source", str(FIXTURES / "job-intake" / "synthetic-job-description.txt"),
                    "--job-review", str(FIXTURES / "job-intake" / "valid-review.json"),
                    "--output", str(temporary / "matching.json"),
                ])
            self.assertEqual(result, 2)
            self.assertIn("reviewed", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
