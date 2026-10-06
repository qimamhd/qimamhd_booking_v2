# -*- coding: utf-8 -*-
from odoo import fields, models


class BookingHall(models.Model):
    _name = "qimam.booking.hall"
    _description = "Booking Hall"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, copy=False)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    capacity = fields.Integer(tracking=True)
    description = fields.Text()
    base_price = fields.Monetary(currency_field="currency_id", tracking=True)
    tax_ids = fields.Many2many(
        "account.tax",
        string="Default Taxes",
        domain=[("type_tax_use", "=", "sale")],
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True, store=True
    )

    _sql_constraints = [
        ("hall_code_company_uniq", "unique(code, company_id)", "Hall code must be unique per company."),
        ("hall_capacity_positive", "CHECK(capacity >= 0)", "Capacity cannot be negative."),
    ]
