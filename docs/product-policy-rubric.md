# Resume Quality Policy and Acceptance Rubric

**Status:** Draft policy for implementation

**Owner:** CV-6

**Applies to:** the tailored-resume workflow, from candidate input through export

## Purpose

This policy makes the product a constrained editor, not a source of new candidate facts. A tailored resume may reorder, select, condense, and rewrite candidate-provided evidence for a target role. It must not create or imply experience that the candidate cannot substantiate.

The workflow is:

`evidence ledger -> requirement matrix -> draft -> independent critique -> deterministic verification -> targeted revision -> human approval`

The policy distinguishes non-negotiable safety and document-integrity checks from quality preferences. A style preference must never be presented as a universal ATS rule.

## Terms and records

### Candidate evidence ledger

The evidence ledger is the reviewed source of truth derived from the master CV and candidate corrections. Each item has a stable identifier, source excerpt, and type (for example: role, responsibility, tool, result, date, qualification, or credential). Sensitive source text is handled under the future privacy policy; it must not be copied into logs or evaluation fixtures.

### Requirement matrix

For every material job-description requirement, retain its importance and one of these mutually exclusive states:

| State | Meaning | Permitted product response |
| --- | --- | --- |
| Supported and represented | Evidence supports the requirement and the draft communicates it | Keep or improve its presentation. |
| Supported but missing | Evidence supports the requirement but the draft does not communicate it | Add a traceable claim. |
| Needs confirmation | Available input suggests, but does not establish, support | Ask a narrow candidate question or retain `[NEEDS EVIDENCE]` internally. |
| Unsupported | No candidate evidence supports the requirement | Do not add the claim; optionally show it as a qualification gap. |

`[NEEDS EVIDENCE]` is a workflow marker and must not appear in an exported resume.

### Substantive claim

A substantive claim is an assertion about responsibility, ownership, scope, result, metric, technology, credential, title, date, promotion, or domain experience. Each substantive claim in a generated draft needs one or more ledger references. Purely editorial changes, such as shortening a sentence without changing meaning, do not require a new evidence item.

## Policy classes

| Class | Meaning | Effect |
| --- | --- | --- |
| Hard gate | A violation can make the resume misleading, unusable, or materially unsafe to submit | Blocks acceptance and export. |
| Strong default | Normally improves a professional resume, but has valid exceptions | Lowers quality score or produces actionable guidance. |
| House style | Product writing preference, not an ATS claim | Produces a non-blocking flag unless a configured rule promotes it. |
| Context dependent | Depends on market, language, career stage, profession, or employer instructions | Requires configuration or user choice; do not silently decide. |

## Hard acceptance gates

All gates must pass before the resume can be accepted as final or exported as validated.

| Gate | Pass condition | Observable verification |
| --- | --- | --- |
| Factual grounding | Every substantive generated claim links to supporting ledger evidence; wording does not strengthen individual ownership, scope, or outcome beyond that evidence | Claim-to-ledger coverage check; review samples containing team vs. individual work, metrics, dates, and tools. |
| No unresolved contradiction | Conflicting source facts (for example dates, title, degree, metric, or employment overlap) are resolved by the candidate or omitted from the final claim | Conflict detector plus a test fixture for each conflict class. |
| Critical parser safety | Essential contact details, section labels, roles, employers, and dates survive text extraction in a logical order | Export a fixture, extract text, and assert required fields and ordering. |
| No clipping or hidden essential content | The exported one-page document contains no text outside the printable page or hidden solely in headers, footers, text boxes, graphics, or images | PDF page count and text-bound checks; manual visual regression review. |
| High-severity language correctness | No unresolved spelling, grammar, or punctuation defect that changes meaning or makes the document unprofessional | Deterministic checks plus critic findings; use fixtures for dates, names, and sentence fragments. |
| One-page product constraint | The final resume is exactly one page and remains within configured readability limits | PDF page-count check and typography/margin threshold check. |
| Candidate approval | The candidate has reviewed and approved the final factual representation and positioning | Persisted explicit approval event tied to the final version. |

