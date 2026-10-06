#!/usr/bin/env python3
from pathlib import Path
import ast
from xml.etree import ElementTree as ET
root=Path(__file__).resolve().parents[1]
errors=[]
for p in root.rglob("*.py"):
    try: ast.parse(p.read_text())
    except Exception as e: errors.append(f"PY {p}: {e}")
for p in root.rglob("*.xml"):
    try: ET.parse(str(p))
    except Exception as e: errors.append(f"XML {p}: {e}")
booking=(root/"views/booking_views.xml").read_text()
stay=(root/"views/stay_booking_views.xml").read_text()
manifest=(root/"__manifest__.py").read_text()
if '<field name="company_id" invisible="1"/>' not in booking:
    errors.append("booking form must contain invisible company_id for dynamic domains")
if '<field name="company_id" invisible="1"/>' not in stay:
    errors.append("stay form must contain company_id anchor")
if manifest.index('"views/stay_booking_views.xml"') > manifest.index('"views/booking_branch_views.xml"'):
    errors.append("booking_branch_views.xml must load after stay_booking_views.xml")
print("REVIEW GATE:", "PASS" if not errors else "FAIL")
for e in errors: print(" -",e)
raise SystemExit(bool(errors))
