# Protocol: independent resume critic

Review the draft independently. Receive only the reviewed matching artifact, the
draft artifact, and the fixed rubric; do not receive or reconstruct the writer's
hidden reasoning. Do not rewrite the resume or provide chain-of-thought.

Return a JSON `resume-critic/v1` queue with `run_id` and concise defects. Each
defect needs an ID, `critical`/`high`/`medium`/`low` severity, one rubric dimension
(`factual_integrity`, `role_relevance`, `achievement_evidence`, `scannability`,
`structure`, `language_tone`, or `consistency`), optional draft `claim_id`, a
specific finding, and a recommended action. Diagnose only; requests such as
"remove unsupported wording" are allowed, but a rewritten bullet is not.

Validate before revision:

```bash
python3 tools/resume_critic.py --queue /private/critic.json \
  --draft /private/draft.json --matching /private/evidence-matching.json
```
