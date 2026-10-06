#!/usr/bin/env python3
from pathlib import Path
import ast, py_compile, re, sys
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]; checks=[]
def add(name,ok,detail=""): checks.append((name,bool(ok),detail))
errors=[]
for p in ROOT.rglob("*.py"):
    if "__pycache__" in p.parts: continue
    try: py_compile.compile(str(p),doraise=True)
    except Exception as e: errors.append(f"{p.relative_to(ROOT)}: {e}")
add("Python compile",not errors,"; ".join(errors))
errors=[]
for p in ROOT.rglob("*.xml"):
    try: ET.parse(str(p))
    except Exception as e: errors.append(f"{p.relative_to(ROOT)}: {e}")
add("XML parse",not errors,"; ".join(errors))
try: ast.literal_eval((ROOT/"__manifest__.py").read_text()); add("Manifest parse",True)
except Exception as e: add("Manifest parse",False,str(e))
api=(ROOT/"controllers/api.py").read_text()
add("API domain split","/api/v2/events/" in api and "/api/v2/stays/" in api)
add("Bearer guard",'Authorization' in api and 'qimam.booking.api.session' in api)
add("No top-level routed functions",not bool(re.search(r'^@http\\.route',api,re.M)))
stay=(ROOT/"models/stay_booking.py").read_text()
add("Stay branch/resource lock",'qimam.stay.branch:%s' in stay)
security=(ROOT/"security/booking_security.xml").read_text()
add("Branch record rules",'user.allowed_branch_ids.ids' in security)
add("custom_branch dependency",'"custom_branch_13"' in (ROOT/"__manifest__.py").read_text())
auth=(ROOT/"models/booking_api_auth.py").read_text()
add("Hashed token storage",'access_hash' in auth and 'refresh_hash' in auth and 'access_token=fields' not in auth)
add("Refresh rotation",'rec.sudo().write({"revoked_at":now})' in auth)
workspace=(ROOT/"models/booking_workspace_service.py").read_text()
add("Workspace methods are class methods",'    def today_operations(' in workspace)
move=(ROOT/"models/account_move.py").read_text(); stay=(ROOT/"models/stay_booking.py").read_text()
add("Hotel financial link",'qimam_stay_id' in move and '_reserved_invoice_factor' in stay)
add("Hotel controlled cancellation",'action_open_cancel_wizard' in stay and '_unresolved_posted_financials' in stay)
studio=(ROOT/"models/booking_studio_service.py").read_text()
add("Studio branch scope",'branch_id' in studio and '("company_id","=",company.id),("active","=",True)' not in studio)
commercial=(ROOT/"models/booking_commercial_service.py").read_text()
add("Commercial branch scope",'branch_id' in commercial and 'booking.company_id != self.env.company' not in commercial)
booking=(ROOT/"models/booking.py").read_text()
add("Canonical discount authorization",'_check_discount_authorization_vals' in booking and 'group_booking_supervisor' in booking)
add("Child line branch fields",'related="booking_id.branch_id"' in booking)
ops=(ROOT/"models/booking_operations_readiness.py").read_text()
add("Operation structure authorization",'Only Booking Supervisors may change operational checklist structure' in ops)
demo=(ROOT/"models/booking_demo_builder.py").read_text()
manifest=(ROOT/"__manifest__.py").read_text()
add("On-demand demo builder",'def build(self,branch_id=None)' in demo and 'booking_demo_builder' not in manifest)
add("Demo idempotency",'Demo data already exists for this branch' in demo)
add("Demo branch scope",'custom.branches' in demo and 'allowed_branch_ids' in demo)
add("No automatic demo manifest",'"demo"' not in manifest)
failed=[x for x in checks if not x[1]]
for n,ok,d in checks: print(("[PASS] " if ok else "[FAIL] ")+n+((" — "+d) if d else ""))
print("\\nRESULT:","PASS" if not failed else "FAIL")
sys.exit(1 if failed else 0)
