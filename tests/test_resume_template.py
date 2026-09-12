from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class ResumeTemplateTests(unittest.TestCase):
 def test_template_is_single_column_and_parser_safe(self):
  text=(ROOT/'templates'/'resume.tex').read_text()
  self.assertNotIn('tabular',text);self.assertNotIn('multicol',text);self.assertNotIn('includegraphics',text)
  for heading in ('Summary','Experience','Skills','Education'): self.assertIn(heading,text)
 def test_private_resume_output_is_ignored(self):
  self.assertIn('/private-cv',(ROOT/'.gitignore').read_text())
