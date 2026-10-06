# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError

class BookingOperationTemplate(models.Model):
    _name="qimam.booking.operation.template"
    _description="Booking Operation Checklist Template"
    _order="sequence,id"
    name=fields.Char(required=True)
    sequence=fields.Integer(default=10)
    active=fields.Boolean(default=True)
    company_id=fields.Many2one("res.company",required=True,default=lambda self:self.env.company,index=True)
    category=fields.Selection([
        ("venue","Venue"),("guest","Guest Experience"),("service","Service"),
        ("safety","Safety"),("finance","Financial"),("handover","Handover")
    ],required=True,default="venue")
    timing=fields.Selection([
        ("before","Before Event"),("day","Event Day"),("after","After Event")
    ],required=True,default="before")
    required=fields.Boolean(default=True)
    blocks_event=fields.Boolean(string="Blocks Event Start")
    service_id=fields.Many2one("qimam.booking.service",ondelete="cascade",
        help="If set, this item is generated only when the service exists on the booking.")
    note=fields.Char()

class BookingOperationItem(models.Model):
    _name="qimam.booking.operation.item"
    _description="Booking Operational Readiness Item"
    _order="sequence,id"
    booking_id=fields.Many2one("qimam.booking",required=True,ondelete="cascade",index=True)
    company_id=fields.Many2one(related="booking_id.company_id",store=True,index=True)
    sequence=fields.Integer(default=10)
    name=fields.Char(required=True)
    category=fields.Selection([
        ("venue","Venue"),("guest","Guest Experience"),("service","Service"),
        ("safety","Safety"),("finance","Financial"),("handover","Handover")
    ],required=True)
    timing=fields.Selection([("before","Before Event"),("day","Event Day"),("after","After Event")],required=True)
    required=fields.Boolean(default=True)
    blocks_event=fields.Boolean()
    responsible_id=fields.Many2one("res.users",domain="[('company_ids','in',company_id)]")
    due_date=fields.Date()
    state=fields.Selection([
        ("todo","To Do"),("progress","In Progress"),("done","Done"),("blocked","Blocked"),("skipped","Skipped")
    ],default="todo",required=True,index=True)
    note=fields.Char()
    completed_by=fields.Many2one("res.users",readonly=True)
    completed_at=fields.Datetime(readonly=True)

    def write(self, vals):
        structural={"booking_id","branch_id","company_id","name","category","timing","required","blocks_event","sequence"}
        if structural & set(vals) and not self.env.user.has_group("qimamhd_booking_v2.group_booking_supervisor"):
            raise AccessError(_("Only Booking Supervisors may change operational checklist structure."))
        return super().write(vals)

    def action_skip(self):
        if not self.env.user.has_group("qimamhd_booking_v2.group_booking_supervisor"):
            raise AccessError(_("Only Booking Supervisors may skip readiness items."))
        self.write({"state":"skipped","completed_by":self.env.user.id,"completed_at":fields.Datetime.now()})

    def action_start(self):
        self.filtered(lambda x:x.state=="todo").write({"state":"progress"})
    def action_done(self):
        self.write({"state":"done","completed_by":self.env.user.id,"completed_at":fields.Datetime.now()})
    def action_block(self):
        self.write({"state":"blocked"})
    def action_reset(self):
        self.write({"state":"todo","completed_by":False,"completed_at":False})

class Booking(models.Model):
    _inherit="qimam.booking"

    operation_item_ids=fields.One2many("qimam.booking.operation.item","booking_id",string="Operational Readiness")
    operation_count=fields.Integer(compute="_compute_operation_readiness")
    readiness_percent=fields.Float(compute="_compute_operation_readiness")
    blocking_operation_count=fields.Integer(compute="_compute_operation_readiness")
    operational_status=fields.Selection([
        ("not_planned","Not Planned"),("at_risk","At Risk"),("in_progress","In Progress"),("ready","Ready"),("closed","Closed")
    ],compute="_compute_operation_readiness")

    @api.depends("operation_item_ids.state","operation_item_ids.required","operation_item_ids.blocks_event","state")
    def _compute_operation_readiness(self):
        for b in self:
            items=b.operation_item_ids
            required=items.filtered("required")
            completed=required.filtered(lambda x:x.state in ("done","skipped"))
            blockers=items.filtered(lambda x:x.blocks_event and x.state not in ("done","skipped"))
            b.operation_count=len(items)
            b.blocking_operation_count=len(blockers)
            b.readiness_percent=(len(completed)/len(required)*100.0) if required else (100.0 if items else 0.0)
            if b.state=="completed": b.operational_status="closed"
            elif not items: b.operational_status="not_planned"
            elif blockers or items.filtered(lambda x:x.state=="blocked"): b.operational_status="at_risk"
            elif b.readiness_percent>=99.99: b.operational_status="ready"
            else: b.operational_status="in_progress"

    def action_generate_operations(self):
        for b in self:
            if b.state=="cancelled":
                raise UserError(_("Cancelled bookings cannot generate operations."))
            existing=set(b.operation_item_ids.mapped("name"))
            services=set(b.service_line_ids.mapped("service_id").ids)
            templates=self.env["qimam.booking.operation.template"].search([
                ("branch_id","=",b.branch_id.id),("active","=",True)
            ])
            for t in templates:
                if t.service_id and t.service_id.id not in services:
                    continue
                if t.name in existing:
                    continue
                self.env["qimam.booking.operation.item"].create({
                    "booking_id":b.id,"branch_id":b.branch_id.id,"sequence":t.sequence,"name":t.name,"category":t.category,
                    "timing":t.timing,"required":t.required,"blocks_event":t.blocks_event,
                    "due_date":b.booking_date,"note":t.note,
                })
        return True

    def action_start_event(self):
        for b in self:
            blockers=b.operation_item_ids.filtered(lambda x:x.blocks_event and x.state not in ("done","skipped"))
            if blockers:
                raise UserError(_("Event cannot start. Complete the blocking readiness items first: %s") % ", ".join(blockers.mapped("name")))
        return super(Booking,self).action_start_event()
