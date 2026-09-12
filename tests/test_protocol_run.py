from __future__ import annotations
import json,unittest
from pathlib import Path
from tools.protocol_run import assess
R=Path(__file__).resolve().parents[1]/"tests"/"fixtures"
def load(*p): return json.loads(R.joinpath(*p).read_text())
class ProtocolRunTests(unittest.TestCase):
 def setUp(self): self.m=load("evidence-matching","expected-matching.json");self.d=load("resume-draft","synthetic-draft.json");self.q=load("resume-critic","synthetic-queue.json")
 def test_requires_draft(self): self.assertEqual(assess(self.m,None,None,None,0,False)["status"],"needs_agent_draft")
 def test_requires_critique(self): self.assertEqual(assess(self.m,self.d,None,None,0,False)["status"],"needs_independent_critique")
 def test_requires_evidence_before_approval(self): self.assertEqual(assess(self.m,self.d,self.q,None,0,True)["status"],"needs_candidate_evidence")
 def test_hard_defect_reaches_bound(self):
  q=dict(self.q);q["defects"]=self.q["defects"]+[{"id":"hard","severity":"high","rubric_dimension":"factual_integrity","claim_id":"claim-pipelines","finding":"x","recommendation":"Remove unsupported wording."}]
  self.assertEqual(assess(self.m,self.d,q,None,5,False)["status"],"max_cycles_reached")
