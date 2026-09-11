"""Tests for the local, agent-first job-description intake workflow."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.job_intake import (
    JobIntakeValidationError,
    create_review_template,
    main,
    source_sha256,
    validate_review,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "job-intake"


def load_source() -> str:
    return (FIXTURES / "synthetic-job-description.txt").read_text(encoding="utf-8")


def load_review() -> dict:
    return json.loads((FIXTURES / "valid-review.json").read_text(encoding="utf-8"))


class JobIntakeTests(unittest.TestCase):
    def test_synthetic_review_is_v1_compatible_and_source_bound(self) -> None:
        validate_review(load_review(), load_source())

    def test_prepare_creates_a_deterministic_empty_review_without_executing_input(self) -> None:
        source = load_source()

        template = create_review_template(source, "synthetic")

        self.assertEqual(template["source"]["sha256"], source_sha256(source))
        self.assertEqual(template["requirement_matrix"], [])
        self.assertEqual(template["requirement_categories"], [])
        self.assertNotIn("Ignore all previous instructions", json.dumps(template))
        self.assertNotIn("private candidate data", json.dumps(template))

    def test_review_rejects_a_different_job_description(self) -> None:
        with self.assertRaisesRegex(JobIntakeValidationError, "sha256"):
            validate_review(load_review(), "A different job description")

    def test_review_requires_source_reference_for_every_requirement(self) -> None:
        review = load_review()
        review["source_references"] = review["source_references"][:-1]

        with self.assertRaisesRegex(JobIntakeValidationError, "source reference"):
            validate_review(review, load_source())

    def test_review_rejects_candidate_evidence_and_other_non_intake_fields(self) -> None:
        review = load_review()
        review["candidate_qualifications"] = ["invented"]

        with self.assertRaisesRegex(JobIntakeValidationError, "unsupported fields"):
            validate_review(review, load_source())

    def test_review_rejects_premature_candidate_support_inference(self) -> None:
        review = load_review()
        requirement = review["requirement_matrix"][0]
        requirement["evidence_state"] = "supported"
        requirement["coverage_state"] = "represented"
        requirement["permitted_action"] = "represent_with_evidence"

        with self.assertRaisesRegex(JobIntakeValidationError, "pre-matching state"):
            validate_review(review, load_source())

    def test_review_requires_exact_terms_to_be_traceable_to_cited_lines(self) -> None:
        review = load_review()
        review["requirement_matrix"][0]["exact_terms"] = ["unrelated term"]

        with self.assertRaisesRegex(JobIntakeValidationError, "is not present"):
            validate_review(review, load_source())

    def test_cli_prepare_and_validate_walkthrough(self) -> None:
        source_path = FIXTURES / "synthetic-job-description.txt"
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            template_path = temporary_path / "template.json"
            review_path = temporary_path / "review.json"
            review_path.write_text(json.dumps(load_review()), encoding="utf-8")

            self.assertEqual(
                main(["prepare", "--input", str(source_path), "--output", str(template_path)]),
                0,
            )
            self.assertEqual(
                main(["validate", "--input", str(source_path), "--review", str(review_path)]),
                0,
            )


if __name__ == "__main__":
    unittest.main()