The one-page rule is a current product requirement. It does not justify unreadable type, silent clipping, or deleting relevant evidence without showing the candidate what changed.

## Quality rubric

The rubric is an engineering decision aid, not a universal ATS score or a scientific predictor of interviews. The critic evaluates it in a context separate from the writer; mechanical properties are verified independently where possible.

| Dimension | Weight | Acceptance floor | Observable question |
| --- | ---: | ---: | --- |
| Factual integrity | 20 | Pass hard gate | Are all substantive claims traceable and unexaggerated? |
| Target-role relevance | 20 | 14 | Are supported, important requirements prioritized over less relevant material? |
| Achievement evidence | 15 | 9 | Do bullets show action, scope/context, method, or result when evidence permits? |
| Clarity and scannability | 10 | 7 | Can a reader quickly identify role, employer, contribution, and outcome? |
| Parser robustness | 10 | Pass critical fields | Does selectable-text extraction preserve essential information? |
| Structure and prioritization | 10 | 7 | Are the strongest relevant facts prominent and chronology understandable? |
| Language and professional tone | 10 | 7 | Is wording direct, specific, concise, and not promotional or repetitive? |
| Consistency and completeness | 5 | 3 | Are dates, tense, capitalization, headings, and bullet punctuation consistent? |
| **Total** | **100** | **90** | Does the weighted score meet the release threshold? |

Scoring must include the dimension findings and evidence, rather than only a single number. A score cannot override a failed hard gate or a dimension below its floor.

## Writing and formatting policy

### Strong defaults

- Tailor to the actual job description using naturally relevant terminology only where candidate evidence supports it.
- Prefer accomplishment-oriented bullets: action plus context/scope and an outcome or method where supported. Ask for meaningful numbers; never invent them.
- Use specific action verbs where natural, active and direct language, concise bullets, reverse chronological experience, and a readable information hierarchy.
- Use present tense for ongoing work and past tense for completed work unless a documented context requires otherwise.
- Remove duty-only, duplicated, or irrelevant material before shrinking type.
- Use conventional headings, selectable text, a single-column logical order, clear dates, and complete job titles where practical.

### House-style checks

These are non-blocking review flags unless a later product decision changes their severity:

- Normalize double spaces to a single space, except where a formatting system deliberately requires whitespace.
- Do not use `--` as prose punctuation. Use restrained em dashes and prefer simpler punctuation when clearer.
- Flag unnecessary first-person pronouns in bullets, excessive slashes, decorative Unicode icons, exclamation marks, ellipses, inconsistent bullet terminal punctuation, and repeated phrases.
- Flag generic or unsupported self-description such as `aspiring`, `passionate`, `enthusiastic`, `dedicated`, `hard-working`, `results-driven`, `team player`, `responsible for`, `worked on`, `successfully`, or `excellent communication skills`. Replace only when a more specific, evidence-backed statement is available.
- Do not keyword-stuff or paste job-description sentences.

These flags are editorial guidance, not claims about a universal ATS ban list.

### Parser-safe defaults

Do not rely on columns, tables, text boxes, headers, footers, graphics, skill bars, icons, or image-only text for information necessary to understand the resume. The system must honor an employer's requested file format when that instruction is available. PDF validation requires selectable, extractable text.

## Revision and convergence policy

1. Build the evidence ledger and requirement matrix before drafting.
2. The writer changes only defects named in the current unified defect queue; it does not freely regenerate strong, approved content.
3. The critic receives the evidence ledger, requirement matrix, rubric, and draft, but not the writer's hidden reasoning.
4. Deterministic verifiers check factual references, style rules, date and punctuation consistency, duplicate content, text extraction, page count, and layout bounds.
5. A missing fact produces a targeted candidate question or an unresolved internal evidence marker, never an inferred claim.
6. Stop successfully only when all hard gates pass, the score is at least 90/100, every dimension meets its floor, no Critical or High defect remains, and either improvement is under two points across the last two complete rounds or no material textual change is justified.
7. Hard stop after five complete revision rounds. If criteria still fail, present unresolved defects and required candidate actions instead of endlessly rewriting.
8. Request candidate approval after the gates pass and before final acceptance. A candidate rejection returns only the identified concerns to the defect queue.

