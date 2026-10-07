#!/usr/bin/env python3
from pathlib import Path
import ast
from xml.etree import ElementTree as ET

root=Path(__file__).resolve().parents[1]
errors=[]

for p in root.rglob("*.py"):
    try:
        ast.parse(p.read_text())
    except Exception as exc:
        errors.append("PY %s: %s" % (p.relative_to(root), exc))

for p in root.rglob("*.xml"):
    try:
        tree=ET.parse(str(p))
    except Exception as exc:
        errors.append("XML %s: %s" % (p.relative_to(root), exc))
        continue

    # Odoo search filters require stable names; group-by filters without name
    # caused the real Odoo 13 install failure seen during UAT.
    for flt in tree.findall(".//search//filter"):
        if not flt.attrib.get("name"):
            errors.append("SEARCH FILTER WITHOUT NAME in %s: %s" %
                          (p.relative_to(root), flt.attrib.get("string","<unnamed>")))

booking=(root/"views/booking_views.xml").read_text()
stay=(root/"views/stay_booking_views.xml").read_text()
manifest=(root/"__manifest__.py").read_text()

if '<field name="company_id" invisible="1"/>' not in booking:
    errors.append("booking form must contain invisible company_id for dynamic domains")
if '<field name="company_id" invisible="1"/>' not in stay:
    errors.append("stay form must contain company_id for dynamic/domain consistency")
if '<field name="branch_id"' not in booking:
    errors.append("booking form must visibly contain branch_id")
if '<field name="branch_id"' not in stay:
    errors.append("stay form must visibly contain branch_id because resource domain references it")
if manifest.index('"views/stay_booking_views.xml"') > manifest.index('"views/booking_branch_views.xml"'):
    errors.append("booking_branch_views.xml must load after stay_booking_views.xml")

print("DEEP REVIEW GATE:", "PASS" if not errors else "FAIL")
for err in errors:
    print(" -",err)
raise SystemExit(1 if errors else 0)
