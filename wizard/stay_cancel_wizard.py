# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
class StayCancelWizard(models.TransientModel):
    _name="qimam.stay.cancel.wizard"; _description="Controlled Stay Cancellation"
    stay_id=fields.Many2one("qimam.stay.booking",required=True,readonly=True)
    reason=fields.Text(required=True)
    cancel_draft_invoices=fields.Boolean(default=True)
    draft_invoice_count=fields.Integer(compute="_compute")
    posted_document_count=fields.Integer(compute="_compute")
    amount_paid=fields.Monetary(related="stay_id.amount_paid",currency_field="currency_id",readonly=True)
    amount_due=fields.Monetary(related="stay_id.amount_due",currency_field="currency_id",readonly=True)
    currency_id=fields.Many2one(related="stay_id.currency_id",readonly=True)
    @api.depends("stay_id.invoice_ids.state")
    def _compute(self):
        for r in self:
            r.draft_invoice_count=len(r.stay_id.invoice_ids.filtered(lambda m:m.state=="draft"))
            r.posted_document_count=len(r.stay_id.invoice_ids.filtered(lambda m:m.state=="posted"))
    def action_cancel(self):
        self.ensure_one(); stay=self.stay_id
        if stay.state in ("checked_in","checked_out"): raise UserError(_("Checked-in/out stays cannot be cancelled through this wizard."))
        posted=stay.invoice_ids.filtered(lambda m:m.state=="posted")
        if posted: raise UserError(_("Posted accounting documents exist. Reverse/refund and reconcile them before cancelling the stay."))
        drafts=stay.invoice_ids.filtered(lambda m:m.state=="draft")
        if drafts and not self.cancel_draft_invoices: raise UserError(_("Cancel the draft invoices or enable automatic draft cancellation."))
        for move in drafts: move.button_cancel()
        stay.write({"state":"cancelled","hold_until":False,"cancellation_reason":self.reason,
                    "cancelled_by":self.env.user.id,"cancelled_at":fields.Datetime.now()})
        return {"type":"ir.actions.act_window_close"}
