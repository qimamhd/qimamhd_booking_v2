# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models, _

BLOCKING = ["hold", "confirmed", "preparing", "event", "completed"]

class BookingDashboard(models.TransientModel):
    _name = "qimam.booking.dashboard"
    _description = "Booking Command Center"
    date = fields.Date(default=fields.Date.today, required=True)
    branch_id = fields.Many2one("custom.branches", default=lambda self: self.env.user.branch_id, required=True,
        domain=lambda self:[("id","in",self.env.user.allowed_branch_ids.ids)])
    booking_count = fields.Integer(compute="_compute_metrics")
    confirmed_count = fields.Integer(compute="_compute_metrics")
    hold_count = fields.Integer(compute="_compute_metrics")
    attention_count = fields.Integer(compute="_compute_metrics")

    def _day_domain(self):
        self.ensure_one()
        return [("branch_id","=",self.branch_id.id),("booking_date","=",self.date),("state","!=","cancelled")]

    @api.depends("date","branch_id")
    def _compute_metrics(self):
        B=self.env["qimam.booking"]
        for rec in self:
            rows=B.search(rec._day_domain())
            rec.booking_count=len(rows)
            rec.confirmed_count=len(rows.filtered(lambda b:b.state in ("confirmed","preparing","event","completed")))
            rec.hold_count=len(rows.filtered(lambda b:b.state=="hold"))
            rec.attention_count=len(rows.filtered(lambda b:b.overdue_amount>0 or b.state=="hold"))

    def action_day(self):
        self.ensure_one(); a=self.env.ref("qimamhd_booking_v2.action_qimam_booking").read()[0]; a["domain"]=self._day_domain(); return a
    def action_attention(self):
        self.ensure_one()
        ids=self.env["qimam.booking"].search(self._day_domain()).filtered(lambda b:b.overdue_amount>0 or b.state=="hold").ids
        a=self.env.ref("qimamhd_booking_v2.action_qimam_booking").read()[0]; a["domain"]=[("id","in",ids)]; return a
    def action_availability(self):
        self.ensure_one()
        return {"type":"ir.actions.act_window","name":_("Availability"),"res_model":"qimam.booking.availability.wizard","view_mode":"form","target":"current","context":{"default_booking_date":self.date}}
    def action_quick(self):
        self.ensure_one()
        return {"type":"ir.actions.act_window","name":_("Quick Booking"),"res_model":"qimam.booking.quick.wizard","view_mode":"form","target":"new","context":{"default_booking_date":self.date}}

class BookingAvailabilityWizard(models.TransientModel):
    _name = "qimam.booking.availability.wizard"
    _description = "Booking Availability"
    booking_date=fields.Date(default=fields.Date.today, required=True)
    hall_id=fields.Many2one("qimam.booking.hall")
    min_capacity=fields.Integer(string="Minimum Capacity")
    line_ids=fields.One2many("qimam.booking.availability.line","wizard_id",readonly=True)
    recommendation=fields.Char(compute="_compute_recommendation")

    def _hall_domain(self):
        d=[("branch_id","=",self.env.user.branch_id.id),("active","=",True)]
        if self.hall_id: d.append(("id","=",self.hall_id.id))
        if self.min_capacity: d.append(("capacity",">=",self.min_capacity))
        return d

    def _commands(self):
        B=self.env["qimam.booking"]
        halls=self.env["qimam.booking.hall"].search(self._hall_domain(),order="sequence,name")
        periods=self.env["qimam.booking.period"].search([("branch_id","=",self.env.user.branch_id.id),("active","=",True)],order="sequence,id")
        out=[(5,0,0)]
        for hall in halls:
            for period in periods:
                c=B.search([("branch_id","=",self.env.user.branch_id.id),("hall_id","=",hall.id),("booking_date","=",self.booking_date),
                            ("state","in",BLOCKING),("period_line_ids.period_id","=",period.id)],limit=1)
                out.append((0,0,{"hall_id":hall.id,"capacity":hall.capacity,"period_id":period.id,
                                 "status":c.state if c else "available","booking_id":c.id if c else False}))
        return out

    @api.depends("booking_date","hall_id","min_capacity")
    def _compute_recommendation(self):
        B=self.env["qimam.booking"]
        for rec in self:
            suggestion=False
            periods=self.env["qimam.booking.period"].search([("branch_id","=",self.env.user.branch_id.id),("active","=",True)],order="sequence,id")
            for hall in self.env["qimam.booking.hall"].search(rec._hall_domain(),order="capacity,sequence,name"):
                for period in periods:
                    busy=B.search_count([("branch_id","=",self.env.user.branch_id.id),("hall_id","=",hall.id),("booking_date","=",rec.booking_date),
                                         ("state","in",BLOCKING),("period_line_ids.period_id","=",period.id)])
                    if not busy: suggestion=_("Suggested: %s — %s")%(hall.name,period.name); break
                if suggestion: break
            rec.recommendation=suggestion or _("No matching free slot for the selected filters.")

    @api.onchange("booking_date","hall_id","min_capacity")
    def _onchange_filters(self):
        if self.booking_date: self.line_ids=self._commands()
    def action_refresh(self):
        self.ensure_one(); self.line_ids=self._commands()
        return {"type":"ir.actions.act_window","name":_("Availability"),"res_model":self._name,"view_mode":"form","res_id":self.id,"target":"current"}
    def action_previous(self):
        self.ensure_one(); self.booking_date-=timedelta(days=1); return self.action_refresh()
    def action_next(self):
        self.ensure_one(); self.booking_date+=timedelta(days=1); return self.action_refresh()
    def action_quick(self):
        self.ensure_one()
        return {"type":"ir.actions.act_window","name":_("Quick Booking"),"res_model":"qimam.booking.quick.wizard","view_mode":"form","target":"new","context":{"default_booking_date":self.booking_date}}

class BookingAvailabilityLine(models.TransientModel):
    _name="qimam.booking.availability.line"; _description="Availability Cell"; _order="hall_id,period_id"
    wizard_id=fields.Many2one("qimam.booking.availability.wizard",required=True,ondelete="cascade")
    hall_id=fields.Many2one("qimam.booking.hall",readonly=True); capacity=fields.Integer(readonly=True)
    period_id=fields.Many2one("qimam.booking.period",readonly=True)
    status=fields.Selection([("available","Available"),("hold","Hold"),("confirmed","Confirmed"),("preparing","Preparing"),("event","Event"),("completed","Completed")],readonly=True)
    booking_id=fields.Many2one("qimam.booking",readonly=True)
    def action_open(self):
        self.ensure_one()
        if self.booking_id:
            return {"type":"ir.actions.act_window","name":_("Booking"),"res_model":"qimam.booking","view_mode":"form","res_id":self.booking_id.id,"target":"current"}
        return {"type":"ir.actions.act_window","name":_("Quick Booking"),"res_model":"qimam.booking.quick.wizard","view_mode":"form","target":"new",
                "context":{"default_booking_date":self.wizard_id.booking_date,"default_hall_id":self.hall_id.id,"default_period_ids":[(6,0,[self.period_id.id])]}}
