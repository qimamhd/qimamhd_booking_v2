# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo import api, fields, models, _

class BookingWorkspaceService(models.AbstractModel):
    _name="qimam.booking.workspace.service"
    _description="Booking OS Workspace Service"

    @api.model
    def bootstrap(self):
        company=self.env.company
        branch=self.env.user.branch_id
        today=fields.Date.context_today(self)
        mode=company.qimam_booking_business_mode or "events"
        event_domain=[("branch_id","=",branch.id),("booking_date","=",today),("state","!=","cancelled")]
        stay_domain=[("branch_id","=",branch.id),("state","in",["hold","confirmed","checked_in"]),
                     ("checkin_date","<=",today),("checkout_date",">",today)]
        events=self.env["qimam.booking"].search(event_domain)
        stays=self.env["qimam.stay.booking"].search(stay_domain)
        return {
            "company":{"id":company.id,"name":company.name,"mode":mode},
            "branch":{"id":branch.id,"name":branch.name},
            "today":today.isoformat(),
            "hijri":self.env["qimam.booking.calendar.service"].hijri_label(today),
            "metrics":{
                "events_today":len(events),
                "event_holds":len(events.filtered(lambda x:x.state=="hold")),
                "stays_active":len(stays),
                "checkins":self.env["qimam.stay.booking"].search_count([
                    ("branch_id","=",branch.id),("checkin_date","=",today),("state","in",["hold","confirmed"])]),
                "checkouts":self.env["qimam.stay.booking"].search_count([
                    ("branch_id","=",branch.id),("checkout_date","=",today),("state","in",["confirmed","checked_in"])]),
            }
        }

    @api.model
    def find_stay_options(self, checkin_date, checkout_date, guests=1):
        Resource=self.env["qimam.booking.resource"]
        Stay=self.env["qimam.stay.booking"]
        checkin=fields.Date.from_string(checkin_date)
        checkout=fields.Date.from_string(checkout_date)
        if not checkin or not checkout or checkout <= checkin:
            return {"options":[],"message":_("Choose a valid stay range.")}
        resources=Resource.search([
            ("branch_id","=",self.env.user.branch_id.id),("booking_mode","=","stay"),
            ("active","=",True),("capacity",">=",max(int(guests or 1),1))
        ],order="base_price,capacity,name")
        busy=Stay.search([
            ("branch_id","=",self.env.user.branch_id.id),("state","in",["hold","confirmed","checked_in"]),
            ("checkin_date","<",checkout),("checkout_date",">",checkin)
        ]).mapped("resource_id")
        free=resources-busy
        nights=(checkout-checkin).days
        return {"options":[{
            "id":r.id,"name":r.name,"code":r.code,"type":r.resource_type_id.name,
            "capacity":r.capacity,"price":r.base_price,"total":r.base_price*nights,
            "currency":r.currency_id.symbol or r.currency_id.name
        } for r in free[:12]],"nights":nights}


    @api.model
    def today_operations(self):
        today=fields.Date.context_today(self)
        company=self.env.company
        branch=self.env.user.branch_id
        items=[]
        for b in self.env["qimam.booking"].search([
            ("branch_id","=",branch.id),("booking_date","=",today),("state","!=","cancelled")
        ], order="state,id"):
            items.append({
                "kind":"event","id":b.id,"title":b.partner_id.name or b.name,
                "subtitle":b.hall_id.name if b.hall_id else "",
                "state":b.state,"time_label":_("Today"),"attention":getattr(b,"attention_message","") or "",
            })
        for st in self.env["qimam.stay.booking"].search([
            ("branch_id","=",branch.id),("state","in",["hold","confirmed","checked_in"]),
            "|",("checkin_date","=",today),("checkout_date","=",today)
        ], order="checkin_date,id"):
            if st.checkin_date==today:
                items.append({"kind":"arrival","id":st.id,"title":st.partner_id.name,
                    "subtitle":st.resource_id.name,"state":st.state,"time_label":_("Arrival"),"attention":""})
            if st.checkout_date==today:
                items.append({"kind":"departure","id":st.id,"title":st.partner_id.name,
                    "subtitle":st.resource_id.name,"state":st.state,"time_label":_("Departure"),"attention":""})
        rank={"departure":0,"arrival":1,"event":2}
        items.sort(key=lambda x:(rank.get(x["kind"],9),x["subtitle"],x["title"]))
        return {"date":today.isoformat(),"hijri":self.env["qimam.booking.calendar.service"].hijri_label(today),"items":items}

    @api.model
    def booking_preview(self, model, record_id):
        if model=="qimam.stay.booking":
            r=self.env[model].browse(int(record_id)).exists()
            if not r or r.branch_id not in self.env.user.allowed_branch_ids:return {}
            return {"model":model,"id":r.id,"name":r.name,"customer":r.partner_id.name,
                "resource":r.resource_id.name,"state":r.state,"start":str(r.checkin_date),
                "end":str(r.checkout_date),"amount":r.amount_total,"currency":r.currency_id.symbol or "",
                "primary_action":"checkin" if r.state=="confirmed" else ("checkout" if r.state=="checked_in" else "")}
        if model=="qimam.booking":
            r=self.env[model].browse(int(record_id)).exists()
            if not r or r.branch_id not in self.env.user.allowed_branch_ids:return {}
            return {"model":model,"id":r.id,"name":r.name,"customer":r.partner_id.name,
                "resource":r.hall_id.name if r.hall_id else "","state":r.state,"start":str(r.booking_date),
                "end":"","amount":r.amount_total,"currency":r.currency_id.symbol or "",
                "attention":getattr(r,"attention_message","") or "","primary_action":""}
        return {}

    @api.model
    def execute_primary_action(self, model, record_id, action):
        if model!="qimam.stay.booking":
            return {"ok":False}
        rec=self.env[model].browse(int(record_id)).exists()
        if not rec or rec.branch_id not in self.env.user.allowed_branch_ids:return {"ok":False}
        if action=="checkin": rec.action_checkin()
        elif action=="checkout": rec.action_checkout()
        else:return {"ok":False}
        return {"ok":True,"state":rec.state}

