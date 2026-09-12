from pathlib import Path
import unittest
from tools.export_resume import main
class ExportTests(unittest.TestCase):
 def test_missing_source_fails_without_creating_resume(self):
  self.assertEqual(main(['--tex','/missing.tex','--draft','/missing.json','--matching','/missing.json','--output-dir','/tmp/cv-export-test']),2)
