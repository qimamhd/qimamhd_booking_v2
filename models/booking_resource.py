# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class BookingResourceType(models.Model):
    _name = "qimam.booking.resource.type"
    _description = "Bookable Resource Type"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    booking_mode = fields.Selection(
        [("event", "Event / periods"), ("stay", "Stay / nights")],
        required=True, default="event",
        help="Event resources use day + period. Stay resources use check-in/check-out."
    )
    icon = fields.Selection(
        [("hall","Hall"),("room","Room"),("apartment","Apartment"),("chalet","Chalet"),("other","Other")],
        default="other", required=True
    )
    company_id = fields.Many2one("res.company", required=True, default=lambda self:self.env.company, index=True)
    _sql_constraints=[("resource_type_code_company_uniq","unique(code, company_id)","Resource type code must be unique per company.")]

class BookingResource(models.Model):
    _name = "qimam.booking.resource"
    _description = "Bookable Resource"
    _order = "resource_type_id, sequence, name"

    name=fields.Char(required=True, translate=True)
    code=fields.Char(required=True, index=True)
    sequence=fields.Integer(default=10)
    active=fields.Boolean(default=True)
    resource_type_id=fields.Many2one("qimam.booking.resource.type",required=True,ondelete="restrict",index=True)
    booking_mode=fields.Selection(related="resource_type_id.booking_mode",store=True,readonly=True,index=True)
    capacity=fields.Integer()
    floor=fields.Char()
    base_price=fields.Monetary(currency_field="currency_id")
    tax_ids=fields.Many2many("account.tax","qimam_resource_tax_rel","resource_id","tax_id",
        string="Sales Taxes",domain=[("type_tax_use","=","sale")])
    company_id=fields.Many2one("res.company",required=True,default=lambda self:self.env.company,index=True)
    currency_id=fields.Many2one(related="company_id.currency_id",readonly=True)
    note=fields.Text()
    _sql_constraints=[("resource_code_company_uniq","unique(code, company_id)","Resource code must be unique per company.")]

    @api.constrains("capacity","base_price")
    def _check_nonnegative(self):
        for rec in self:
            if rec.capacity < 0 or rec.base_price < 0:
                raise ValidationError(_("Capacity and base price cannot be negative."))
