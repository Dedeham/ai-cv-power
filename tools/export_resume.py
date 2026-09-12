#!/usr/bin/env python3
"""Compile a private LaTeX resume and run local one-page/export hard gates."""
from __future__ import annotations
import argparse,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from tools.resume_fit import assess_pdf
from tools.resume_verify import verify
from tools.protocol_run import read
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--tex',type=Path,required=True);p.add_argument('--draft',type=Path,required=True);p.add_argument('--matching',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args(argv)
 if not a.tex.is_file(): print('export-resume: source .tex file is missing',file=sys.stderr);return 2
 a.output_dir.mkdir(parents=True,exist_ok=True)
 done=subprocess.run(['pdflatex','-interaction=nonstopmode','-output-directory',str(a.output_dir),str(a.tex)],text=True,capture_output=True,check=False)
 pdf=a.output_dir/(a.tex.stem+'.pdf')
 if done.returncode or not pdf.is_file(): print('export-resume: LaTeX compilation failed',file=sys.stderr);return 2
 fit=assess_pdf(pdf); report=verify(read(a.draft),read(a.matching),pdf)
 print(f'PDF: {pdf}\nFit: {fit["state"]}\nVerification: {report["overall_status"]}')
 return 0 if fit['state']=='one_page' and report['overall_status']=='pass' else 2
if __name__=='__main__': raise SystemExit(main())
