"""Dependency-free validation for the portable protocol-run contract."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class ContractValidationError(ValueError):
    """Raised when a protocol artifact violates a required contract rule."""


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractValidationError(f"{path} must be an object")
    return value


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"{path} must be a non-empty string")
    return value


def _require_list(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise ContractValidationError(f"{path} must be an array")
    return value


def _index_by_id(records: Sequence[Any], path: str) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for position, raw_record in enumerate(records):
        record = _require_mapping(raw_record, f"{path}[{position}]")
        record_id = _require_string(record.get("id"), f"{path}[{position}].id")
        if record_id in indexed:
            raise ContractValidationError(f"{path} contains duplicate id {record_id!r}")
        indexed[record_id] = record
    return indexed


def validate_protocol_run(run: Mapping[str, Any]) -> None:
    """Validate a complete local protocol run and its cross-record invariants.

    This deliberately uses only the Python standard library so agents can validate
    file artifacts before any framework, database, or model provider is selected.
    JSON Schema files alongside this module describe the portable wire format.
    """

    document = _require_mapping(run, "protocol_run")
    if document.get("schema_version") != "resume-tailoring/v1":
        raise ContractValidationError("protocol_run.schema_version must be resume-tailoring/v1")
    _require_string(document.get("run_id"), "protocol_run.run_id")

    ledger = _index_by_id(_require_list(document.get("evidence_ledger"), "evidence_ledger"), "evidence_ledger")
    requirements = _index_by_id(
        _require_list(document.get("requirement_matrix"), "requirement_matrix"),
        "requirement_matrix",
    )
    resume = _require_mapping(document.get("tailored_resume"), "tailored_resume")
    _require_string(resume.get("version_id"), "tailored_resume.version_id")
    claims = _index_by_id(_require_list(resume.get("claims"), "tailored_resume.claims"), "tailored_resume.claims")

    _validate_ledger(ledger)
    _validate_requirements(requirements)
    _validate_claims(claims, ledger, requirements)
    _validate_defects(_require_list(document.get("defect_queue"), "defect_queue"), claims)
    _validate_verification(_require_mapping(document.get("verification_report"), "verification_report"))
    _validate_audit(_require_list(document.get("revision_history"), "revision_history"), claims)
    _validate_approval(_require_mapping(document.get("approval_record"), "approval_record"), resume)


def _validate_ledger(ledger: Mapping[str, Mapping[str, Any]]) -> None:
    allowed_fact_states = {"verified", "possible", "unknown"}
    for evidence_id, item in ledger.items():
        _require_string(item.get("source_excerpt"), f"evidence_ledger[{evidence_id}].source_excerpt")
        if item.get("fact_state") not in allowed_fact_states:
            raise ContractValidationError(f"evidence_ledger[{evidence_id}].fact_state is invalid")
        if item.get("fact_state") == "possible" and not item.get("confirmation_question"):
            raise ContractValidationError(
                f"evidence_ledger[{evidence_id}] possible facts require confirmation_question"
            )


def _validate_requirements(requirements: Mapping[str, Mapping[str, Any]]) -> None:
    allowed_states = {
        ("supported", "represented"),
        ("supported", "missing"),
        ("needs_confirmation", "not_applicable"),
        ("unsupported", "not_applicable"),
    }
    for requirement_id, requirement in requirements.items():
        _require_string(requirement.get("text"), f"requirement_matrix[{requirement_id}].text")
        if requirement.get("priority") not in {"critical", "high", "medium", "low"}:
            raise ContractValidationError(f"requirement_matrix[{requirement_id}].priority is invalid")
        pair = (requirement.get("evidence_state"), requirement.get("coverage_state"))
        if pair not in allowed_states:
            raise ContractValidationError(
                f"requirement_matrix[{requirement_id}] has inconsistent evidence/coverage states: {pair}"
            )
        if requirement.get("evidence_state") == "needs_confirmation" and not requirement.get("question"):
            raise ContractValidationError(
                f"requirement_matrix[{requirement_id}] needs_confirmation requires question"
            )


def _validate_claims(
    claims: Mapping[str, Mapping[str, Any]],
    ledger: Mapping[str, Mapping[str, Any]],
    requirements: Mapping[str, Mapping[str, Any]],
) -> None:
    for claim_id, claim in claims.items():
        _require_string(claim.get("text"), f"tailored_resume.claims[{claim_id}].text")
        claim_type = claim.get("claim_type")
        if claim_type not in {"substantive", "editorial"}:
            raise ContractValidationError(f"tailored_resume.claims[{claim_id}].claim_type is invalid")
        evidence_refs = _require_list(claim.get("evidence_refs"), f"tailored_resume.claims[{claim_id}].evidence_refs")
        if claim_type == "substantive" and not evidence_refs:
            raise ContractValidationError(f"tailored_resume.claims[{claim_id}] substantive claims require evidence_refs")
        for evidence_id in evidence_refs:
            if evidence_id not in ledger:
                raise ContractValidationError(f"tailored_resume.claims[{claim_id}] references unknown evidence {evidence_id!r}")
            if ledger[evidence_id]["fact_state"] == "unknown":
                raise ContractValidationError(f"tailored_resume.claims[{claim_id}] cannot use unknown evidence {evidence_id!r}")
        for requirement_id in _require_list(claim.get("requirement_refs"), f"tailored_resume.claims[{claim_id}].requirement_refs"):
            if requirement_id not in requirements:
                raise ContractValidationError(f"tailored_resume.claims[{claim_id}] references unknown requirement {requirement_id!r}")
            if requirements[requirement_id]["evidence_state"] == "unsupported":
                raise ContractValidationError(f"tailored_resume.claims[{claim_id}] cannot represent unsupported requirement {requirement_id!r}")


def _validate_defects(defects: Sequence[Any], claims: Mapping[str, Mapping[str, Any]]) -> None:
    for position, raw_defect in enumerate(defects):
        defect = _require_mapping(raw_defect, f"defect_queue[{position}]")
        if defect.get("severity") not in {"critical", "high", "medium", "low"}:
            raise ContractValidationError(f"defect_queue[{position}].severity is invalid")
        if defect.get("status") not in {"open", "resolved", "waived"}:
            raise ContractValidationError(f"defect_queue[{position}].status is invalid")
        claim_id = defect.get("claim_id")
        if claim_id is not None and claim_id not in claims:
            raise ContractValidationError(f"defect_queue[{position}] references unknown claim {claim_id!r}")


def _validate_verification(report: Mapping[str, Any]) -> None:
    if report.get("overall_status") not in {"pass", "fail", "needs_review"}:
        raise ContractValidationError("verification_report.overall_status is invalid")
    _require_list(report.get("checks"), "verification_report.checks")


def _validate_audit(revisions: Sequence[Any], claims: Mapping[str, Mapping[str, Any]]) -> None:
    for position, raw_revision in enumerate(revisions):
        revision = _require_mapping(raw_revision, f"revision_history[{position}]")
        _require_string(revision.get("revision_id"), f"revision_history[{position}].revision_id")
        changes = _require_list(revision.get("material_changes"), f"revision_history[{position}].material_changes")
        for change in changes:
            change_record = _require_mapping(change, f"revision_history[{position}].material_changes")
            claim_id = _require_string(change_record.get("claim_id"), "material_change.claim_id")
            if claim_id not in claims:
                raise ContractValidationError(f"revision_history[{position}] references unknown claim {claim_id!r}")


def _validate_approval(approval: Mapping[str, Any], resume: Mapping[str, Any]) -> None:
    if approval.get("status") not in {"pending", "approved", "rejected"}:
        raise ContractValidationError("approval_record.status is invalid")
    if approval.get("final_version") != resume.get("version_id"):
        raise ContractValidationError("approval_record.final_version must match tailored_resume.version_id")
