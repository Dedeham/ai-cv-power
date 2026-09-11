#!/usr/bin/env python3
"""Match reviewed candidate evidence to reviewed job requirements locally.

This helper is deliberately conservative and dependency-free.  It does not
call a model, network service, shell, or database.  It records only direct,
case-insensitive exact-term evidence found in candidate-reviewed excerpts;
semantic interpretation belongs to the local agent protocol and candidate
confirmation, never to this tool.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools.candidate_intake import CandidateIntakeError, validate_review_packet
from tools.job_intake import JobIntakeValidationError, validate_review


MATCH_SCHEMA_VERSION = "evidence-matching/v1"
SUPPORTED_REVIEW_STATUSES = {"accepted", "corrected"}


class EvidenceMatchingError(ValueError):
    """Raised when matching input or output violates the local protocol."""


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EvidenceMatchingError(f"{path} must be an object")
    return value


def _require_list(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise EvidenceMatchingError(f"{path} must be an array")
    return value


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceMatchingError(f"{path} must be a non-empty string")
    return value


def _term_pattern(term: str) -> re.Pattern[str]:
    """Build a literal phrase matcher without weakening numbers or operators.

    Spaces in an employer term may vary, but punctuation (notably ``+`` in
    ``3+ years``) remains literal.  Word boundaries prevent ``SQL`` from
    silently matching an unrelated longer token such as ``PostgreSQL``.
    """

    escaped = re.escape(term.strip())
    escaped = re.sub(r"(?:\\ )+", r"\\s+", escaped)
    prefix = r"(?<!\\w)" if term[0].isalnum() else ""
    suffix = r"(?!\\w)" if term[-1].isalnum() else ""
    return re.compile(prefix + escaped + suffix, re.IGNORECASE)


def _matches_term(excerpt: str, term: str) -> bool:
    return bool(_term_pattern(term).search(excerpt))


def _accepted_verified_evidence(candidate_review: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Return only evidence allowed to support a new resume claim."""

    review_status_by_evidence = {
        item["evidence_id"]: item["status"]
        for item in candidate_review["review_items"]
    }
    evidence: list[dict[str, Any]] = []
    source_references: dict[str, dict[str, Any]] = {}
    for item in candidate_review["evidence_ledger"]:
        evidence_id = item["id"]
        status = review_status_by_evidence[evidence_id]
        if status not in SUPPORTED_REVIEW_STATUSES:
            continue
        if item["fact_state"] != "verified":
            # validate_review_packet normally makes this impossible for accepted
            # evidence.  Retain this defensive guard because evidence matching
            # is a claim gate, not a best-effort importer.
            raise EvidenceMatchingError(f"accepted evidence {evidence_id!r} must be verified")
        evidence.append(dict(item))
        source_references[evidence_id] = {
            "evidence_id": evidence_id,
            "source_span": dict(next(
                review_item["source_span"]
                for review_item in candidate_review["review_items"]
                if review_item["evidence_id"] == evidence_id
            )),
        }
    return evidence, source_references


def _matching_evidence(exact_terms: Sequence[Any], evidence: Sequence[Mapping[str, Any]]) -> tuple[dict[str, list[str]], list[str]]:
    """Return direct matches for every exact term and their union of IDs."""

    matches: dict[str, list[str]] = {}
    evidence_ids: list[str] = []
    for raw_term in exact_terms:
        term = _require_string(raw_term, "requirement.exact_terms item")
        term_matches = [item["id"] for item in evidence if _matches_term(item["source_excerpt"], term)]
        matches[term] = term_matches
        for evidence_id in term_matches:
            if evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
    return matches, evidence_ids


def _validate_existing_resume(
    existing_resume: Mapping[str, Any] | None,
    evidence_ids: set[str],
    requirement_ids: set[str],
) -> dict[str, Mapping[str, Any]]:
    if existing_resume is None:
        return {}
    _require_string(existing_resume.get("version_id"), "existing_resume.version_id")
    claims_by_id: dict[str, Mapping[str, Any]] = {}
    for position, raw_claim in enumerate(_require_list(existing_resume.get("claims"), "existing_resume.claims")):
        claim = _require_mapping(raw_claim, f"existing_resume.claims[{position}]")
        claim_id = _require_string(claim.get("id"), f"existing_resume.claims[{position}].id")
        if claim_id in claims_by_id:
            raise EvidenceMatchingError(f"existing_resume.claims contains duplicate id {claim_id!r}")
        if claim.get("claim_type") not in {"substantive", "editorial"}:
            raise EvidenceMatchingError(f"existing_resume.claims[{claim_id}].claim_type is invalid")
        evidence_refs = _require_list(claim.get("evidence_refs"), f"existing_resume.claims[{claim_id}].evidence_refs")
        requirement_refs = _require_list(claim.get("requirement_refs"), f"existing_resume.claims[{claim_id}].requirement_refs")
        if claim["claim_type"] == "substantive" and not evidence_refs:
            raise EvidenceMatchingError(f"existing_resume.claims[{claim_id}] substantive claim needs evidence_refs")
        unknown_evidence = set(evidence_refs) - evidence_ids
        if unknown_evidence:
            raise EvidenceMatchingError(
                f"existing_resume.claims[{claim_id}] references evidence outside the reviewed ledger: {sorted(unknown_evidence)!r}"
            )
        unknown_requirements = set(requirement_refs) - requirement_ids
        if unknown_requirements:
            raise EvidenceMatchingError(
                f"existing_resume.claims[{claim_id}] references unknown requirements: {sorted(unknown_requirements)!r}"
            )
        claims_by_id[claim_id] = claim
    return claims_by_id


