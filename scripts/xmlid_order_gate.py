#!/usr/bin/env python3
from pathlib import Path
import ast,re
from xml.etree import ElementTree as ET
root=Path(__file__).resolve().parents[1]
manifest=ast.literal_eval((root/"__manifest__.py").read_text())
data=manifest.get("data",[])
defined={}
errors=[]
ref_attrs=("parent","action","groups","inherit_id")
for idx,rel in enumerate(data):
    p=root/rel
    if not p.exists(): continue
    if p.suffix!=".xml": continue
    try: tree=ET.parse(str(p))
    except Exception as e:
        errors.append(f"{rel}: XML parse: {e}"); continue
    # Check refs against ids defined strictly earlier or earlier in same file.
    for el in tree.getroot().iter():
        refs=[]
        for a in ref_attrs:
            v=el.attrib.get(a)
            if not v: continue
            refs += [x.strip() for x in v.split(",") if x.strip()]
        if el.tag=="field" and el.attrib.get("ref"): refs.append(el.attrib["ref"])
        for ref in refs:
            if ref.startswith("model_"):
                continue
            if "." in ref:
                mod,xid=ref.split(".",1)
                if mod!="qimamhd_booking_v2": continue
            else: xid=ref
            if xid not in defined:
                errors.append(f"{rel}: references local xmlid before definition: {xid}")
        xid=el.attrib.get("id")
        if xid: defined[xid]=(idx,rel)
    # record ids are attributes too and handled above
print("XMLID ORDER GATE:", "PASS" if not errors else "FAIL")
for e in errors: print(" -",e)
raise SystemExit(1 if errors else 0)
