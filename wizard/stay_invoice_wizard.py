# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
class StayInvoiceWizard(models.TransientModel):
    _name="qimam.stay.invoice.wizard"; _description="Hotel Stay Invoice Wizard"
    stay_id=fields.Many2one("qimam.stay.booking",required=True,readonly=True)
    invoice_type=fields.Selection([("full","Full stay"),("deposit","Deposit"),("final","Remaining / Final")],default="full",required=True)
    deposit_percent=fields.Float(default=30.0)
    already_invoiced_percent=fields.Float(compute="_compute")
    invoice_percent=fields.Float(compute="_compute")
    preview_amount=fields.Monetary(compute="_compute",currency_field="currency_id")
    currency_id=fields.Many2one(related="stay_id.currency_id",readonly=True)
    @api.depends("stay_id","invoice_type","deposit_percent")
    def _compute(self):
        for r in self:
            existing=r.stay_id._reserved_invoice_factor()*100.0 if r.stay_id else 0.0; remaining=max(100-existing,0.0)
            pct=min(max(r.deposit_percent,0.0),remaining) if r.invoice_type=="deposit" else remaining
            r.already_invoiced_percent=existing; r.invoice_percent=pct; r.preview_amount=(r.stay_id.amount_total or 0.0)*pct/100.0
    @api.constrains("deposit_percent")
    def _check_pct(self):
        for r in self:
            if r.invoice_type=="deposit" and not 0<r.deposit_percent<=100: raise ValidationError(_("Deposit percentage must be between 0 and 100."))
    def action_create_invoice(self):
        self.ensure_one(); stay=self.stay_id; stay._lock_financial_capacity()
        remaining=max(1.0-stay._reserved_invoice_factor(),0.0)
        if remaining<=0.000001: raise UserError(_("The stay is already fully invoiced/reserved."))
        if self.invoice_type=="deposit": factor=min(self.deposit_percent/100.0,remaining); kind="deposit"
        elif self.invoice_type=="final": factor=remaining; kind="final"
        else: factor=remaining; kind="full" if remaining>=0.999999 else "final"
        vals={"type":"out_invoice","partner_id":stay.partner_id.id,"invoice_origin":stay.name,
              "qimam_stay_id":stay.id,"qimam_booking_invoice_kind":kind,"qimam_booking_factor":factor,
              "invoice_line_ids":stay._prepare_invoice_lines(factor)}
        if "branch_id" in self.env["account.move"]._fields: vals["branch_id"]=stay.branch_id.id
        move=self.env["account.move"].create(vals)
        return {"type":"ir.actions.act_window","name":_("Customer Invoice"),"res_model":"account.move","view_mode":"form","res_id":move.id,"target":"current"}
