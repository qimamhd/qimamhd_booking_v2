# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    booking_invoice_policy = fields.Selection(
        [
            ("manual", "Manual"),
            ("on_confirm", "Full invoice on confirmation"),
            ("deposit", "Deposit invoice then final invoice"),
            ("schedule", "Invoices by payment schedule"),
        ],
        string="Booking Invoice Policy",
        default="manual",
        config_parameter="qimamhd_booking_v2.invoice_policy",
    )
    booking_hold_hours = fields.Integer(
        string="Default Hold Hours",
        default=24,
        config_parameter="qimamhd_booking_v2.hold_hours",
    )
    booking_require_payment_before_confirm = fields.Boolean(
        string="Require payment before confirmation",
        config_parameter="qimamhd_booking_v2.require_payment_before_confirm",
    )
