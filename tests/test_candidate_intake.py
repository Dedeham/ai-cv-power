"""Tests for the local, protocol-first candidate intake helper."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools.candidate_intake import (
    CandidateIntakeError,
    build_review_packet,
    main,
    validate_review_packet,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "candidate-intake" / "synthetic-master-cv.tex"


class CandidateIntakeTests(unittest.TestCase):
    def test_builds_pending_contract_compatible_evidence_candidates_with_source_spans(self) -> None:
        packet = build_review_packet(FIXTURE.read_text(encoding="utf-8"), "fixture-run")

        self.assertEqual(packet["schema_version"], "candidate-intake/v1")
        self.assertEqual(packet["run_id"], "fixture-run")
        self.assertEqual(packet["review_status"], "pending")
        self.assertGreaterEqual(len(packet["evidence_ledger"]), 3)
        self.assertEqual(len(packet["evidence_ledger"]), len(packet["review_items"]))

        for evidence, review_item in zip(packet["evidence_ledger"], packet["review_items"]):
            self.assertEqual(evidence["id"], review_item["evidence_id"])
            self.assertEqual(evidence["fact_state"], "possible")
            self.assertTrue(evidence["confirmation_question"])
            self.assertEqual(review_item["status"], "needs_candidate_review")
            self.assertGreaterEqual(review_item["source_span"]["line_start"], 1)
            self.assertGreaterEqual(review_item["source_span"]["line_end"], review_item["source_span"]["line_start"])
            self.assertTrue(review_item["allowed_wording"])

    def test_reviewed_packet_requires_every_candidate_to_be_confirmed_or_rejected(self) -> None:
        packet = build_review_packet(FIXTURE.read_text(encoding="utf-8"), "fixture-run")
        packet["review_status"] = "reviewed"

        with self.assertRaisesRegex(CandidateIntakeError, "needs_candidate_review"):
            validate_review_packet(packet, require_reviewed=True)

        for evidence, review_item in zip(packet["evidence_ledger"], packet["review_items"]):
            review_item["status"] = "accepted"
            evidence["fact_state"] = "verified"
            evidence.pop("confirmation_question")

        validate_review_packet(packet, require_reviewed=True)

    def test_rejects_reviewed_unknown_or_unmatched_evidence(self) -> None:
        packet = build_review_packet(FIXTURE.read_text(encoding="utf-8"), "fixture-run")
        packet["review_status"] = "reviewed"
        for evidence, review_item in zip(packet["evidence_ledger"], packet["review_items"]):
            review_item["status"] = "accepted"
            evidence["fact_state"] = "verified"
            evidence.pop("confirmation_question")
        packet["evidence_ledger"][0]["fact_state"] = "unknown"

        with self.assertRaisesRegex(CandidateIntakeError, "unknown"):
            validate_review_packet(packet, require_reviewed=True)

    def test_cli_accepts_pasted_text_and_writes_only_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "candidate-intake.json"
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch("sys.stdin", io.StringIO("Example role\\n- Coordinated sample work\\n")):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    result = main(
                        [
                            "prepare",
                            "--stdin",
                            "--run-id",
                            "pasted-run",
                            "--output",
                            str(output_path),
                        ]
                    )

            self.assertEqual(result, 0, stderr.getvalue())
            self.assertIn("review packet", stdout.getvalue())
            packet = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(packet["run_id"], "pasted-run")

    def test_cli_accepts_an_ignored_private_source_and_output_path(self) -> None:
        private_directory = ROOT / "private-cv"
        private_directory.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private_directory) as temporary_directory:
            source_path = Path(temporary_directory) / "master_cv.txt"
            output_path = Path(temporary_directory) / "candidate-intake.json"
            source_path.write_text("Example analyst role\\n- Prepared sample reports\\n", encoding="utf-8")

            result = main(
                [
                    "prepare",
                    "--input",
                    str(source_path),
                    "--run-id",
                    "private-run",
                    "--output",
                    str(output_path),
                ]
            )

            self.assertEqual(result, 0)
            self.assertTrue(output_path.is_file())

    def test_cli_rejects_tracked_repository_input_and_pdf_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "candidate-intake.json"
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = main(
                    [
                        "prepare",
                        "--input",
                        str(FIXTURE),
                        "--run-id",
                        "fixture-run",
                        "--output",
                        str(output_path),
                    ]
                )
            self.assertEqual(result, 2)
            self.assertIn("ignored local folder", stderr.getvalue())

            pdf_path = Path(temporary_directory) / "source.pdf"
            pdf_path.write_bytes(b"not a PDF parser test")
            with redirect_stderr(stderr):
                result = main(
                    [
                        "prepare",
                        "--input",
                        str(pdf_path),
                        "--run-id",
                        "pdf-run",
                        "--output",
                        str(output_path),
                    ]
                )
            self.assertEqual(result, 2)
            self.assertIn("plain-text, Markdown, and LaTeX-like", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
