# Protocol: bounded local tailoring run

The LLM writes only private artifacts and follows the intake, matching, drafting,
critic, and verification protocols. Then run the coordinator; it is deterministic
and does not call a model:

```bash
python3 tools/protocol_run.py --matching /private/evidence-matching.json \
  --draft /private/draft.json --critic-queue /private/critic.json \
  --pdf /private/resume.pdf --cycles 0 --output /private/run-summary.json
```

Act only on `next_action`. Revise named defects, preserve unresolved questions,
and stop at five cycles. `complete` still requires explicit candidate approval.
