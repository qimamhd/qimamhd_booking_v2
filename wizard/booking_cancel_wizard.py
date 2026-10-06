# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BookingCancelWizard(models.TransientModel):
    _name = "qimam.booking.cancel.wizard"
    _description = "Cancel Booking Wizard"

    booking_id = fields.Many2one("qimam.booking", required=True, readonly=True)
    reason = fields.Text(required=True)
    cancel_draft_invoices = fields.Boolean(
        string="Cancel draft invoices",
        default=True,
        help="Draft invoices linked to the booking will be cancelled before the slot is released.",
    )
    posted_invoice_count = fields.Integer(compute="_compute_financial_status")
    draft_invoice_count = fields.Integer(compute="_compute_financial_status")
    amount_due = fields.Monetary(
        related="booking_id.amount_due", readonly=True, currency_field="currency_id"
    )
    amount_paid = fields.Monetary(
        related="booking_id.amount_paid", readonly=True, currency_field="currency_id"
    )
    currency_id = fields.Many2one(related="booking_id.currency_id", readonly=True)
    financial_action = fields.Selection(
        [("none", "Ready to cancel"), ("review", "Financial reversal required")],
        compute="_compute_financial_status", readonly=True
    )

    @api.depends("booking_id", "booking_id.invoice_ids.state")
    def _compute_financial_status(self):
        for rec in self:
            active = rec.booking_id.invoice_ids.filtered(lambda m: m.state != "cancel")
            posted = active.filtered(lambda m: m.state == "posted")
            drafts = active.filtered(lambda m: m.state == "draft")
            rec.posted_invoice_count = len(posted)
            rec.draft_invoice_count = len(drafts)
            rec.financial_action = "review" if posted else "none"

    def action_cancel(self):
        self.ensure_one()
        booking = self.booking_id
        posted = booking.invoice_ids.filtered(lambda m: m.state == "posted")
        if posted:
            raise UserError(_(
                "Cancellation is blocked because posted accounting documents exist. "
                "Create the required credit note/refund/reconciliation first. "
                "Reversing accounting documents does not cancel the booking automatically; "
                "return here after the financial workflow is complete."
            ))

        drafts = booking.invoice_ids.filtered(lambda m: m.state == "draft")
        if drafts and not self.cancel_draft_invoices:
            raise UserError(_("Cancel the draft invoices or enable 'Cancel draft invoices' first."))
        if drafts:
            drafts.button_cancel()

        booking.write({
            "state": "cancelled",
            "cancellation_reason": self.reason,
            "cancelled_by": self.env.user.id,
            "cancelled_at": fields.Datetime.now(),
            "hold_until": False,
        })
        return {"type": "ir.actions.act_window_close"}