The five-round and two-point rules are operational defaults, not research claims; make them configurable in a later implementation task.

## Severity and defect queue

| Severity | Examples | Required handling |
| --- | --- | --- |
| Critical | Fabricated claim, wrong date, missing essential parsed contact detail, clipped essential content | Block; revise or ask candidate. |
| High | Unsupported ownership wording, unresolved contradiction, major grammar defect, one-page overflow | Block; revise or ask candidate. |
| Medium | Important supported requirement not represented, unclear accomplishment, weak structure | Revise when it improves score or relevance. |
| Low | Cliché, double space, unnecessary em dash, non-material repetition | Clean up automatically when meaning is preserved; otherwise flag. |

Every queue item needs a unique identifier, severity, rubric dimension, affected content, evidence reference when relevant, recommended action, and resolution status. Resolved defects remain in revision memory so they are not reintroduced.

## Candidate-question triggers

Ask rather than infer when the system needs to establish a material fact, including individual versus team ownership; magnitude or confidentiality of a metric; scope of people, customers, projects, or budget; official versus clarified job title; date conflict; credential; technology usage; or preferred career narrative. Questions must be specific enough to answer without asking the candidate to rewrite their CV.

## Open product decisions

The following are intentionally unresolved. Implementations must expose a configuration, defer, or seek direction rather than choosing a value silently.

| Decision | Why it matters |
| --- | --- |
| Initial markets, languages, and local resume conventions | Changes date formats, names, page conventions, photo expectations, and guidance. |
| Account, storage, retention, and deletion model | Determines consent, data lifecycle, and approval persistence. |
| Accepted inputs and exports | Determines parser, editor, and validation scope for pasted text, PDF, DOCX, and other sources. |
| Exact noaislob-style lexicon and whether users can override it | Defines which style flags are enabled and their severity. |
| Initial template count and customization boundaries | Determines layout implementation and visual testing surface. |
| Model provider, quality/cost/latency budgets, and critic independence | Determines implementation architecture and evaluation reliability. |
| Candidate-facing treatment of unsupported requirements | Determines whether gaps are hidden, surfaced, or converted to questions. |
| Readability thresholds for font size, margins, density, and sparse-page use | Needed to make the one-page gate objectively testable. |
| Score floors and whether 90/100 is configurable by market or career stage | The current numbers are engineering defaults, not a validated universal score. |

## Verification matrix for this policy

Future implementation tasks must maintain representative, sanitized fixtures that make every policy dimension observable. At minimum, the corpus must cover:

| Scenario | Expected result |
| --- | --- |
| A supported quantified achievement | Claim links to evidence and can be represented. |
| A job requirement absent from candidate evidence | Requirement is `Unsupported`; no generated claim appears. |
| Ambiguous team achievement | System asks about individual contribution or preserves team wording. |
| Conflicting employment dates | Finalization is blocked pending resolution or omission. |
| Job description with repeated keywords | Natural, evidence-backed coverage without stuffing. |
| Draft containing double spaces, `--`, cliché, and duplicate bullet | Deterministic style findings are produced with correct severity. |
| Export containing contact details in a header or a two-column table | Critical parser-safety gate fails. |
| Dense and sparse one-page layouts | No clipping; readability threshold passes; use of space is reviewed. |
| Five non-converging revisions | System stops and returns unresolved defects rather than continuing. |
| Candidate rejects a final claim | Defect is reopened and final acceptance is withheld. |

## Source and scope note

This policy operationalizes the project requirements and the supplied *Deep Research Report: Prompting AI to Improve CVs and Building an Iterative CV Optimization Agent*. It does not embed candidate CV content or private source documents. Research-backed recommendations are kept separate from explicit engineering defaults and unresolved product choices.
