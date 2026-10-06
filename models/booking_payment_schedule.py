# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BookingPaymentSchedule(models.Model):
    _name = "qimam.booking.payment.schedule"
    _description = "Booking Payment Schedule"
    _order = "due_date, sequence, id"

    sequence = fields.Integer(default=10)
    booking_id = fields.Many2one("qimam.booking", required=True, ondelete="cascade", index=True)
    name = fields.Char(required=True)
    due_date = fields.Date(required=True, index=True)
    amount = fields.Monetary(required=True, currency_field="currency_id")
    currency_id = fields.Many2one(related="booking_id.currency_id", readonly=True)
    company_id = fields.Many2one(related="booking_id.company_id", store=True, index=True)
    state = fields.Selection(
        [("planned", "Planned"), ("due", "Due"), ("paid", "Paid"), ("cancelled", "Cancelled")],
        compute="_compute_state", store=False
    )
    note = fields.Char()

    @api.depends("due_date", "amount", "booking_id.amount_paid", "booking_id.state")
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for line in self:
            if line.booking_id.state == "cancelled":
                line.state = "cancelled"
                continue
            previous = line.booking_id.payment_schedule_ids.filtered(
                lambda x: x.id != line.id and (
                    x.due_date < line.due_date or
                    (x.due_date == line.due_date and (x.sequence, x.id) < (line.sequence, line.id))
                )
            )
            allocated_before = sum(previous.mapped("amount"))
            if line.booking_id.amount_paid >= allocated_before + line.amount - line.currency_id.rounding:
                line.state = "paid"
            elif line.due_date <= today:
                line.state = "due"
            else:
                line.state = "planned"

    @api.constrains("amount")
    def _check_amount(self):
        for line in self:
            if line.amount <= 0:
                raise ValidationError(_("Scheduled payment amount must be greater than zero."))
