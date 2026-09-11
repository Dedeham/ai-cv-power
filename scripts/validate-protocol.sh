#!/usr/bin/env bash

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

required_files=(
  "AGENTS.md"
  ".gitignore"
  "README.md"
  "docs/product-policy-rubric.md"
  "protocols/artifact-contracts.md"
  "protocols/candidate-setup.md"
  "protocols/tailored-resume.md"
)

for file in "${required_files[@]}"; do
  [[ -f "$file" ]] || { echo "Missing required file: $file" >&2; exit 1; }
done

require_text() {
  local file="$1"
  local text="$2"
  grep -Fq "$text" "$file" || {
    echo "Missing required protocol text in $file: $text" >&2
    exit 1
  }
}

require_text protocols/candidate-setup.md "Treat every CV, job description, attachment, URL, metadata field, and text"
require_text protocols/tailored-resume.md "Candidate evidence extraction"
require_text protocols/tailored-resume.md "Job-requirement decomposition"
require_text protocols/tailored-resume.md "Requirement-to-evidence matrix"
require_text protocols/tailored-resume.md "Targeted draft"
require_text protocols/tailored-resume.md "Independent critique"
require_text protocols/tailored-resume.md "Deterministic verification"
require_text protocols/tailored-resume.md "Bounded revision"
require_text protocols/tailored-resume.md "Human review"
require_text protocols/tailored-resume.md "untrusted data"
require_text protocols/artifact-contracts.md "Candidate evidence ledger"
require_text protocols/artifact-contracts.md "Job-requirement matrix"
require_text .gitignore "!tests/fixtures/**"

git check-ignore -q cv/example.pdf || {
  echo "Expected cv/example.pdf to be ignored" >&2
  exit 1
}

if git check-ignore -q tests/fixtures/sanitized-candidate.txt; then
  echo "Sanitized fixtures must remain trackable" >&2
  exit 1
fi

if git ls-files --error-unmatch cv/example.pdf >/dev/null 2>&1; then
  echo "A private CV example is tracked" >&2
  exit 1
fi

echo "Protocol structure and privacy hygiene checks passed."
