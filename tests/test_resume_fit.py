from pathlib import Path
import unittest
from unittest.mock import patch
from tools.resume_fit import assess_pdf
class FitTests(unittest.TestCase):
 def test_missing_pdf_is_invalid(self): self.assertEqual(assess_pdf(Path('/definitely-missing-resume.pdf'))['state'],'invalid')
 @patch('tools.resume_fit.shutil.which',return_value='/usr/bin/pdfinfo')
 @patch('tools.resume_fit.subprocess.run')
 def test_page_states_and_truthful_overflow_guidance(self,run,_which):
  pdf=Path(__file__)
  run.return_value.stdout='Pages:           1\\n'
  self.assertEqual(assess_pdf(pdf)['state'],'one_page')
  run.return_value.stdout='Pages:           2\\n'
  result=assess_pdf(pdf)
  self.assertEqual(result['state'],'overflow')
  self.assertIn('do not shrink type',result['recommendations'][-1])
