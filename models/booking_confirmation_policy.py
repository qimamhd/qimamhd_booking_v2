# -*- coding: utf-8 -*-
from odoo import fields, models

class ResCompany(models.Model):
    _inherit="res.company"
    qimam_booking_confirmation_policy=fields.Selection([
        ("manual","Manual approval"),
        ("invoice","Posted invoice required"),
        ("deposit","Deposit payment required"),
    ], default="manual", required=True, string="Booking Confirmation Policy")
    qimam_booking_default_deposit_percent=fields.Float(default=30.0, string="Default Booking Deposit %")

class ResConfigSettings(models.TransientModel):
    _inherit="res.config.settings"
    qimam_booking_confirmation_policy=fields.Selection(related="company_id.qimam_booking_confirmation_policy",readonly=False)
    qimam_booking_default_deposit_percent=fields.Float(related="company_id.qimam_booking_default_deposit_percent",readonly=False)
