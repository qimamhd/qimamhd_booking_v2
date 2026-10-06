# -*- coding: utf-8 -*-
from odoo import fields, models


class BookingService(models.Model):
    _name = "qimam.booking.service"
    _description = "Booking Service"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    price = fields.Monetary(required=True, currency_field="currency_id")
    tax_ids = fields.Many2many(
        "account.tax", domain=[("type_tax_use", "=", "sale")]
    )
    product_id = fields.Many2one(
        "product.product",
        domain=[("sale_ok", "=", True)],
        help="Optional accounting product used on invoice lines.",
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True, store=True
    )
