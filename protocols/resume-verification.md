# Protocol: deterministic resume verification

After draft grounding and independent critique, run the deterministic gate. It
reports factual/parser/layout failures separately from non-blocking house-style
findings. A PDF supplied to the gate must be exactly one page with selectable,
extractable claim text; absent PDF tools are a hard failure, never a pass.

```bash
python3 tools/resume_verify.py --draft /private/draft.json \
  --matching /private/evidence-matching.json --pdf /private/resume.pdf \
  --output /private/verification.json
```

Do not validate/export a final resume while any Critical or High finding remains.
