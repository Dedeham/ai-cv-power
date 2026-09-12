#!/usr/bin/env python3
"""Deterministic local quality gates for a grounded resume draft and PDF export."""
from __future__ import annotations
import argparse,json,re,shutil,subprocess,sys
from collections.abc import Mapping,Sequence
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from tools.resume_draft import ResumeDraftError,validate_draft
STYLE=(r" {2,}",r"--",r"\b(?:aspiring|passionate|enthusiastic|dedicated|hard-working|results-driven|team player|responsible for|worked on|successfully)\b",r"!",r"\.\.\.")
def finding(i,sev,kind,where,action): return {"id":i,"severity":sev,"kind":kind,"location":where,"action":action}
def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def verify(draft:Mapping[str,Any],matching:Mapping[str,Any],pdf:Path|None=None)->dict:
 out=[]
 try: validate_draft(draft,matching)
 except ResumeDraftError as e: out.append(finding("grounding","critical","factual","draft",str(e)))
 claims=draft.get("claims",[]); texts=[]
 for c in claims:
  t=c.get("text",""); texts.append(t)
  for rule in STYLE:
   if re.search(rule,t,re.I): out.append(finding(f"style-{c.get('id')}-{len(out)}","low","style",c.get("id","claim"),"Remove house-style pattern while preserving meaning."))
  if re.search(r"\b\d+(?:\.\d+)?%",t) and not any("%" in e.get("source_excerpt","") for e in matching.get("evidence_ledger",[]) if e.get("id") in c.get("evidence_refs",[])):
   out.append(finding(f"metric-{c.get('id')}","critical","factual",c.get("id","claim"),"Remove or link the numerical claim to supporting evidence."))
 for n,t in enumerate(texts):
  if t and texts.count(t)>1: out.append(finding(f"duplicate-{n}","medium","consistency",f"claims[{n}]","Remove duplicate bullet text."))
 if pdf:
  if not shutil.which("pdfinfo") or not shutil.which("pdftotext"):
   out.append(finding("pdf-tools","critical","parser","export","Install pdfinfo and pdftotext to validate the export."))
  else:
   info=subprocess.run(["pdfinfo",str(pdf)],text=True,capture_output=True,check=False).stdout
   pages=re.search(r"^Pages:\s+(\d+)",info,re.M)
   if not pages or pages.group(1)!="1": out.append(finding("page-count","high","layout","export","Export exactly one page."))
   text=subprocess.run(["pdftotext",str(pdf),"-"],text=True,capture_output=True,check=False).stdout
   for c in claims:
    if c.get("text") and c["text"] not in text: out.append(finding(f"extract-{c.get('id')}","critical","parser",c.get("id","claim"),"Use selectable, extractable text for this content."))
 return {"schema_version":"resume-verification/v1","overall_status":"pass" if not any(x["severity"] in {"critical","high"} for x in out) else "fail","findings":out}
def main(argv:Sequence[str]|None=None):
 p=argparse.ArgumentParser();p.add_argument("--draft",required=True);p.add_argument("--matching",required=True);p.add_argument("--pdf");p.add_argument("--output");a=p.parse_args(argv)
 report=verify(read(a.draft),read(a.matching),Path(a.pdf) if a.pdf else None);data=json.dumps(report,indent=2)+"\n"
 if a.output: Path(a.output).write_text(data)
 else: print(data,end="")
 return 0 if report["overall_status"]=="pass" else 2
if __name__=="__main__": raise SystemExit(main())
