from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from tools.resume_critic import CriticError,validate_queue
R=Path(__file__).resolve().parents[1]/"tests"/"fixtures"
def load(*p): return json.loads(R.joinpath(*p).read_text())
class CriticTests(unittest.TestCase):
 def setUp(self): self.m=load("evidence-matching","expected-matching.json");self.d=load("resume-draft","synthetic-draft.json");self.q=load("resume-critic","synthetic-queue.json")
 def test_valid_queue(self): validate_queue(self.q,self.d,self.m)
 def test_rejects_unknown_claim(self):
  q=copy.deepcopy(self.q);q["defects"][0]["claim_id"]="invented"
  with self.assertRaisesRegex(CriticError,"unknown claim"): validate_queue(q,self.d,self.m)
 def test_rejects_free_rewrite(self):
  q=copy.deepcopy(self.q);q["defects"][0]["recommendation"]="Rewrite this bullet as a stronger claim."
  with self.assertRaisesRegex(CriticError,"not freely rewrite"): validate_queue(q,self.d,self.m)
