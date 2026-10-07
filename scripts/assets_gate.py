#!/usr/bin/env python3
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
errors=[]
allowed=(".qm_",".qs_",".qc_",".qe_",".qo_",".o_qimam_",".qp_",".qb_")
for p in (root/"static/src/scss").glob("*.scss"):
    t=p.read_text()
    if re.search(r"\b(?:min|max|clamp)\s*\([^)]*(?:vw|vh)[^)]*(?:px|rem|em)|\b(?:min|max|clamp)\s*\([^)]*(?:px|rem|em)[^)]*(?:vw|vh)",t):
        errors.append(f"{p.name}: mixed-unit Sass min/max/clamp")
    for m in re.finditer(r'(^|})\s*([^@{}][^{]+)\{',t):
        sel=m.group(2)
        for part in sel.split(","):
            x=part.strip()
            if x.startswith(".") and not x.startswith(allowed):
                errors.append(f"{p.name}: unscoped selector {x[:80]}")
    if "inset:" in t:
        errors.append(f"{p.name}: CSS inset shorthand avoided for Odoo13/theme compatibility")
print("ASSETS GATE:", "PASS" if not errors else "FAIL")
for e in errors: print(" -",e)
raise SystemExit(1 if errors else 0)
