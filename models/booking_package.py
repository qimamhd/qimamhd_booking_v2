# -*- coding: utf-8 -*-
from odoo import fields, models


class BookingPackage(models.Model):
    _name = "qimam.booking.package"
    _description = "Booking Package"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    description = fields.Text()
    line_ids = fields.One2many("qimam.booking.package.line", "package_id")
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )


class BookingPackageLine(models.Model):
    _name = "qimam.booking.package.line"
    _description = "Booking Package Line"

    package_id = fields.Many2one(
        "qimam.booking.package", required=True, ondelete="cascade"
    )
    service_id = fields.Many2one("qimam.booking.service", required=True)
    quantity = fields.Float(default=1.0, required=True)
    branch_id = fields.Many2one(related="package_id.branch_id", store=True, index=True)
