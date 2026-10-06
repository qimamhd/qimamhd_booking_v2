# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError

def _default_branch(self):
    return self.env.user.branch_id

class BookingBranchMixin(models.AbstractModel):
    _name="qimam.booking.branch.mixin"
    _description="Qimam Booking Branch Scope"

    branch_id=fields.Many2one(
        "custom.branches", string="Branch", required=True, index=True,
        default=_default_branch
    )

    @api.constrains("branch_id")
    def _check_allowed_branch(self):
        allowed=self.env.user.allowed_branch_ids
        for rec in self:
            if rec.branch_id and rec.branch_id not in allowed and not self.env.su:
                raise AccessError(_("You are not allowed to operate on branch %s.") % rec.branch_id.display_name)

class Booking(models.Model):
    _inherit=["qimam.booking","qimam.booking.branch.mixin"]
    _name="qimam.booking"

class BookingHall(models.Model):
    _inherit=["qimam.booking.hall","qimam.booking.branch.mixin"]
    _name="qimam.booking.hall"

class BookingPeriod(models.Model):
    _inherit=["qimam.booking.period","qimam.booking.branch.mixin"]
    _name="qimam.booking.period"

class BookingService(models.Model):
    _inherit=["qimam.booking.service","qimam.booking.branch.mixin"]
    _name="qimam.booking.service"

class BookingPackage(models.Model):
    _inherit=["qimam.booking.package","qimam.booking.branch.mixin"]
    _name="qimam.booking.package"

class BookingResourceType(models.Model):
    _inherit=["qimam.booking.resource.type","qimam.booking.branch.mixin"]
    _name="qimam.booking.resource.type"

class BookingResource(models.Model):
    _inherit=["qimam.booking.resource","qimam.booking.branch.mixin"]
    _name="qimam.booking.resource"

class StayBooking(models.Model):
    _inherit=["qimam.stay.booking","qimam.booking.branch.mixin"]
    _name="qimam.stay.booking"

class BookingPaymentSchedule(models.Model):
    _inherit=["qimam.booking.payment.schedule","qimam.booking.branch.mixin"]
    _name="qimam.booking.payment.schedule"

    @api.model
    def create(self,vals):
        if vals.get("booking_id") and not vals.get("branch_id"):
            vals["branch_id"]=self.env["qimam.booking"].browse(vals["booking_id"]).branch_id.id
        return super().create(vals)

class BookingOperationTemplate(models.Model):
    _inherit=["qimam.booking.operation.template","qimam.booking.branch.mixin"]
    _name="qimam.booking.operation.template"

class BookingOperationItem(models.Model):
    _inherit=["qimam.booking.operation.item","qimam.booking.branch.mixin"]
    _name="qimam.booking.operation.item"

    @api.model
    def create(self,vals):
        if vals.get("booking_id") and not vals.get("branch_id"):
            vals["branch_id"]=self.env["qimam.booking"].browse(vals["booking_id"]).branch_id.id
        return super().create(vals)
