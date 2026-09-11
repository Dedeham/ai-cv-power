"""Contract tests for the local, agent-first resume protocol."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from contracts.v1.validate import ContractValidationError, validate_protocol_run


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "contracts"


def load_fixture(category: str, name: str) -> dict:
    return json.loads((FIXTURES / category / name).read_text(encoding="utf-8"))


class ContractValidationTests(unittest.TestCase):
    def test_representative_protocol_run_is_valid_and_round_trips(self) -> None:
        run = load_fixture("valid", "protocol-run.json")

        validate_protocol_run(run)

        restored = json.loads(json.dumps(run, sort_keys=True))
        validate_protocol_run(restored)

    def test_substantive_claim_requires_evidence(self) -> None:
        run = load_fixture("invalid", "substantive-claim-without-evidence.json")

        with self.assertRaisesRegex(ContractValidationError, "evidence_refs"):
            validate_protocol_run(run)

    def test_unsupported_requirement_cannot_be_represented(self) -> None:
        run = load_fixture("invalid", "unsupported-requirement-represented.json")

        with self.assertRaisesRegex(ContractValidationError, "unsupported"):
            validate_protocol_run(run)

    def test_claim_cannot_reference_unknown_evidence(self) -> None:
        run = load_fixture("invalid", "unknown-evidence-reference.json")

        with self.assertRaisesRegex(ContractValidationError, "unknown evidence"):
            validate_protocol_run(run)

    def test_approved_version_must_match_resume_version(self) -> None:
        run = load_fixture("invalid", "approval-for-wrong-version.json")

        with self.assertRaisesRegex(ContractValidationError, "final_version"):
            validate_protocol_run(run)


if __name__ == "__main__":
    unittest.main()
