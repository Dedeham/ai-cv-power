from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from tools.resume_verify import verify
R=Path(__file__).resolve().parents[1]/"tests"/"fixtures"
def load(*p): return json.loads(R.joinpath(*p).read_text())
class VerifyTests(unittest.TestCase):
 def setUp(self): self.d=load("resume-draft","synthetic-draft.json");self.m=load("evidence-matching","expected-matching.json")
 def test_clean_draft_passes(self): self.assertEqual(verify(self.d,self.m)["overall_status"],"pass")
 def test_style_flags_are_nonblocking(self):
  d=copy.deepcopy(self.d);d["claims"][1]["text"]="Passionate  team player -- successfully worked on it!"
  r=verify(d,self.m);self.assertEqual(r["overall_status"],"pass");self.assertTrue(r["findings"])
 def test_bad_reference_is_hard_gate(self):
  d=copy.deepcopy(self.d);d["claims"][0]["requirement_refs"]=["req-002"]
  r=verify(d,self.m);self.assertEqual(r["overall_status"],"fail");self.assertEqual(r["findings"][0]["severity"],"critical")
 def test_unsupported_metric_is_hard_gate(self):
  d=copy.deepcopy(self.d);d["claims"][0]["text"]="Built pipelines that improved reporting by 25%."
  self.assertEqual(verify(d,self.m)["overall_status"],"fail")
