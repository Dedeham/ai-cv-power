# Local artifact contracts

All protocol artifacts are local, candidate-controlled records. Do not commit
them unless they are explicitly sanitized fixtures under `tests/fixtures/`.
Identifiers must be stable within one tailoring run.

## Candidate evidence ledger

Create after the candidate has reviewed extracted source material.

| Field | Required | Meaning |
| --- | --- | --- |
| `evidence_id` | Yes | Stable local identifier, such as `E-001`. |
| `type` | Yes | Role, responsibility, tool, result, date, qualification, or credential. |
| `source_excerpt` | Yes | Minimal source text supporting the item. |
| `candidate_status` | Yes | `reviewed`, `needs_confirmation`, or `rejected`. |
| `notes` | No | Clarification that does not replace the source. |

## Job-requirement matrix

Create before the draft. Include every material role requirement.

| Field | Required | Meaning |
| --- | --- | --- |
| `requirement_id` | Yes | Stable local identifier, such as `R-001`. |
| `requirement` | Yes | A concise, neutral decomposition of the job description. |
| `importance` | Yes | `critical`, `important`, or `supporting`. |
| `state` | Yes | `supported_and_represented`, `supported_but_missing`, `needs_confirmation`, or `unsupported`. |
| `evidence_ids` | Yes | Ledger IDs; empty only for `unsupported`. |
| `draft_claim_ids` | Yes | Draft claim IDs; empty until represented. |

## Targeted draft and claim map

Each substantive claim in the draft needs a local `claim_id` and one or more
`evidence_ids`. A substantive claim covers responsibility, ownership, scope,
result, metric, technology, credential, title, date, promotion, or domain
experience. Editorial shortening that preserves meaning is not a new claim.

## Defect queue and review record

The critic and deterministic verifier each add queue items with: unique ID,
severity (`critical`, `high`, `medium`, or `low`), rubric dimension, affected
content, evidence reference where relevant, recommended action, and resolution
status. Keep resolved items during the run so they cannot be silently
reintroduced. Record the candidate's explicit final approval against the final
draft version.
