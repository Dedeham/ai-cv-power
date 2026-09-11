#!/usr/bin/env python3
"""Prepare and validate local, reviewed job-description requirement artifacts.

This module deliberately does not call a model, network service, shell, or
external parser. A local agent follows ``protocols/job-intake.md`` to perform
semantic extraction, then this tool validates the resulting artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from contracts.v1.validate import ContractValidationError, validate_protocol_run


REVIEW_SCHEMA_VERSION = "job-intake-review/v1"
REQUIREMENT_CATEGORIES = {"must_have", "preferred", "responsibility"}
MATCHING_QUESTION = "Does the reviewed candidate evidence ledger support this requirement?"


class JobIntakeValidationError(ValueError):
    """Raised when a job-intake review is incomplete or unsafe to advance."""


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise JobIntakeValidationError(f"{path} must be an object")
    return value


def _require_list(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise JobIntakeValidationError(f"{path} must be an array")
    return value


def _require_non_empty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise JobIntakeValidationError(f"{path} must be a non-empty string")
    return value


def source_sha256(text: str) -> str:
    """Return the stable content fingerprint used to bind a review to a source."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _line_count(text: str) -> int:
    return len(text.splitlines())


def create_review_template(source_text: str, source_label: str) -> dict[str, Any]:
    """Create an empty, deterministic review template for an untrusted source."""
    if not source_text.strip():
        raise JobIntakeValidationError("job description input must not be blank")
    if not source_label.strip():
        raise JobIntakeValidationError("source label must not be blank")
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "source": {
            "label": source_label,
            "sha256": source_sha256(source_text),
            "line_count": _line_count(source_text),
        },
        "review_status": "needs_requirement_review",
        "requirement_matrix": [],
        "requirement_categories": [],
        "source_references": [],
        "domain_terms": [],
        "seniority_signals": [],
    }


def _contract_shell(requirements: Sequence[Any]) -> dict[str, Any]:
    """Build the smallest complete v1 run needed to validate matrix records."""
    return {
        "schema_version": "resume-tailoring/v1",
        "run_id": "job-intake-validation",
        "evidence_ledger": [],
        "requirement_matrix": list(requirements),
        "tailored_resume": {"version_id": "job-intake-draft", "claims": []},
        "defect_queue": [],
        "verification_report": {"overall_status": "needs_review", "checks": []},
        "revision_history": [],
        "approval_record": {"status": "pending", "final_version": "job-intake-draft"},
    }


def _validate_line_range(item: Mapping[str, Any], path: str, line_count: int) -> None:
    start_line, end_line = item.get("start_line"), item.get("end_line")
    if not isinstance(start_line, int) or isinstance(start_line, bool) or start_line < 1:
        raise JobIntakeValidationError(f"{path}.start_line must be a positive integer")
    if not isinstance(end_line, int) or isinstance(end_line, bool) or end_line < start_line:
        raise JobIntakeValidationError(f"{path}.end_line must be an integer at or after start_line")
    if end_line > line_count:
        raise JobIntakeValidationError(f"{path}.end_line exceeds source line count")


def _validate_categories(raw_categories: Sequence[Any], requirement_ids: set[str]) -> None:
    category_ids: set[str] = set()
    for position, raw_category in enumerate(raw_categories):
        category = _require_mapping(raw_category, f"requirement_categories[{position}]")
        requirement_id = _require_non_empty_string(
            category.get("requirement_id"),
            f"requirement_categories[{position}].requirement_id",
        )
        if requirement_id not in requirement_ids:
            raise JobIntakeValidationError(
                f"requirement_categories[{position}] references unknown requirement {requirement_id!r}"
            )
        if requirement_id in category_ids:
            raise JobIntakeValidationError(f"requirement {requirement_id!r} has more than one category")
        if category.get("category") not in REQUIREMENT_CATEGORIES:
            raise JobIntakeValidationError(f"requirement_categories[{position}].category is invalid")
        category_ids.add(requirement_id)
    if category_ids != requirement_ids:
        raise JobIntakeValidationError("every requirement must have exactly one category")


def _validate_named_source_items(raw_items: Sequence[Any], path: str, line_count: int) -> None:
    for position, raw_item in enumerate(raw_items):
        item = _require_mapping(raw_item, f"{path}[{position}]")
        _require_non_empty_string(item.get("text"), f"{path}[{position}].text")
        _validate_line_range(item, f"{path}[{position}]", line_count)


def _validate_exact_terms(
    requirements: Sequence[Mapping[str, Any]],
    references_by_requirement: Mapping[str, list[Mapping[str, Any]]],
    source_lines: Sequence[str],
) -> None:
    """Ensure retained employer terminology is traceable to its cited lines."""
    for requirement in requirements:
        requirement_id = requirement["id"]
        exact_terms = _require_list(
            requirement.get("exact_terms", []),
            f"requirement_matrix[{requirement_id}].exact_terms",
        )
        cited_source = "\n".join(
            line
            for reference in references_by_requirement[requirement_id]
            for line in source_lines[reference["start_line"] - 1 : reference["end_line"]]
        ).casefold()
        for position, term in enumerate(exact_terms):
            normalized_term = _require_non_empty_string(
                term,
                f"requirement_matrix[{requirement_id}].exact_terms[{position}]",
            )
            if normalized_term.casefold() not in cited_source:
                raise JobIntakeValidationError(
                    f"requirement_matrix[{requirement_id}].exact_terms[{position}] "
                    "is not present in its cited source lines"
                )


