#!/usr/bin/env python3
"""Validate a concise independent-critic defect queue for a local draft."""
from __future__ import annotations
import argparse, json, sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from tools.resume_draft import ResumeDraftError, validate_draft

class CriticError(ValueError): pass
SEVERITIES={"critical","high","medium","low"}
DIMENSIONS={"factual_integrity","role_relevance","achievement_evidence","scannability","structure","language_tone","consistency"}

def _obj(v:Any,p:str)->Mapping[str,Any]:
 if not isinstance(v,Mapping): raise CriticError(f"{p} must be an object")
 return v
def _text(v:Any,p:str)->str:
 if not isinstance(v,str) or not v.strip(): raise CriticError(f"{p} must be a non-empty string")
 return v
def _arr(v:Any,p:str)->Sequence[Any]:
 if not isinstance(v,list): raise CriticError(f"{p} must be an array")
 return v

def validate_queue(queue:Mapping[str,Any],draft:Mapping[str,Any],matching:Mapping[str,Any])->None:
 try: validate_draft(draft,matching)
 except ResumeDraftError as e: raise CriticError(f"draft failed grounding gate: {e}") from e
 q=_obj(queue,"critic_queue")
 if q.get("schema_version")!="resume-critic/v1": raise CriticError("critic_queue.schema_version must be resume-critic/v1")
 if q.get("run_id")!=draft.get("run_id"): raise CriticError("critic_queue.run_id must match draft")
 claim_ids={c["id"] for c in draft["claims"]}; seen=set()
 for n,raw in enumerate(_arr(q.get("defects"),"critic_queue.defects")):
  d=_obj(raw,f"defects[{n}]"); did=_text(d.get("id"),f"defects[{n}].id")
  if did in seen: raise CriticError(f"duplicate defect id {did!r}")
  seen.add(did)
  if d.get("severity") not in SEVERITIES: raise CriticError(f"defect {did!r} has invalid severity")
  if d.get("rubric_dimension") not in DIMENSIONS: raise CriticError(f"defect {did!r} has invalid rubric_dimension")
  if d.get("claim_id") is not None and d["claim_id"] not in claim_ids: raise CriticError(f"defect {did!r} references unknown claim")
  _text(d.get("finding"),f"defect {did!r}.finding"); _text(d.get("recommendation"),f"defect {did!r}.recommendation")
  if "rewrite" in d["recommendation"].lower(): raise CriticError(f"defect {did!r} must diagnose, not freely rewrite")

def read(p:Path)->dict[str,Any]:
 try: return dict(_obj(json.loads(p.read_text(encoding="utf-8")),str(p)))
 except (OSError,json.JSONDecodeError) as e: raise CriticError(f"cannot read {p}: {e}") from e
def main(argv:Sequence[str]|None=None)->int:
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("--queue",type=Path,required=True);p.add_argument("--draft",type=Path,required=True);p.add_argument("--matching",type=Path,required=True);a=p.parse_args(argv)
 try: validate_queue(read(a.queue),read(a.draft),read(a.matching));print("Critic defect queue passed validation.");return 0
 except CriticError as e: print(f"resume-critic: {e}",file=sys.stderr);return 2
if __name__=="__main__": raise SystemExit(main())
