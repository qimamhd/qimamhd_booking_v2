# -*- coding: utf-8 -*-
from odoo import http, fields, api, SUPERUSER_ID
from odoo.http import request
from odoo.modules.registry import Registry
from odoo.exceptions import AccessError, ValidationError, UserError

API_VERSION="2.0"
EVENT_BLOCKING=("hold","confirmed","preparing","event","completed")
STAY_BLOCKING=("hold","confirmed","checked_in")

def envelope(success,data=None,error=None,meta=None):
    result={"success":bool(success),"api_version":API_VERSION}
    if success: result["data"]=data if data is not None else {}
    else: result["error"]=error or {"code":"UNKNOWN_ERROR","message":"Unknown error"}
    if meta: result["meta"]=meta
    return result

def ok(data=None,meta=None): return envelope(True,data=data,meta=meta)
def fail(code,message,details=None):
    error={"code":code,"message":message}
    if details is not None:error["details"]=details
    return envelope(False,error=error)

def _bearer():
    header=request.httprequest.headers.get("Authorization","")
    return header[7:].strip() if header.lower().startswith("bearer ") else ""

def guarded(fn):
    def wrapper(*args,**kwargs):
        try:
            token=_bearer()
            device_id=request.httprequest.headers.get("X-Device-ID","")
            session=request.env["qimam.booking.api.session"].sudo().authenticate(token,device_id)
            # Execute all downstream ORM calls as the authenticated Odoo user.
            request.env=request.env(user=session.user_id.id)
            return fn(*args,**kwargs)
        except AccessError as exc:return fail("ACCESS_DENIED",str(exc))
        except ValidationError as exc:
            msg=str(exc);code="VALIDATION_ERROR"
            if "overlap" in msg.lower() or "period" in msg.lower() and "book" in msg.lower():code="AVAILABILITY_CONFLICT"
            return fail(code,msg)
        except UserError as exc:return fail("BUSINESS_RULE_VIOLATION",str(exc))
        except (KeyError,ValueError,TypeError) as exc:return fail("INVALID_PAYLOAD",str(exc))
    wrapper.__name__=fn.__name__
    return wrapper

def company_record(model,record_id,mode=None):
    rec=request.env[model].browse(int(record_id)).exists()
    if not rec:
        raise AccessError("Record is not available.")
    if "branch_id" in rec._fields and rec.branch_id not in request.env.user.allowed_branch_ids:
        raise AccessError("Record is not available in an allowed branch.")
    if "company_id" in rec._fields and rec.company_id != request.env.company:
        raise AccessError("Record belongs to another accounting company.")
    if mode and getattr(rec,"booking_mode",None)!=mode:
        raise ValidationError("Resource does not support booking mode '%s'."%mode)
    return rec


def active_branch(payload=None):
    payload=payload or {}
    requested=payload.get("branch_id")
    branch=request.env.user.branch_id
    if requested:
        branch=request.env["custom.branches"].browse(int(requested)).exists()
    if not branch or branch not in request.env.user.allowed_branch_ids:
        raise AccessError("Branch is not allowed for this user.")
    return branch

def customer_payload(p):
    return {"id":p.id,"name":p.name,"mobile":p.mobile or p.phone or "","email":p.email or ""}

