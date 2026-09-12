#!/usr/bin/env python3
"""Coordinate a bounded local resume-tailoring protocol run from JSON artifacts."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from tools.evidence_matching import validate_matching_result,EvidenceMatchingError
from tools.resume_draft import validate_draft,ResumeDraftError
from tools.resume_critic import validate_queue,CriticError
from tools.resume_verify import verify
MAX_CYCLES=5
class RunError(ValueError): pass
def read(p:Path)->dict[str,Any]:
 try:
  x=json.loads(p.read_text(encoding="utf-8"))
  if not isinstance(x,dict): raise RunError("artifact must be an object")
  return x
 except (OSError,json.JSONDecodeError) as e: raise RunError(f"cannot read {p}: {e}") from e
def assess(matching:dict[str,Any],draft:dict[str,Any]|None,queue:dict[str,Any]|None,pdf:Path|None,cycles:int,approved:bool)->dict[str,Any]:
 if cycles<0 or cycles>MAX_CYCLES: raise RunError(f"cycles must be between 0 and {MAX_CYCLES}")
 try: validate_matching_result(matching)
 except EvidenceMatchingError as e: return {"status":"blocked","next_action":"repair_matching","reason":str(e)}
 gaps=matching.get("coverage_report",{}).get("needs_confirmation",[])
 if draft is None: return {"status":"needs_agent_draft","next_action":"create_grounded_draft","questions":gaps}
 try: validate_draft(draft,matching)
 except ResumeDraftError as e: return {"status":"blocked","next_action":"repair_draft_grounding","reason":str(e),"questions":gaps}
 if queue is None: return {"status":"needs_independent_critique","next_action":"create_critic_queue","questions":gaps}
 try: validate_queue(queue,draft,matching)
 except CriticError as e: return {"status":"blocked","next_action":"repair_critic_queue","reason":str(e),"questions":gaps}
 report=verify(draft,matching,pdf)
 blockers=[x for x in queue.get("defects",[]) if x.get("severity") in {"critical","high"}]
 blockers += [x for x in report["findings"] if x["severity"] in {"critical","high"}]
 if blockers:
  return {"status":"max_cycles_reached" if cycles>=MAX_CYCLES else "needs_targeted_revision","next_action":"revise_named_defects","cycles":cycles,"defects":blockers,"questions":gaps}
 if gaps: return {"status":"needs_candidate_evidence","next_action":"answer_targeted_questions","questions":gaps}
 if not approved: return {"status":"needs_candidate_approval","next_action":"review_final_factual_representation","verification":report}
 return {"status":"complete","next_action":"export_approved_resume","verification":report}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--matching",type=Path,required=True);p.add_argument("--draft",type=Path);p.add_argument("--critic-queue",type=Path);p.add_argument("--pdf",type=Path);p.add_argument("--cycles",type=int,default=0);p.add_argument("--approved",action="store_true");p.add_argument("--output",type=Path);a=p.parse_args(argv)
 try: r=assess(read(a.matching),read(a.draft) if a.draft else None,read(a.critic_queue) if a.critic_queue else None,a.pdf,a.cycles,a.approved)
 except RunError as e: print(f"protocol-run: {e}",file=sys.stderr);return 2
 data=json.dumps(r,indent=2)+"\n"; (a.output.write_text(data) if a.output else print(data,end="")); return 0
if __name__=="__main__": raise SystemExit(main())
