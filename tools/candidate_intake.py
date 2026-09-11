#!/usr/bin/env python3
"""Create and validate private, candidate-reviewed evidence intake packets.

The helper is deliberately deterministic. It never calls a model, network, or
shell command based on source content. It treats source material as data and
leaves semantic atomicization and candidate confirmation to the protocol.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


SUPPORTED_SUFFIXES = {".txt", ".md", ".markdown", ".tex"}
MAX_SOURCE_BYTES = 1_000_000
TERMINAL_REVIEW_STATUSES = {"accepted", "rejected", "corrected"}


class CandidateIntakeError(ValueError):
    """Raised when a candidate intake packet violates the local intake protocol."""


def repository_root() -> Path:
    """Return this repository's root without trusting the current directory."""

    return Path(__file__).resolve().parents[1]


def _stable_evidence_id(position: int) -> str:
    return f"e-{position:03d}"


def _is_heading(line: str) -> bool:
    normalized = line.strip()
    return (
        normalized.startswith(("#", "\\section", "\\subsection", "\\begin", "\\end", "%"))
        or (len(normalized) < 80 and normalized.isupper() and any(character.isalpha() for character in normalized))
    )


def _kind_for_line(line: str) -> str:
    normalized = line.lower()
    if any(token in normalized for token in ("certif", "license", "credential")):
        return "credential"
    if any(token in normalized for token in ("bsc", "msc", "ba ", "ma ", "degree", "education")):
        return "qualification"
    if any(token in normalized for token in ("python", "sql", "javascript", "excel", "tableau", "aws", "git")):
        return "tool"
    if any(character.isdigit() for character in normalized) and any(
        marker in normalized for marker in ("%", "increased", "reduced", "saved", "improved", "grew")
    ):
        return "result"
    if any(marker in normalized for marker in ("20", "19")) and any(
        marker in normalized for marker in ("--", "-", "–", "—")
    ):
        return "date"
    if normalized.startswith(("-", "*", "\\item")):
        return "responsibility"
    return "other"


def _clean_source_unit(line: str) -> str:
    """Keep a compact source excerpt while retaining the candidate's wording."""

    return " ".join(line.strip().removeprefix("\\item").strip().split())


def _allowed_wording(excerpt: str) -> str:
    return f"Use only the supported meaning in: {excerpt}"


def build_review_packet(source_text: str, run_id: str) -> dict[str, Any]:
    """Build a pending packet with v1-compatible evidence records and spans."""

    if not source_text.strip():
        raise CandidateIntakeError("source text must contain at least one non-whitespace character")
    _validate_identifier(run_id, "run_id")

    evidence_ledger: list[dict[str, str]] = []
    review_items: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(source_text.splitlines(), start=1):
        excerpt = _clean_source_unit(raw_line)
        if not excerpt or _is_heading(raw_line):
            continue

        evidence_id = _stable_evidence_id(len(evidence_ledger) + 1)
        evidence_ledger.append(
            {
                "id": evidence_id,
                "kind": _kind_for_line(excerpt),
                "fact_state": "possible",
                "source_excerpt": excerpt,
                "confirmation_question": "Does this source excerpt support this fact exactly as written?",
            }
        )
        review_items.append(
            {
                "evidence_id": evidence_id,
                "source_span": {"line_start": line_number, "line_end": line_number},
                "status": "needs_candidate_review",
                "allowed_wording": _allowed_wording(excerpt),
            }
        )

    if not evidence_ledger:
        raise CandidateIntakeError("source text contains no reviewable candidate fact lines")

    return {
        "schema_version": "candidate-intake/v1",
        "run_id": run_id,
        "review_status": "pending",
        "evidence_ledger": evidence_ledger,
        "review_items": review_items,
        "protocol_note": (
            "Pending candidates are untrusted source-derived data. Candidate review is required "
            "before any accepted verified evidence may be transferred to a protocol run."
        ),
    }