class BookingApiV2(http.Controller):

    # ---------- Shared core ----------
    @http.route("/api/v2/bootstrap",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def bootstrap(self,**payload):
        c=request.env.company;mode=c.qimam_booking_business_mode or "events"
        return ok({
            "company":{"id":c.id,"name":c.name,"currency":c.currency_id.name,"currency_symbol":c.currency_id.symbol},
            "business_mode":mode,
            "branch":{"id":request.env.user.branch_id.id,"name":request.env.user.branch_id.name},
            "allowed_branches":[{"id":b.id,"name":b.name} for b in request.env.user.allowed_branch_ids],
            "capabilities":{
                "events":mode in ("events","mixed"),
                "stays":mode in ("hotel","mixed"),
                "event_periods":True,
                "stay_half_open_interval":True,
                "server_authoritative_availability":True,
                "server_authoritative_pricing":True,
            },
            "user":{"id":request.env.user.id,"name":request.env.user.name,
                    "is_supervisor":request.env.user.has_group("qimamhd_booking_v2.group_booking_supervisor"),
                    "is_manager":request.env.user.has_group("qimamhd_booking_v2.group_booking_manager")}
        })

    @http.route("/api/v2/customers/search",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def customers(self,**payload):
        term=(payload.get("q") or "").strip();limit=min(max(int(payload.get("limit") or 20),1),50)
        domain=[("customer_rank",">",0)] if "customer_rank" in request.env["res.partner"]._fields else []
        if term:domain+=["|","|",("name","ilike",term),("mobile","ilike",term),("phone","ilike",term)]
        rows=request.env["res.partner"].search(domain,limit=limit)
        return ok([customer_payload(x) for x in rows],{"limit":limit})

    # ---------- Events / halls ----------
    @http.route("/api/v2/events/catalog",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def event_catalog(self,**payload):
        c=request.env.company;branch=active_branch(payload)
        halls=request.env["qimam.booking.hall"].search([("branch_id","=",branch.id),("active","=",True)])
        periods=request.env["qimam.booking.period"].search([("branch_id","=",branch.id),("active","=",True)])
        return ok({"mode":"event","halls":[{"id":h.id,"name":h.name,"capacity":h.capacity,"base_price":h.base_price} for h in halls],
                   "periods":[{"id":p.id,"name":p.name,"code":p.code,"time_from":p.time_from,"time_to":p.time_to} for p in periods]})

    @http.route("/api/v2/events/availability",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def event_availability(self,**payload):
        date=fields.Date.from_string(payload["date"]);hall_id=payload.get("hall_id");branch=active_branch(payload)
        periods=request.env["qimam.booking.period"].search([("branch_id","=",branch.id),("active","=",True)])
        hd=[("branch_id","=",branch.id),("active","=",True)]
        if hall_id:hd.append(("id","=",int(hall_id)))
        halls=request.env["qimam.booking.hall"].search(hd);result=[]
        for hall in halls:
            cells=[]
            for period in periods:
                conflict=request.env["qimam.booking"].search([
                    ("branch_id","=",branch.id),("hall_id","=",hall.id),("booking_date","=",date),
                    ("state","in",EVENT_BLOCKING),("period_line_ids.period_id","=",period.id)],limit=1)
                cells.append({"period_id":period.id,"period_name":period.name,"available":not bool(conflict),
                              "status":conflict.state if conflict else "available"})
            result.append({"hall_id":hall.id,"hall_name":hall.name,"date":date.isoformat(),"periods":cells})
        return ok({"mode":"event","items":result})

    @http.route("/api/v2/events/bookings/create",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def event_create(self,**payload):
        branch=active_branch(payload)
        period_ids=list(dict.fromkeys(int(x) for x in payload["period_ids"]))
        if not period_ids:raise ValidationError("At least one period is required.")
        hall=company_record("qimam.booking.hall",payload["hall_id"])
        if hall.branch_id != branch: raise AccessError("Hall does not belong to the selected branch.")
        partner=request.env["res.partner"].browse(int(payload["partner_id"])).exists()
        if not partner:raise ValidationError("Customer does not exist.")
        periods=request.env["qimam.booking.period"].browse(period_ids).exists()
        if len(periods)!=len(period_ids) or any(p.branch_id!=branch for p in periods):
            raise ValidationError("One or more periods are invalid for the active company.")
        booking=request.env["qimam.booking"].create({
            "partner_id":partner.id,"branch_id":branch.id,"booking_date":fields.Date.from_string(payload["date"]),
            "hall_id":hall.id,"guest_count":int(payload.get("guest_count") or 0),"note":payload.get("note"),
            "period_line_ids":[(0,0,{"period_id":p.id}) for p in periods],
        })
        if payload.get("hold"):booking.action_hold()
        return ok(self._event(booking))

    @http.route("/api/v2/events/bookings/get",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def event_get(self,**payload):return ok(self._event(company_record("qimam.booking",payload["id"])))

    @http.route("/api/v2/events/bookings/action",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def event_action(self,**payload):
        b=company_record("qimam.booking",payload["id"]);action=payload["action"]
        allowed={"hold":"action_hold","confirm":"action_confirm","prepare":"action_prepare","start_event":"action_start_event","complete":"action_complete"}
        if action not in allowed:raise UserError("Unsupported event action.")
        getattr(b,allowed[action])()
        return ok(self._event(b))

    def _event(self,b):
        return {"mode":"event","branch":{"id":b.branch_id.id,"name":b.branch_id.name},"id":b.id,"number":b.name,"state":b.state,"date":b.booking_date.isoformat(),
                "customer":customer_payload(b.partner_id),"hall":{"id":b.hall_id.id,"name":b.hall_id.name},
                "periods":[{"id":p.id,"name":p.name} for p in b.period_ids],
                "guest_count":b.guest_count,"amount_total":b.amount_total,"currency":b.currency_id.name,
                "financial_status":b.financial_status,"readiness":getattr(b,"readiness_percent",0.0)}

    # ---------- Stays / hotel ----------
    @http.route("/api/v2/stays/resources",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def stay_resources(self,**payload):
        branch=active_branch(payload)
        rows=request.env["qimam.booking.resource"].search([
            ("branch_id","=",branch.id),("booking_mode","=","stay"),("active","=",True)])
        return ok({"mode":"stay","resources":[{"id":r.id,"name":r.name,"code":r.code,"capacity":r.capacity,
                   "floor":r.floor or "","base_price":r.base_price,"currency":r.currency_id.name,
                   "type":{"id":r.resource_type_id.id,"name":r.resource_type_id.name,"icon":r.resource_type_id.icon}} for r in rows]})

    @http.route("/api/v2/stays/availability",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def stay_availability(self,**payload):
        branch=active_branch(payload)
        start=fields.Date.from_string(payload["checkin"]);end=fields.Date.from_string(payload["checkout"])
        if end<=start:raise ValidationError("Check-out must be after check-in.")
        guests=max(int(payload.get("guests") or 1),1)
        domain=[("branch_id","=",branch.id),("booking_mode","=","stay"),("active","=",True),("capacity",">=",guests)]
        if payload.get("resource_id"):domain.append(("id","=",int(payload["resource_id"])))
        resources=request.env["qimam.booking.resource"].search(domain);items=[]
        for r in resources:
            conflict=request.env["qimam.stay.booking"].search([
                ("branch_id","=",branch.id),("resource_id","=",r.id),("state","in",STAY_BLOCKING),
                ("checkin_date","<",end),("checkout_date",">",start)],limit=1)
            if not conflict:
                nights=(end-start).days
                items.append({"resource_id":r.id,"name":r.name,"capacity":r.capacity,"available":True,
                              "checkin":start.isoformat(),"checkout":end.isoformat(),"nights":nights,
                              "price_per_night":r.base_price,"total":r.base_price*nights,"currency":r.currency_id.name})
        return ok({"mode":"stay","interval_semantics":"[checkin, checkout)","items":items})

    @http.route("/api/v2/stays/bookings/create",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def stay_create(self,**payload):
        branch=active_branch(payload)
        resource=company_record("qimam.booking.resource",payload["resource_id"],"stay")
        if resource.branch_id != branch: raise AccessError("Resource does not belong to the selected branch.")
        partner=request.env["res.partner"].browse(int(payload["partner_id"])).exists()
        if not partner:raise ValidationError("Customer does not exist.")
        rec=request.env["qimam.stay.booking"].create({
            "partner_id":partner.id,"resource_id":resource.id,"branch_id":branch.id,
            "checkin_date":fields.Date.from_string(payload["checkin"]),"checkout_date":fields.Date.from_string(payload["checkout"]),
            "adults":max(int(payload.get("adults") or 1),1),"children":max(int(payload.get("children") or 0),0),
            "note":payload.get("note"),"price_per_night":resource.base_price,
        })
        if payload.get("hold"):rec.action_hold()
        return ok(self._stay(rec))

    @http.route("/api/v2/stays/bookings/get",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def stay_get(self,**payload):return ok(self._stay(company_record("qimam.stay.booking",payload["id"])))

    @http.route("/api/v2/stays/bookings/action",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def stay_action(self,**payload):
        b=company_record("qimam.stay.booking",payload["id"]);action=payload["action"]
        allowed={"hold":"action_hold","confirm":"action_confirm","checkin":"action_checkin","checkout":"action_checkout","cancel":"action_cancel"}
        if action not in allowed:raise UserError("Unsupported stay action.")
        getattr(b,allowed[action])()
        return ok(self._stay(b))

    def _stay(self,b):
        return {"mode":"stay","branch":{"id":b.branch_id.id,"name":b.branch_id.name},"id":b.id,"number":b.name,"state":b.state,
                "customer":customer_payload(b.partner_id),
                "resource":{"id":b.resource_id.id,"name":b.resource_id.name,"type":b.resource_id.resource_type_id.name},
                "checkin":b.checkin_date.isoformat(),"checkout":b.checkout_date.isoformat(),"nights":b.nights,
                "adults":b.adults,"children":b.children,"price_per_night":b.price_per_night,
                "amount_untaxed":b.amount_untaxed,"amount_tax":b.amount_tax,"amount_total":b.amount_total,"currency":b.currency_id.name,
                "financial":{"status":b.financial_status,"invoice_progress":b.invoice_progress,"invoiced":b.amount_invoiced,
                             "credited":b.amount_credited,"paid":b.amount_paid,"due":b.amount_due}}

    # ---------- Temporary compatibility aliases (event domain only) ----------
    @http.route("/api/v2/periods",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def legacy_periods(self,**payload):
        data=self.event_catalog(**payload)
        if data.get("success"): data["data"]=data["data"]["periods"]
        return data

    @http.route("/api/v2/halls",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def legacy_halls(self,**payload):
        data=self.event_catalog(**payload)
        if data.get("success"): data["data"]=data["data"]["halls"]
        return data

    @http.route("/api/v2/availability",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def legacy_event_availability(self,**payload):
        mapped={"date":payload.get("date"),"hall_id":payload.get("hall_id"),"branch_id":payload.get("branch_id")}
        return self.event_availability(**mapped)

    @http.route("/api/v2/bookings/create",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def legacy_event_create(self,**payload):
        mapped=dict(payload)
        if "booking_date" in mapped and "date" not in mapped:mapped["date"]=mapped.pop("booking_date")
        return self.event_create(**mapped)

    @http.route("/api/v2/auth/logout",type="json",auth="none",methods=["POST"],csrf=False)
    @guarded
    def token_logout(self,**payload):
        token=_bearer()
        digest=__import__("hashlib").sha256(token.encode("utf-8")).hexdigest()
        session=request.env["qimam.booking.api.session"].sudo().search([
            ("access_hash","=",digest),("user_id","=",request.env.user.id),("revoked_at","=",False)
        ],limit=1)
        if session: session.revoke()
        return ok({"revoked":True})
