# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    qimam_booking_id = fields.Many2one(
        "qimam.booking",
        string="Booking",
        copy=False,
        index=True,
        ondelete="restrict",
    )
    qimam_booking_invoice_kind = fields.Selection(
        [
            ("full", "Full"),
            ("deposit", "Deposit"),
            ("final", "Final"),
            ("schedule", "Schedule"),
        ],
        string="Booking Invoice Type",
        copy=False,
        index=True,
    )
    qimam_booking_factor = fields.Float(
        string="Booking Invoice Factor",
        copy=False,
        help="Contract proportion represented by this invoice. 1.0 = 100%.",
    )
    qimam_stay_id = fields.Many2one(
        "qimam.stay.booking",
        string="Hotel Stay",
        copy=False,
        index=True,
        ondelete="restrict",
    )

