# -*- coding: utf-8 -*-
from odoo import fields, models

class ResCompany(models.Model):
    _inherit="res.company"
    qimam_booking_business_mode=fields.Selection(
        [("events","Halls & Events"),("hotel","Hotel & Stays"),("mixed","Mixed")],
        string="Booking Business Mode",default="events",required=True)

class ResConfigSettings(models.TransientModel):
    _inherit="res.config.settings"
    qimam_booking_business_mode=fields.Selection(related="company_id.qimam_booking_business_mode",readonly=False)
