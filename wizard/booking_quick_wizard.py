# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import ValidationError


class BookingQuickWizard(models.TransientModel):
    _name = "qimam.booking.quick.wizard"
    _description = "Quick Booking Wizard"

    partner_id = fields.Many2one("res.partner", required=True)
    booking_date = fields.Date(required=True, default=fields.Date.today)
    hall_id = fields.Many2one("qimam.booking.hall", required=True)
    period_ids = fields.Many2many("qimam.booking.period", required=True)
    guest_count = fields.Integer()
    note = fields.Text()

    def action_create_booking(self):
        self.ensure_one()
        if not self.period_ids:
            raise ValidationError(_("Select at least one period."))
        booking = self.env["qimam.booking"].create({
            "partner_id": self.partner_id.id,
            "booking_date": self.booking_date,
            "hall_id": self.hall_id.id,
            "guest_count": self.guest_count,
            "note": self.note,
            "period_line_ids": [(0, 0, {"period_id": p.id}) for p in self.period_ids],
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Booking"),
            "res_model": "qimam.booking",
            "view_mode": "form",
            "res_id": booking.id,
            "target": "current",
        }
