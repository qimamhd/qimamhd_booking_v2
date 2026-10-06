# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class BookingPeriod(models.Model):
    _name = "qimam.booking.period"
    _description = "Booking Period"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, copy=False)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    time_from = fields.Float(string="Default Start Time", help="Optional operational time only.")
    time_to = fields.Float(string="Default End Time", help="Optional operational time only.")
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )

    _sql_constraints = [
        ("period_code_company_uniq", "unique(code, company_id)", "Period code must be unique per company."),
    ]

    @api.constrains("time_from", "time_to")
    def _check_times(self):
        for rec in self:
            if not (0 <= rec.time_from <= 24 and 0 <= rec.time_to <= 24):
                raise ValidationError(_("Period times must be between 0 and 24."))
