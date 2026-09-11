# Resume-tailoring contracts, v1

This folder defines portable JSON artifacts for the local, agent-first MVP. They are deliberately independent of a UI, database, LLM provider, or cloud service.

`protocol-run.schema.json` is the versioned wire contract. One protocol run contains:

- `evidence_ledger`: reviewed candidate source facts, including `verified`, `possible`, and `unknown` fact states;
- `requirement_matrix`: job requirements, priority, exact terms, evidence and coverage state, plus permitted action;
- `tailored_resume`: claims organized by section, with evidence and requirement references;
- `defect_queue`: review findings and their resolution state;
- `verification_report`: deterministic-check outcomes;
- `revision_history`: material claim changes for an audit trail; and
- `approval_record`: the candidate's decision for the exact resume version.

The schema defines record shape. `validate.py` enforces cross-record rules that JSON Schema cannot express portably: substantive claims require evidence; references must resolve; unknown evidence cannot support a claim; unsupported requirements cannot be represented; and approval must name the final resume version.

Run the local validation tests without installing dependencies:

```bash
python3 -m unittest discover -s tests -v
```

Fixtures are entirely synthetic. Do not place a real CV, job description, contact detail, employer name, or other private candidate material in this directory. Use opaque IDs and invented examples only.
