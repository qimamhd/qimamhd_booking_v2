# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BookingInvoiceWizard(models.TransientModel):
    _name = "qimam.booking.invoice.wizard"
    _description = "Booking Invoice Wizard"

    booking_id = fields.Many2one("qimam.booking", required=True, readonly=True)
    invoice_type = fields.Selection(
        [
            ("full", "Full contract"),
            ("deposit", "Deposit"),
            ("final", "Remaining / Final"),
        ],
        required=True,
        default="full",
    )
    deposit_percent = fields.Float(default=30.0)
    already_invoiced_percent = fields.Float(
        compute="_compute_progress", readonly=True
    )
    invoice_percent = fields.Float(compute="_compute_progress", readonly=True)
    preview_amount = fields.Monetary(
        compute="_compute_progress", currency_field="currency_id"
    )
    currency_id = fields.Many2one(related="booking_id.currency_id", readonly=True)

    @api.depends("booking_id", "invoice_type", "deposit_percent")
    def _compute_progress(self):
        for rec in self:
            existing = rec.booking_id._reserved_invoice_factor() * 100.0 if rec.booking_id else 0.0
            remaining = max(100.0 - existing, 0.0)
            if rec.invoice_type == "full":
                percent = remaining
            elif rec.invoice_type == "deposit":
                percent = min(max(rec.deposit_percent, 0.0), remaining)
            else:
                percent = remaining
            rec.already_invoiced_percent = existing
            rec.invoice_percent = percent
            rec.preview_amount = (rec.booking_id.amount_total or 0.0) * percent / 100.0

    @api.constrains("deposit_percent")
    def _check_deposit_percent(self):
        for rec in self:
            if rec.invoice_type == "deposit" and not (0 < rec.deposit_percent <= 100):
                raise ValidationError(_("Deposit percentage must be greater than 0 and at most 100."))

    def action_create_invoice(self):
        self.ensure_one()
        booking = self.booking_id
        if booking.state not in ("draft", "hold", "confirmed", "preparing", "event", "completed"):
            raise UserError(_("This booking cannot be invoiced in its current state."))

        booking._lock_financial_capacity()
        remaining = max(1.0 - booking._reserved_invoice_factor(), 0.0)
        if remaining <= 0.000001:
            raise UserError(_("The contract is already fully invoiced."))

        if self.invoice_type == "deposit":
            factor = min(self.deposit_percent / 100.0, remaining)
            kind = "deposit"
        elif self.invoice_type == "final":
            factor = remaining
            kind = "final"
        else:
            factor = remaining
            kind = "full" if remaining >= 0.999999 else "final"

        lines = booking._prepare_contract_invoice_lines(factor=factor)
        if not lines:
            raise UserError(_("There is nothing to invoice."))

        move = self.env["account.move"].create({
            "type": "out_invoice",
            "partner_id": booking.partner_id.id,
            "invoice_origin": booking.name,
            "qimam_booking_id": booking.id,
            "qimam_booking_invoice_kind": kind,
            "qimam_booking_factor": factor,
            "invoice_line_ids": lines,
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Customer Invoice"),
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": move.id,
            "target": "current",
        }