def match_reviewed_artifacts(
    candidate_review: Mapping[str, Any],
    job_review: Mapping[str, Any],
    *,
    job_source_text: str,
    existing_resume: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a traceable requirement matrix from reviewed local artifacts.

    A requirement is ``supported`` only when every retained exact term has a
    direct match in accepted, verified evidence.  Partial direct coverage is
    deliberately ``needs_confirmation``: it cannot become a claim.  No direct
    coverage is ``unsupported`` and is likewise excluded from claims.
    """

    try:
        validate_review_packet(candidate_review, require_reviewed=True)
    except CandidateIntakeError as error:
        raise EvidenceMatchingError(f"candidate review failed validation: {error}") from error
    try:
        validate_review(job_review, job_source_text)
    except JobIntakeValidationError as error:
        raise EvidenceMatchingError(f"job review failed validation: {error}") from error

    evidence, evidence_source_references = _accepted_verified_evidence(candidate_review)
    requirements = list(job_review["requirement_matrix"])
    requirement_ids = {requirement["id"] for requirement in requirements}
    claims = _validate_existing_resume(existing_resume, {item["id"] for item in evidence}, requirement_ids)

    matrix: list[dict[str, Any]] = []
    supported_missing: list[dict[str, Any]] = []
    represented: list[dict[str, Any]] = []
    questions: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    for requirement in requirements:
        exact_terms = requirement.get("exact_terms", [])
        term_matches, matched_ids = _matching_evidence(exact_terms, evidence)
        all_terms_match = bool(exact_terms) and all(term_matches[term] for term in term_matches)
        partial_terms_match = bool(matched_ids) and not all_terms_match
        record = {
            "id": requirement["id"],
            "text": requirement["text"],
            "priority": requirement["priority"],
            "exact_terms": list(exact_terms),
            "evidence_refs": matched_ids,
        }

        represented_claim_ids = [
            claim_id
            for claim_id, claim in claims.items()
            if requirement["id"] in claim["requirement_refs"]
            and set(claim["evidence_refs"]) & set(matched_ids)
        ]
        if all_terms_match:
            if represented_claim_ids:
                record.update(
                    evidence_state="supported",
                    coverage_state="represented",
                    permitted_action="represent_with_evidence",
                )
                represented.append({
                    "requirement_id": requirement["id"],
                    "evidence_refs": matched_ids,
                    "claim_ids": represented_claim_ids,
                })
            else:
                record.update(
                    evidence_state="supported",
                    coverage_state="missing",
                    permitted_action="represent_with_evidence",
                )
                supported_missing.append({"requirement_id": requirement["id"], "evidence_refs": matched_ids})
        elif partial_terms_match:
            absent_terms = [term for term, ids in term_matches.items() if not ids]
            question = (
                f"The reviewed evidence directly supports {', '.join(term for term, ids in term_matches.items() if ids)}, "
                f"but not {', '.join(absent_terms)}. Can you provide evidence that establishes the missing requirement terms?"
            )
            record.update(
                evidence_state="needs_confirmation",
                coverage_state="not_applicable",
                permitted_action="ask_question",
                question=question,
            )
            questions.append({
                "requirement_id": requirement["id"],
                "evidence_refs": matched_ids,
                "missing_exact_terms": absent_terms,
                "question": question,
            })
        else:
            record.update(
                evidence_state="unsupported",
                coverage_state="not_applicable",
                permitted_action="exclude_claim",
            )
            gaps.append({"requirement_id": requirement["id"], "permitted_action": "exclude_claim"})
        matrix.append(record)

    result = {
        "schema_version": MATCH_SCHEMA_VERSION,
        "run_id": candidate_review["run_id"],
        "candidate_review": {"run_id": candidate_review["run_id"], "review_status": candidate_review["review_status"]},
        "job_review": {"source_sha256": job_review["source"]["sha256"], "review_status": job_review["review_status"]},
        "evidence_ledger": evidence,
        "evidence_source_references": list(evidence_source_references.values()),
        "requirement_matrix": matrix,
        "requirement_source_references": list(job_review["source_references"]),
        "coverage_report": {
            "supported_but_missing": supported_missing,
            "represented": represented,
            "needs_confirmation": questions,
            "unsupported": gaps,
        },
    }
    validate_matching_result(result)
    return result


def validate_matching_result(result: Mapping[str, Any]) -> None:
    """Validate reference preservation and the no-unsupported-claim gate."""

    document = _require_mapping(result, "matching_result")
    if document.get("schema_version") != MATCH_SCHEMA_VERSION:
        raise EvidenceMatchingError(f"matching_result.schema_version must be {MATCH_SCHEMA_VERSION}")
    _require_string(document.get("run_id"), "matching_result.run_id")
    ledger = _require_list(document.get("evidence_ledger"), "matching_result.evidence_ledger")
    evidence_ids = {_require_string(item.get("id"), "matching_result.evidence_ledger.id") for item in ledger if isinstance(item, Mapping)}
    if len(evidence_ids) != len(ledger):
        raise EvidenceMatchingError("matching_result.evidence_ledger must contain unique object IDs")
    source_ref_ids = {
        _require_string(_require_mapping(item, "evidence_source_reference").get("evidence_id"), "evidence_source_reference.evidence_id")
        for item in _require_list(document.get("evidence_source_references"), "matching_result.evidence_source_references")
    }
    if source_ref_ids != evidence_ids:
        raise EvidenceMatchingError("every usable evidence item must retain exactly one source reference")

    matrix = _require_list(document.get("requirement_matrix"), "matching_result.requirement_matrix")
    requirement_ids: set[str] = set()
    for raw_requirement in matrix:
        requirement = _require_mapping(raw_requirement, "matching_result.requirement_matrix item")
        requirement_id = _require_string(requirement.get("id"), "matching_result.requirement_matrix.id")
        if requirement_id in requirement_ids:
            raise EvidenceMatchingError(f"matching_result.requirement_matrix contains duplicate id {requirement_id!r}")
        requirement_ids.add(requirement_id)
        evidence_state = requirement.get("evidence_state")
        coverage_state = requirement.get("coverage_state")
        permitted_action = requirement.get("permitted_action")
        evidence_refs = _require_list(requirement.get("evidence_refs"), f"requirement_matrix[{requirement_id}].evidence_refs")
        unknown_refs = set(evidence_refs) - evidence_ids
        if unknown_refs:
            raise EvidenceMatchingError(f"requirement_matrix[{requirement_id}] has unknown evidence refs {sorted(unknown_refs)!r}")
        if evidence_state == "supported":
            if coverage_state not in {"missing", "represented"} or permitted_action != "represent_with_evidence" or not evidence_refs:
                raise EvidenceMatchingError(f"supported requirement {requirement_id!r} must have evidence and a represent action")
        elif evidence_state == "needs_confirmation":
            if coverage_state != "not_applicable" or permitted_action != "ask_question" or not evidence_refs:
                raise EvidenceMatchingError(f"needs_confirmation requirement {requirement_id!r} must preserve partial evidence and ask")
            _require_string(requirement.get("question"), f"requirement_matrix[{requirement_id}].question")
        elif evidence_state == "unsupported":
            if coverage_state != "not_applicable" or permitted_action != "exclude_claim" or evidence_refs:
                raise EvidenceMatchingError(f"unsupported requirement {requirement_id!r} cannot have evidence or a claim action")
        else:
            raise EvidenceMatchingError(f"requirement_matrix[{requirement_id}].evidence_state is invalid")

    referenced_requirement_ids = {
        _require_string(_require_mapping(item, "requirement_source_reference").get("requirement_id"), "requirement_source_reference.requirement_id")
        for item in _require_list(document.get("requirement_source_references"), "matching_result.requirement_source_references")
    }
    if referenced_requirement_ids != requirement_ids:
        raise EvidenceMatchingError("every requirement must retain one or more job source references")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EvidenceMatchingError(f"cannot read JSON artifact {path}: {error}") from error
    if not isinstance(document, dict):
        raise EvidenceMatchingError(f"JSON artifact {path} must be an object")
    return document


def _write_json(path: Path, document: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    match = commands.add_parser("match", help="match reviewed local artifacts")
    match.add_argument("--candidate-review", required=True, type=Path)
    match.add_argument("--job-source", required=True, type=Path)
    match.add_argument("--job-review", required=True, type=Path)
    match.add_argument("--existing-resume", type=Path, help="optional local resume claim map used only for coverage")
    match.add_argument("--output", required=True, type=Path)
    validate = commands.add_parser("validate", help="validate a matching artifact")
    validate.add_argument("--input", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "match":
            candidate_review = _read_json(args.candidate_review)
            job_review = _read_json(args.job_review)
            job_source_text = args.job_source.read_text(encoding="utf-8")
            existing_resume = _read_json(args.existing_resume) if args.existing_resume else None
            result = match_reviewed_artifacts(
                candidate_review,
                job_review,
                job_source_text=job_source_text,
                existing_resume=existing_resume,
            )
            _write_json(args.output, result)
            print(f"Created local evidence matching artifact: {args.output}")
            return 0
        validate_matching_result(_read_json(args.input))
        print("Evidence matching artifact passed validation.")
        return 0
    except (EvidenceMatchingError, OSError) as error:
        print(f"evidence-matching: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
