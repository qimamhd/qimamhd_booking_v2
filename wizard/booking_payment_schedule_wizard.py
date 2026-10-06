# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BookingPaymentScheduleWizard(models.TransientModel):
    _name = "qimam.booking.payment.schedule.wizard"
    _description = "Build Booking Payment Schedule"

    booking_id = fields.Many2one("qimam.booking", required=True, readonly=True)
    schedule_type = fields.Selection(
        [("deposit_balance", "Deposit + balance"), ("equal", "Equal installments")],
        required=True, default="deposit_balance"
    )
    deposit_percent = fields.Float(default=30.0)
    installment_count = fields.Integer(default=3)
    first_due_date = fields.Date(default=fields.Date.today, required=True)
    interval_months = fields.Integer(default=1, required=True)
    preview_total = fields.Monetary(related="booking_id.amount_total", readonly=True)
    currency_id = fields.Many2one(related="booking_id.currency_id", readonly=True)

    @api.constrains("deposit_percent", "installment_count", "interval_months")
    def _check_values(self):
        for rec in self:
            if rec.schedule_type == "deposit_balance" and not (0 < rec.deposit_percent < 100):
                raise ValidationError(_("Deposit percentage must be between 0 and 100."))
            if rec.schedule_type == "equal" and rec.installment_count < 2:
                raise ValidationError(_("Use at least two installments."))
            if rec.interval_months < 1:
                raise ValidationError(_("Installment interval must be at least one month."))

    def action_generate(self):
        self.ensure_one()
        booking = self.booking_id
        booking.payment_schedule_ids.unlink()
        total = booking.amount_total
        vals = []
        if self.schedule_type == "deposit_balance":
            deposit = booking.currency_id.round(total * self.deposit_percent / 100.0)
            vals = [
                {"name": _("Deposit"), "due_date": self.first_due_date, "amount": deposit, "sequence": 10},
                {"name": _("Final balance"), "due_date": booking.booking_date,
                 "amount": booking.currency_id.round(total - deposit), "sequence": 20},
            ]
        else:
            each = booking.currency_id.round(total / self.installment_count)
            allocated = 0.0
            for i in range(self.installment_count):
                amount = each if i < self.installment_count - 1 else booking.currency_id.round(total - allocated)
                vals.append({
                    "name": _("Installment %s") % (i + 1),
                    "due_date": self.first_due_date + relativedelta(months=i * self.interval_months),
                    "amount": amount,
                    "sequence": (i + 1) * 10,
                })
                allocated += amount
        for vals_line in vals:
            vals_line["booking_id"] = booking.id
            self.env["qimam.booking.payment.schedule"].create(vals_line)
        return booking.action_view_payment_schedule()
