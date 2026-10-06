# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class BookingStudioService(models.AbstractModel):
    _name="qimam.booking.studio.service"
    _description="Guided Booking Studio Service"

    @api.model
    def bootstrap(self, mode=None):
        company=self.env.company
        branch=self.env.user.branch_id
        business=company.qimam_booking_business_mode or "events"
        if mode not in ("events","hotel"):
            mode="hotel" if business=="hotel" else "events"
        partners=self.env["res.partner"].search([("customer_rank",">",0)],limit=12,order="write_date desc")
        result={
            "mode":mode,"business_mode":business,
            "customers":[{"id":p.id,"name":p.name,"phone":p.phone or p.mobile or ""} for p in partners],
            "currency":company.currency_id.symbol or company.currency_id.name,
            "branch":{"id":branch.id,"name":branch.name},
        }
        if mode=="events":
            halls=self.env["qimam.booking.hall"].search([("branch_id","=",branch.id),("active","=",True)],order="capacity,name")
            periods=self.env["qimam.booking.period"].search([("branch_id","=",branch.id),("active","=",True)],order="sequence,name")
            result.update({
                "halls":[{"id":h.id,"name":h.name,"capacity":h.capacity,"price":h.base_price} for h in halls],
                "periods":[{"id":p.id,"name":p.name} for p in periods],
            })
        else:
            types=self.env["qimam.booking.resource.type"].search([("branch_id","=",branch.id),("booking_mode","=","stay"),("active","=",True)])
            result["types"]=[{"id":t.id,"name":t.name} for t in types]
        return result

    @api.model
    def search_customers(self, term):
        term=(term or "").strip()
        if not term:return []
        partners=self.env["res.partner"].search(["|","|",("name","ilike",term),("phone","ilike",term),("mobile","ilike",term)],limit=10)
        return [{"id":p.id,"name":p.name,"phone":p.phone or p.mobile or ""} for p in partners]

    @api.model
    def event_quote(self, booking_date, hall_id, period_ids):
        if not booking_date or not hall_id or not period_ids:
            return {"ok":False,"message":_("Choose date, hall and at least one period.")}
        day=fields.Date.from_string(booking_date)
        hall=self.env["qimam.booking.hall"].browse(int(hall_id)).exists()
        periods=self.env["qimam.booking.period"].browse([int(x) for x in period_ids]).exists()
        if not hall or hall.branch_id != self.env.user.branch_id:
            return {"ok":False,"message":_("Hall is not available.")}
        blocking=self.env["qimam.booking"].search([
            ("branch_id","=",self.env.user.branch_id.id),("hall_id","=",hall.id),("booking_date","=",day),
            ("state","in",["hold","confirmed","preparing","event","completed"])
        ])
        busy=set(blocking.mapped("period_line_ids.period_id").ids)
        wanted=set(periods.ids)
        if busy & wanted:
            names=", ".join(self.env["qimam.booking.period"].browse(list(busy & wanted)).mapped("name"))
            return {"ok":False,"code":"PERIOD_ALREADY_BOOKED","message":_("Unavailable periods: %s")%names}
        # Hall price is a snapshot baseline; final tax/service calculation remains on booking model.
        return {"ok":True,"hall":{"id":hall.id,"name":hall.name,"capacity":hall.capacity},
                "periods":[{"id":p.id,"name":p.name} for p in periods],
                "base":hall.base_price,"currency":hall.currency_id.symbol or hall.currency_id.name,
                "date":day.isoformat()}

    @api.model
    def stay_quote(self, checkin_date, checkout_date, guests=1):
        return self.env["qimam.booking.workspace.service"].find_stay_options(checkin_date,checkout_date,guests)

    @api.model
    def create_stay(self, payload):
        partner_id=int(payload.get("partner_id") or 0)
        resource_id=int(payload.get("resource_id") or 0)
        if not partner_id or not resource_id:
            raise UserError(_("Customer and room are required."))
        resource=self.env["qimam.booking.resource"].browse(resource_id).exists()
        if not resource or resource.branch_id != self.env.user.branch_id or resource.booking_mode!="stay":
            raise UserError(_("Invalid room/resource."))
        vals={
            "partner_id":partner_id,"resource_id":resource.id,"branch_id":self.env.user.branch_id.id,
            "checkin_date":payload.get("checkin_date"),"checkout_date":payload.get("checkout_date"),
            "adults":max(int(payload.get("adults") or 1),1),
            "children":max(int(payload.get("children") or 0),0),
            "price_per_night":resource.base_price,
            "state":"hold" if payload.get("hold") else "draft",
        }
        rec=self.env["qimam.stay.booking"].create(vals)
        return {"id":rec.id,"name":rec.name,"model":"qimam.stay.booking","state":rec.state}

    @api.model
    def create_event(self, payload):
        partner_id=int(payload.get("partner_id") or 0)
        hall_id=int(payload.get("hall_id") or 0)
        period_ids=[int(x) for x in (payload.get("period_ids") or [])]
        day=payload.get("booking_date")
        quote=self.event_quote(day,hall_id,period_ids)
        if not quote.get("ok"):
            raise UserError(quote.get("message"))
        if not partner_id:
            raise UserError(_("Customer is required."))
        # Use canonical booking model; period line command is the existing relation contract.
        vals={"partner_id":partner_id,"hall_id":hall_id,"branch_id":self.env.user.branch_id.id,"booking_date":day,
              "period_line_ids":[(0,0,{"period_id":pid}) for pid in period_ids]}
        rec=self.env["qimam.booking"].create(vals)
        return {"id":rec.id,"name":rec.name,"model":"qimam.booking","state":rec.state}
