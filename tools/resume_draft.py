#!/usr/bin/env python3
"""Validate a local, evidence-constrained resume draft artifact.

An LLM or a human writes the draft after following ``protocols/tailored-resume.md``.
This program deliberately does not call a model: it is the deterministic gate that
prevents the draft from claiming support outside the reviewed matching artifact.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.evidence_matching import EvidenceMatchingError, validate_matching_result


DRAFT_SCHEMA_VERSION = "resume-draft/v1"


class ResumeDraftError(ValueError):
    """Raised when a local resume draft fails its evidence gate."""


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ResumeDraftError(f"{path} must be an object")
    return value


def _list(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise ResumeDraftError(f"{path} must be an array")
    return value


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResumeDraftError(f"{path} must be a non-empty string")
    return value


def _ids(value: Any, path: str) -> list[str]:
    result = [_string(item, f"{path} item") for item in _list(value, path)]
    if len(result) != len(set(result)):
        raise ResumeDraftError(f"{path} must not contain duplicates")
    return result


def allowed_support(matching: Mapping[str, Any]) -> dict[str, set[str]]:
    """Return requirement-to-evidence allowlists from a validated match artifact."""
    try:
        validate_matching_result(matching)
    except EvidenceMatchingError as error:
        raise ResumeDraftError(f"matching artifact failed validation: {error}") from error
    allowlist: dict[str, set[str]] = {}
    for requirement in matching["requirement_matrix"]:
        if (requirement["evidence_state"] == "supported"
                and requirement["permitted_action"] == "represent_with_evidence"):
            allowlist[requirement["id"]] = set(requirement["evidence_refs"])
    return allowlist


def validate_draft(draft: Mapping[str, Any], matching: Mapping[str, Any]) -> None:
    """Validate that every substantive claim is grounded in permitted support."""
    document = _mapping(draft, "resume_draft")
    if document.get("schema_version") != DRAFT_SCHEMA_VERSION:
        raise ResumeDraftError(f"resume_draft.schema_version must be {DRAFT_SCHEMA_VERSION}")
    _string(document.get("run_id"), "resume_draft.run_id")
    if document["run_id"] != matching.get("run_id"):
        raise ResumeDraftError("resume_draft.run_id must match the matching artifact")
    _string(document.get("version_id"), "resume_draft.version_id")
    _string(document.get("role_target"), "resume_draft.role_target")
    allowlist = allowed_support(matching)
    claims_seen: set[str] = set()
    for position, raw_claim in enumerate(_list(document.get("claims"), "resume_draft.claims")):
        claim = _mapping(raw_claim, f"resume_draft.claims[{position}]")
        claim_id = _string(claim.get("id"), f"resume_draft.claims[{position}].id")
        if claim_id in claims_seen:
            raise ResumeDraftError(f"resume_draft.claims contains duplicate id {claim_id!r}")
        claims_seen.add(claim_id)
        _string(claim.get("section"), f"resume_draft.claims[{claim_id}].section")
        _string(claim.get("text"), f"resume_draft.claims[{claim_id}].text")
        claim_type = claim.get("claim_type")
        if claim_type not in {"substantive", "editorial"}:
            raise ResumeDraftError(f"resume_draft.claims[{claim_id}].claim_type is invalid")
        evidence_refs = _ids(claim.get("evidence_refs"), f"resume_draft.claims[{claim_id}].evidence_refs")
        requirement_refs = _ids(claim.get("requirement_refs"), f"resume_draft.claims[{claim_id}].requirement_refs")
        if claim_type == "substantive":
            if not evidence_refs or not requirement_refs:
                raise ResumeDraftError(f"substantive claim {claim_id!r} needs evidence_refs and requirement_refs")
            unsupported = set(requirement_refs) - set(allowlist)
            if unsupported:
                raise ResumeDraftError(f"claim {claim_id!r} references a requirement not permitted for drafting: {sorted(unsupported)!r}")
            permitted_evidence = set().union(*(allowlist[requirement] for requirement in requirement_refs))
            unknown = set(evidence_refs) - permitted_evidence
            if unknown:
                raise ResumeDraftError(f"claim {claim_id!r} uses evidence not permitted by its supported requirements: {sorted(unknown)!r}")
        elif evidence_refs or requirement_refs:
            raise ResumeDraftError(f"editorial claim {claim_id!r} must not carry substantive references")
    questions = _list(document.get("questions", []), "resume_draft.questions")
    for position, question in enumerate(questions):
        _string(question, f"resume_draft.questions[{position}]")


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ResumeDraftError(f"cannot read JSON artifact {path}: {error}") from error
    return dict(_mapping(value, str(path)))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", required=True, type=Path)
    parser.add_argument("--matching", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        validate_draft(_read(args.draft), _read(args.matching))
        print("Resume draft passed evidence-grounding validation.")
        return 0
    except ResumeDraftError as error:
        print(f"resume-draft: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
