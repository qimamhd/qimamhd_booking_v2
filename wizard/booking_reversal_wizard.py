# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BookingReversalWizard(models.TransientModel):
    _name = "qimam.booking.reversal.wizard"
    _description = "Booking Financial Reversal Wizard"

    booking_id = fields.Many2one("qimam.booking", required=True, readonly=True)
    invoice_id = fields.Many2one(
        "account.move", string="Posted Invoice", required=True,
        domain="[('qimam_booking_id','=',booking_id),('state','=','posted'),('type','=','out_invoice')]"
    )
    reason = fields.Char(required=True)
    refund_method = fields.Selection(
        [("refund", "Create draft credit note"), ("cancel", "Reverse and reconcile")],
        default="refund", required=True
    )
    amount_paid = fields.Monetary(related="booking_id.amount_paid", readonly=True, currency_field="currency_id")
    currency_id = fields.Many2one(related="booking_id.currency_id", readonly=True)

    def action_reverse(self):
        self.ensure_one()
        invoice = self.invoice_id
        if invoice.qimam_booking_id != self.booking_id or invoice.state != "posted":
            raise UserError(_("Select a posted invoice belonging to this booking."))

        # Use Odoo's standard reversal wizard to preserve accounting behavior.
        reversal = self.env["account.move.reversal"].with_context(
            active_model="account.move", active_ids=invoice.ids
        ).create({
            "refund_method": self.refund_method,
            "reason": self.reason,
            "date": fields.Date.context_today(self),
        })
        result = reversal.reverse_moves()

        # Propagate booking metadata to generated refund(s).
        refunds = self.env["account.move"].search([
            ("reversed_entry_id", "=", invoice.id),
            ("type", "=", "out_refund"),
        ])
        refunds.write({
            "qimam_booking_id": self.booking_id.id,
            "qimam_booking_invoice_kind": invoice.qimam_booking_invoice_kind,
            "qimam_booking_factor": invoice.qimam_booking_factor,
        })
        return result
