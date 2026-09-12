#!/usr/bin/env python3
"""Report truthful one-page fitting guidance for a locally rendered PDF."""
from __future__ import annotations
import argparse,re,shutil,subprocess,sys
from pathlib import Path
def assess_pdf(pdf:Path)->dict:
 if not pdf.is_file(): return {"state":"invalid","pages":None,"recommendations":["Render a PDF before checking fit."]}
 if not shutil.which("pdfinfo"): return {"state":"invalid","pages":None,"recommendations":["Install pdfinfo to measure page count."]}
 output=subprocess.run(["pdfinfo",str(pdf)],text=True,capture_output=True,check=False).stdout
 match=re.search(r"^Pages:\s+(\d+)",output,re.M)
 if not match: return {"state":"invalid","pages":None,"recommendations":["PDF page count could not be read."]}
 pages=int(match.group(1))
 if pages>1: return {"state":"overflow","pages":pages,"recommendations":["Remove irrelevant or duplicate supported content first.","Condense supported bullets without changing facts.","Ask the candidate which lower-priority evidence to omit; do not shrink type or invent filler."]}
 return {"state":"one_page","pages":1,"recommendations":["Review visible density manually; a sparse page is guidance, not permission to add unsupported claims."]}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--pdf",type=Path,required=True);a=p.parse_args(argv);r=assess_pdf(a.pdf);print(r);return 0 if r["state"]=="one_page" else 2
if __name__=="__main__":raise SystemExit(main())
