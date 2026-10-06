# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

STAY_BLOCKING_STATES=("hold","confirmed","checked_in")

class StayBooking(models.Model):
    _name="qimam.stay.booking"
    _description="Hotel / Stay Booking"
    _inherit=["mail.thread","mail.activity.mixin"]
    _order="checkin_date desc, id desc"

    name=fields.Char(default=lambda self:_("New"),copy=False,readonly=True,index=True,tracking=True)
    partner_id=fields.Many2one("res.partner",required=True,index=True,tracking=True)
    resource_id=fields.Many2one("qimam.booking.resource",required=True,index=True,tracking=True,
        domain="[('booking_mode','=','stay'),('branch_id','=',branch_id)]")
    checkin_date=fields.Date(required=True,index=True,tracking=True)
    checkout_date=fields.Date(required=True,index=True,tracking=True)
    nights=fields.Integer(compute="_compute_nights",store=True)
    adults=fields.Integer(default=1)
    children=fields.Integer(default=0)
    state=fields.Selection([("draft","Draft"),("hold","Hold"),("confirmed","Confirmed"),
        ("checked_in","Checked In"),("checked_out","Checked Out"),("cancelled","Cancelled")],
        default="draft",required=True,index=True,tracking=True)
    hold_until=fields.Datetime(copy=False,tracking=True)
    company_id=fields.Many2one("res.company",required=True,default=lambda self:self.env.company,index=True)
    currency_id=fields.Many2one(related="company_id.currency_id",readonly=True)
    price_per_night=fields.Monetary(currency_field="currency_id",tracking=True)
    room_tax_ids=fields.Many2many("account.tax","qimam_stay_tax_rel","stay_id","tax_id",
        string="Stay Taxes",domain=[("type_tax_use","=","sale")])
    amount_untaxed=fields.Monetary(compute="_compute_amounts",store=True,currency_field="currency_id")
    amount_tax=fields.Monetary(compute="_compute_amounts",store=True,currency_field="currency_id")
    amount_total=fields.Monetary(compute="_compute_amounts",store=True,currency_field="currency_id",tracking=True)
    note=fields.Text()
    color=fields.Integer(compute="_compute_color")

    invoice_ids=fields.One2many("account.move","qimam_stay_id",string="Invoices",readonly=True)
    invoice_count=fields.Integer(compute="_compute_financial_status")
    amount_invoiced=fields.Monetary(compute="_compute_financial_status",currency_field="currency_id")
    amount_credited=fields.Monetary(compute="_compute_financial_status",currency_field="currency_id")
    amount_due=fields.Monetary(compute="_compute_financial_status",currency_field="currency_id")
    amount_paid=fields.Monetary(compute="_compute_financial_status",currency_field="currency_id")
    invoice_progress=fields.Float(compute="_compute_financial_status")
    financial_status=fields.Selection([
        ("not_invoiced","Not Invoiced"),("draft_invoice","Draft Invoice"),("invoiced","Invoiced"),
        ("partial","Partially Paid"),("paid","Paid"),("credit","Credit / Reversal")],
        compute="_compute_financial_status")
    cancellation_reason=fields.Text(readonly=True,tracking=True)
    cancelled_by=fields.Many2one("res.users",readonly=True,copy=False)
    cancelled_at=fields.Datetime(readonly=True,copy=False)

    @api.depends("checkin_date","checkout_date")
    def _compute_nights(self):
        for rec in self:
            rec.nights=max((rec.checkout_date-rec.checkin_date).days,0) if rec.checkin_date and rec.checkout_date else 0

    @api.depends("nights","price_per_night","room_tax_ids","partner_id")
    def _compute_amounts(self):
        for rec in self:
            result=rec.room_tax_ids.compute_all(rec.price_per_night or 0.0,currency=rec.currency_id,
                quantity=rec.nights or 0,product=False,partner=rec.partner_id)
            rec.amount_untaxed=result["total_excluded"]
            rec.amount_total=result["total_included"]
            rec.amount_tax=rec.amount_total-rec.amount_untaxed

    @api.depends("state")
    def _compute_color(self):
        palette={"draft":0,"hold":2,"confirmed":4,"checked_in":7,"checked_out":10,"cancelled":1}
        for rec in self: rec.color=palette.get(rec.state,0)

    @api.depends("invoice_ids.state","invoice_ids.type","invoice_ids.amount_total","invoice_ids.amount_residual",
                 "invoice_ids.qimam_booking_factor")
    def _compute_financial_status(self):
        for rec in self:
            active=rec.invoice_ids.filtered(lambda m:m.state!="cancel")
            posted=active.filtered(lambda m:m.state=="posted")
            invoices=posted.filtered(lambda m:m.type=="out_invoice")
            credits=posted.filtered(lambda m:m.type=="out_refund")
            invoiced=sum(invoices.mapped("amount_total")); credited=sum(credits.mapped("amount_total"))
            invoice_residual=sum(invoices.mapped("amount_residual")); credit_residual=sum(credits.mapped("amount_residual"))
            net_due=max(invoice_residual-credit_residual,0.0); net_invoiced=max(invoiced-credited,0.0)
            paid=max(net_invoiced-net_due,0.0)
            factor=max(sum(invoices.mapped("qimam_booking_factor"))-sum(credits.mapped("qimam_booking_factor")),0.0)
            rec.invoice_count=len(active); rec.amount_invoiced=invoiced; rec.amount_credited=credited
            rec.amount_due=net_due; rec.amount_paid=paid; rec.invoice_progress=min(factor*100.0,100.0)
            if credits: rec.financial_status="credit"
            elif not active: rec.financial_status="not_invoiced"
            elif not posted: rec.financial_status="draft_invoice"
            elif net_due<=rec.currency_id.rounding: rec.financial_status="paid"
            elif paid>rec.currency_id.rounding: rec.financial_status="partial"
            else: rec.financial_status="invoiced"

    @api.onchange("resource_id")
    def _onchange_resource(self):
        if self.resource_id and self.state=="draft":
            self.price_per_night=self.resource_id.base_price
            self.room_tax_ids=self.resource_id.tax_ids

    @api.constrains("resource_id","checkin_date","checkout_date","state","branch_id")
    def _check_stay_integrity(self):
        for rec in self:
            if not rec.resource_id or not rec.checkin_date or not rec.checkout_date: continue
            if rec.resource_id.booking_mode!="stay": raise ValidationError(_("Only stay-mode resources can be used for hotel stays."))
            if rec.resource_id.branch_id!=rec.branch_id: raise ValidationError(_("The room/resource must belong to the same branch as the stay."))
            if rec.checkout_date<=rec.checkin_date: raise ValidationError(_("Check-out must be after check-in."))
            if rec.state not in STAY_BLOCKING_STATES: continue
            rec._lock_resource()
            conflict=self.search([("id","!=",rec.id),("branch_id","=",rec.branch_id.id),("resource_id","=",rec.resource_id.id),
                ("state","in",STAY_BLOCKING_STATES),("checkin_date","<",rec.checkout_date),("checkout_date",">",rec.checkin_date)],limit=1)
            if conflict: raise ValidationError(_("This room/resource overlaps booking %s.")%conflict.name)

    def _lock_resource(self):
        self.ensure_one()
        self.env.cr.execute("SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
            ("qimam.stay.branch:%s"%self.branch_id.id,str(self.resource_id.id)))

    def _lock_financial_capacity(self):
        self.ensure_one()
        self.env.cr.execute("SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
            ("qimam.stay.invoice",str(self.id)))

    def _net_invoiced_factor(self):
        self.ensure_one(); posted=self.invoice_ids.filtered(lambda m:m.state=="posted")
        return max(sum(posted.filtered(lambda m:m.type=="out_invoice").mapped("qimam_booking_factor"))-
                   sum(posted.filtered(lambda m:m.type=="out_refund").mapped("qimam_booking_factor")),0.0)

    def _reserved_invoice_factor(self):
        self.ensure_one()
        inv=self.invoice_ids.filtered(lambda m:m.type=="out_invoice" and m.state in ("draft","posted"))
        cr=self.invoice_ids.filtered(lambda m:m.type=="out_refund" and m.state=="posted")
        return max(sum(inv.mapped("qimam_booking_factor"))-sum(cr.mapped("qimam_booking_factor")),0.0)

    def _prepare_invoice_lines(self,factor=1.0):
        self.ensure_one()
        return [(0,0,{"name":_("Stay: %s (%s nights)")%(self.resource_id.name,self.nights),
            "quantity":self.nights*factor,"price_unit":self.price_per_night,
            "tax_ids":[(6,0,self.room_tax_ids.ids)]})]

    def _unresolved_posted_financials(self):
        self.ensure_one()
        posted=self.invoice_ids.filtered(lambda m:m.state=="posted")
        net_factor=self._net_invoiced_factor()
        inv_res=sum(posted.filtered(lambda m:m.type=="out_invoice").mapped("amount_residual"))
        cr_res=sum(posted.filtered(lambda m:m.type=="out_refund").mapped("amount_residual"))
        return net_factor>0.000001 or abs(inv_res-cr_res)>self.currency_id.rounding

    @api.model
    def create(self,vals):
        if vals.get("name",_("New"))==_("New"): vals["name"]=self.env["ir.sequence"].next_by_code("qimam.stay.booking") or _("New")
        if vals.get("resource_id"):
            r=self.env["qimam.booking.resource"].browse(vals["resource_id"])
            if not vals.get("price_per_night"): vals["price_per_night"]=r.base_price
            if "room_tax_ids" not in vals: vals["room_tax_ids"]=[(6,0,r.tax_ids.ids)]
        rec=super().create(vals); rec._check_stay_integrity(); return rec

    def write(self,vals):
        res=super().write(vals)
        if set(vals)&{"resource_id","checkin_date","checkout_date","state","branch_id"}: self._check_stay_integrity()
        return res

    def action_hold(self): self.write({"state":"hold"})

    def action_confirm(self):
        for rec in self:
            rec._check_stay_integrity()
            policy=rec.company_id.qimam_booking_confirmation_policy or "manual"
            posted=rec.invoice_ids.filtered(lambda m:m.type=="out_invoice" and m.state=="posted")
            if policy=="invoice" and not posted: raise UserError(_("A posted customer invoice is required before confirmation."))
            if policy=="deposit":
                pct=max(min(rec.company_id.qimam_booking_default_deposit_percent or 0.0,100.0),0.0)
                required=rec.currency_id.round(rec.amount_total*pct/100.0)
                if rec.amount_paid+rec.currency_id.rounding<required:
                    raise UserError(_("A paid deposit of at least %s %s is required before confirmation.")%(required,rec.currency_id.symbol or rec.currency_id.name))
            rec.write({"state":"confirmed","hold_until":False})

    def action_checkin(self):
        for rec in self:
            if rec.state!="confirmed": raise UserError(_("Only confirmed stays can check in."))
        self.write({"state":"checked_in"})

    def action_checkout(self):
        for rec in self:
            if rec.state!="checked_in": raise UserError(_("Only checked-in stays can check out."))
        self.write({"state":"checked_out"})

    def action_cancel(self):
        for rec in self:
            if rec.state in ("checked_in","checked_out"): raise UserError(_("Checked-in/out stays require controlled financial and operational handling."))
            if rec.invoice_ids.filtered(lambda m:m.state=="posted"):
                raise UserError(_("Posted accounting documents exist. Reverse/refund them before cancelling the stay."))
            drafts=rec.invoice_ids.filtered(lambda m:m.state=="draft")
            if drafts: raise UserError(_("Draft invoices exist. Use the controlled cancellation wizard."))
            rec.write({"state":"cancelled","hold_until":False,"cancelled_by":self.env.user.id,"cancelled_at":fields.Datetime.now()})

    def action_reopen_cancelled(self):
        for rec in self:
            if rec.state!="cancelled": raise UserError(_("Only cancelled stays can be reopened."))
            if rec._unresolved_posted_financials(): raise UserError(_("Unresolved posted financial exposure prevents reopening."))
            rec._lock_resource()
            # validate prospective blocking state BEFORE changing state
            conflict=self.search([("id","!=",rec.id),("branch_id","=",rec.branch_id.id),("resource_id","=",rec.resource_id.id),
                ("state","in",STAY_BLOCKING_STATES),("checkin_date","<",rec.checkout_date),("checkout_date",">",rec.checkin_date)],limit=1)
            if conflict: raise UserError(_("Cannot reopen: the room is now occupied by %s.")%conflict.name)
            rec.write({"state":"draft","cancellation_reason":False,"cancelled_by":False,"cancelled_at":False})

    def action_view_invoices(self):
        self.ensure_one(); action=self.env.ref("account.action_move_out_invoice_type").read()[0]
        action["domain"]=[("qimam_stay_id","=",self.id)]
        action["context"]={"default_qimam_stay_id":self.id,"default_partner_id":self.partner_id.id}
        return action

    def action_create_invoice(self):
        self.ensure_one()
        if self.state not in ("draft","hold","confirmed","checked_in","checked_out"):
            raise UserError(_("This stay cannot be invoiced in its current state."))
        return {"type":"ir.actions.act_window","name":_("Stay Invoice"),"res_model":"qimam.stay.invoice.wizard",
            "view_mode":"form","target":"new","context":{"default_stay_id":self.id}}

    def action_open_cancel_wizard(self):
        self.ensure_one()
        return {"type":"ir.actions.act_window","name":_("Cancel Stay"),"res_model":"qimam.stay.cancel.wizard",
            "view_mode":"form","target":"new","context":{"default_stay_id":self.id}}

    def action_open_reversal_wizard(self):
        self.ensure_one()
        return {"type":"ir.actions.act_window","name":_("Reverse Stay Invoice"),"res_model":"qimam.stay.reversal.wizard",
            "view_mode":"form","target":"new","context":{"default_stay_id":self.id}}
