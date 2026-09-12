# Protocol: local one-page LaTeX rendering

Copy `templates/resume.tex` to an ignored private directory. Populate it only
from a draft which has passed `tools/resume_draft.py`; retain the draft JSON as
the evidence map. Do not introduce a new claim while rendering.

```bash
mkdir -p private-cv/run
cp templates/resume.tex private-cv/run/resume.tex
cd private-cv/run && pdflatex -interaction=nonstopmode resume.tex
python3 ../../tools/resume_verify.py --draft draft.json \
  --matching evidence-matching.json --pdf resume.pdf
```

The verifier must report one page and extract every claimed bullet. If content
does not fit, remove or condense low-priority evidence before reducing readability.

Use the fitting report after every render:

```bash
python3 tools/resume_fit.py --pdf private-cv/run/resume.pdf
```