def validate_review(review: Mapping[str, Any], source_text: str) -> None:
    """Validate a completed review against source text and portable v1 rules."""
    document = _require_mapping(review, "job_intake_review")
    allowed_keys = {
        "schema_version",
        "source",
        "review_status",
        "requirement_matrix",
        "requirement_categories",
        "source_references",
        "domain_terms",
        "seniority_signals",
    }
    unknown_keys = set(document) - allowed_keys
    if unknown_keys:
        raise JobIntakeValidationError(f"job_intake_review has unsupported fields: {sorted(unknown_keys)!r}")
    if document.get("schema_version") != REVIEW_SCHEMA_VERSION:
        raise JobIntakeValidationError(f"schema_version must be {REVIEW_SCHEMA_VERSION}")
    if document.get("review_status") != "reviewed":
        raise JobIntakeValidationError("review_status must be reviewed before advancing")
    source = _require_mapping(document.get("source"), "source")
    _require_non_empty_string(source.get("label"), "source.label")
    if source.get("sha256") != source_sha256(source_text):
        raise JobIntakeValidationError("source.sha256 does not match the supplied job description")
    line_count = _line_count(source_text)
    if source.get("line_count") != line_count:
        raise JobIntakeValidationError("source.line_count does not match the supplied job description")
    requirements = _require_list(document.get("requirement_matrix"), "requirement_matrix")
    if not requirements:
        raise JobIntakeValidationError("requirement_matrix must contain at least one reviewed requirement")
    try:
        validate_protocol_run(_contract_shell(requirements))
    except ContractValidationError as error:
        raise JobIntakeValidationError(f"v1 requirement_matrix validation failed: {error}") from error
    for position, requirement in enumerate(requirements):
        is_pre_matching = (
            requirement.get("evidence_state") == "needs_confirmation"
            and requirement.get("coverage_state") == "not_applicable"
            and requirement.get("permitted_action") == "ask_question"
            and requirement.get("question") == MATCHING_QUESTION
        )
        if not is_pre_matching:
            raise JobIntakeValidationError(f"requirement_matrix[{position}] must remain in the pre-matching state")
    typed_requirements = [_require_mapping(record, "requirement_matrix item") for record in requirements]
    requirement_ids = {record["id"] for record in typed_requirements}
    _validate_categories(_require_list(document.get("requirement_categories"), "requirement_categories"), requirement_ids)
    references = _require_list(document.get("source_references"), "source_references")
    referenced_ids: set[str] = set()
    references_by_requirement: dict[str, list[Mapping[str, Any]]] = {
        requirement_id: [] for requirement_id in requirement_ids
    }
    for position, raw_reference in enumerate(references):
        reference = _require_mapping(raw_reference, f"source_references[{position}]")
        requirement_id = _require_non_empty_string(reference.get("requirement_id"), f"source_references[{position}].requirement_id")
        _validate_line_range(reference, f"source_references[{position}]", line_count)
        if requirement_id not in requirement_ids:
            raise JobIntakeValidationError(f"source_references[{position}] references unknown requirement {requirement_id!r}")
        referenced_ids.add(requirement_id)
        references_by_requirement[requirement_id].append(reference)
    if referenced_ids != requirement_ids:
        raise JobIntakeValidationError("every requirement must have at least one source reference")
    _validate_exact_terms(typed_requirements, references_by_requirement, source_text.splitlines())
    _validate_named_source_items(_require_list(document.get("domain_terms"), "domain_terms"), "domain_terms", line_count)
    _validate_named_source_items(_require_list(document.get("seniority_signals"), "seniority_signals"), "seniority_signals", line_count)


def _read_input(args: argparse.Namespace) -> tuple[str, str]:
    if args.input is not None:
        input_path = Path(args.input)
        try:
            return input_path.read_text(encoding="utf-8"), args.source_label or input_path.name
        except FileNotFoundError as error:
            raise JobIntakeValidationError(f"job description file was not found: {input_path}") from error
        except UnicodeDecodeError as error:
            raise JobIntakeValidationError(f"job description file is not UTF-8 text: {input_path}") from error
    return args.text, args.source_label or "pasted-job-description"


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare", help="create an empty local review template")
    source_group = prepare.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--input", help="private UTF-8 job-description text file")
    source_group.add_argument("--text", help="pasted job-description text")
    prepare.add_argument("--source-label", help="private source label stored in the local review")
    prepare.add_argument("--output", required=True, help="local JSON review artifact path")
    validate = subparsers.add_parser("validate", help="validate a completed local review")
    validate.add_argument("--input", required=True, help="same private UTF-8 job-description text file")
    validate.add_argument("--review", required=True, help="completed local JSON review artifact path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the local preparation or validation command."""
    args = build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            source_text, source_label = _read_input(args)
            _write_json(Path(args.output), create_review_template(source_text, source_label))
            print(f"Created private review template: {args.output}")
            return 0
        source_text = Path(args.input).read_text(encoding="utf-8")
        review = json.loads(Path(args.review).read_text(encoding="utf-8"))
        validate_review(review, source_text)
        print("Job-description intake review passed validation.")
        return 0
    except (JobIntakeValidationError, json.JSONDecodeError, OSError) as error:
        print(f"Job-description intake validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