def validate_review_packet(packet: Mapping[str, Any], *, require_reviewed: bool = False) -> None:
    """Validate packet shape and enforce the candidate-review gate when requested."""

    if packet.get("schema_version") != "candidate-intake/v1":
        raise CandidateIntakeError("schema_version must be candidate-intake/v1")
    _validate_identifier(packet.get("run_id"), "run_id")
    review_status = packet.get("review_status")
    if review_status not in {"pending", "reviewed"}:
        raise CandidateIntakeError("review_status must be pending or reviewed")
    ledger = _require_list(packet.get("evidence_ledger"), "evidence_ledger")
    review_items = _require_list(packet.get("review_items"), "review_items")
    if not ledger:
        raise CandidateIntakeError("evidence_ledger must not be empty")

    ledger_by_id: dict[str, Mapping[str, Any]] = {}
    for index, raw_evidence in enumerate(ledger):
        evidence = _require_mapping(raw_evidence, f"evidence_ledger[{index}]")
        evidence_id = evidence.get("id")
        _validate_identifier(evidence_id, f"evidence_ledger[{index}].id")
        if evidence_id in ledger_by_id:
            raise CandidateIntakeError(f"evidence_ledger contains duplicate id {evidence_id!r}")
        if evidence.get("kind") not in {
            "role", "responsibility", "tool", "result", "date", "qualification", "credential", "other"
        }:
            raise CandidateIntakeError(f"evidence_ledger[{evidence_id}].kind is invalid")
        if evidence.get("fact_state") not in {"verified", "possible", "unknown"}:
            raise CandidateIntakeError(f"evidence_ledger[{evidence_id}].fact_state is invalid")
        _require_nonempty_string(evidence.get("source_excerpt"), f"evidence_ledger[{evidence_id}].source_excerpt")
        if evidence.get("fact_state") == "possible":
            _require_nonempty_string(
                evidence.get("confirmation_question"),
                f"evidence_ledger[{evidence_id}].confirmation_question",
            )
        ledger_by_id[evidence_id] = evidence

    review_by_evidence: dict[str, Mapping[str, Any]] = {}
    for index, raw_item in enumerate(review_items):
        item = _require_mapping(raw_item, f"review_items[{index}]")
        evidence_id = item.get("evidence_id")
        if evidence_id not in ledger_by_id:
            raise CandidateIntakeError(f"review_items[{index}] references unknown evidence {evidence_id!r}")
        if evidence_id in review_by_evidence:
            raise CandidateIntakeError(f"review_items contains duplicate evidence reference {evidence_id!r}")
        status = item.get("status")
        if status not in TERMINAL_REVIEW_STATUSES | {"needs_candidate_review"}:
            raise CandidateIntakeError(f"review_items[{index}].status is invalid")
        span = _require_mapping(item.get("source_span"), f"review_items[{index}].source_span")
        line_start = span.get("line_start")
        line_end = span.get("line_end")
        if not isinstance(line_start, int) or line_start < 1 or not isinstance(line_end, int) or line_end < line_start:
            raise CandidateIntakeError(f"review_items[{index}].source_span must contain valid positive line bounds")
        _require_nonempty_string(item.get("allowed_wording"), f"review_items[{index}].allowed_wording")
        review_by_evidence[evidence_id] = item

    missing_review = set(ledger_by_id) - set(review_by_evidence)
    if missing_review:
        raise CandidateIntakeError(f"evidence_ledger lacks review items for {sorted(missing_review)!r}")

    if require_reviewed:
        if review_status != "reviewed":
            raise CandidateIntakeError("review_status must be reviewed before downstream tailoring")
        for evidence_id, evidence in ledger_by_id.items():
            status = review_by_evidence[evidence_id]["status"]
            if status not in TERMINAL_REVIEW_STATUSES:
                raise CandidateIntakeError(f"evidence {evidence_id!r} remains needs_candidate_review")
            if evidence["fact_state"] == "unknown":
                raise CandidateIntakeError(f"unknown evidence {evidence_id!r} cannot pass the reviewed intake gate")
            if status in {"accepted", "corrected"} and evidence["fact_state"] != "verified":
                raise CandidateIntakeError(f"accepted evidence {evidence_id!r} must be verified")


def _require_mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CandidateIntakeError(f"{path} must be an object")
    return value


def _require_list(value: Any, path: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise CandidateIntakeError(f"{path} must be an array")
    return value


def _require_nonempty_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CandidateIntakeError(f"{path} must be a non-empty string")
    return value


def _validate_identifier(value: Any, path: str) -> None:
    identifier = _require_nonempty_string(value, path)
    if len(identifier) < 3 or len(identifier) > 64 or not identifier[0].islower():
        raise CandidateIntakeError(f"{path} must use the local lowercase identifier convention")
    if any(character not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for character in identifier):
        raise CandidateIntakeError(f"{path} must use only lowercase letters, digits, underscores, and hyphens")


def _is_ignored_by_git(path: Path, repo_root: Path) -> bool:
    try:
        relative_path = path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return True
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", str(relative_path)],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _require_private_path(path: Path, *, label: str) -> None:
    if not _is_ignored_by_git(path, repository_root()):
        raise CandidateIntakeError(
            f"{label} must be outside this repository or in an ignored local folder; "
            "do not use a tracked repository path for private candidate material"
        )


def _read_source(path: Path) -> str:
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise CandidateIntakeError(
            "initial intake supports only plain-text, Markdown, and LaTeX-like source; "
            "PDF, DOCX, OCR, and image parsing are not supported"
        )
    if not path.is_file():
        raise CandidateIntakeError("input source must be an existing file")
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise CandidateIntakeError("input source exceeds the 1 MB local intake limit")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise CandidateIntakeError("input source must be UTF-8 text") from error


def _write_json(path: Path, document: Mapping[str, Any]) -> None:
    _require_private_path(path, label="output path")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    _require_private_path(path, label="input path")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise CandidateIntakeError("input packet must be an existing file") from error
    except json.JSONDecodeError as error:
        raise CandidateIntakeError("input packet must be valid JSON") from error
    if not isinstance(document, dict):
        raise CandidateIntakeError("input packet must be a JSON object")
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare or validate a private candidate intake packet.")
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare", help="prepare a pending review packet")
    source_group = prepare.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--input", type=Path, help="private UTF-8 source file in an ignored folder")
    source_group.add_argument("--stdin", action="store_true", help="read deliberately pasted source text from standard input")
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument("--output", required=True, type=Path, help="private packet output path")

    validate = commands.add_parser("validate", help="validate an existing private review packet")
    validate.add_argument("--input", required=True, type=Path, help="private intake packet")
    validate.add_argument("--require-reviewed", action="store_true", help="enforce the candidate-review gate")
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(arguments)
    try:
        if args.command == "prepare":
            if args.stdin:
                source_text = sys.stdin.read(MAX_SOURCE_BYTES + 1)
                if len(source_text.encode("utf-8")) > MAX_SOURCE_BYTES:
                    raise CandidateIntakeError("pasted source exceeds the 1 MB local intake limit")
            else:
                _require_private_path(args.input, label="input source")
                source_text = _read_source(args.input)
            packet = build_review_packet(source_text, args.run_id)
            _write_json(args.output, packet)
            print(f"Created pending private candidate review packet at {args.output}")
            return 0

        packet = _load_json(args.input)
        validate_review_packet(packet, require_reviewed=args.require_reviewed)
        print("Candidate intake packet passed validation")
        return 0
    except CandidateIntakeError as error:
        print(f"candidate-intake: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
