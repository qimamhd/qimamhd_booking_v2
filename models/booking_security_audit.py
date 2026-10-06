# -*- coding: utf-8 -*-
import json
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

SENSITIVE_BOOKING_FIELDS={
    "booking_date","hall_id","period_line_ids","discount_type","discount_value",
    "hall_price_unit","hall_tax_ids","state","company_id"
}
SENSITIVE_STAY_FIELDS={"resource_id","checkin_date","checkout_date","price_per_night","state","company_id"}

class BookingSecurityAudit(models.Model):
    _name="qimam.booking.security.audit"
    _description="Booking Sensitive Action Audit"
    _order="create_date desc,id desc"
    _log_access=True
    model_name=fields.Char(required=True,index=True,readonly=True)
    res_id=fields.Integer(required=True,index=True,readonly=True)
    record_name=fields.Char(readonly=True)
    action=fields.Selection([
        ("create","Create"),("sensitive_write","Sensitive Change"),("state","State Change"),
        ("cancel","Cancellation"),("reopen","Reopen"),("financial","Financial Action")
    ],required=True,index=True,readonly=True)
    user_id=fields.Many2one("res.users",required=True,default=lambda self:self.env.user,readonly=True,index=True)
    company_id=fields.Many2one("res.company",required=True,readonly=True,index=True)
    changed_fields=fields.Char(readonly=True)
    old_values=fields.Text(readonly=True)
    new_values=fields.Text(readonly=True)
    reason=fields.Char(readonly=True)
    happened_at=fields.Datetime(default=fields.Datetime.now,required=True,readonly=True,index=True)

    @api.model
    def log(self,record,action,changed_fields=None,old=None,new=None,reason=None):
        def safe(value):
            if isinstance(value,models.BaseModel):
                return value.ids
            if hasattr(value,"isoformat"):
                return value.isoformat()
            return value
        payload=lambda d: json.dumps({k:safe(v) for k,v in (d or {}).items()},ensure_ascii=False,default=str)
        return self.sudo().create({
            "model_name":record._name,"res_id":record.id,"record_name":record.display_name,
            "action":action,"user_id":self.env.user.id,"company_id":record.company_id.id,
            "changed_fields":",".join(sorted(changed_fields or [])),
            "old_values":payload(old),"new_values":payload(new),"reason":reason or False,
        })

class Booking(models.Model):
    _inherit="qimam.booking"

    def _audit_snapshot(self,names):
        self.ensure_one()
        result={}
        for name in names:
            field=self._fields.get(name)
            if not field: continue
            value=self[name]
            result[name]=value.ids if field.type in ("many2many","one2many") else (value.id if field.type=="many2one" else value)
        return result

    def write(self,vals):
        sensitive=set(vals)&SENSITIVE_BOOKING_FIELDS
        before={r.id:r._audit_snapshot(sensitive) for r in self} if sensitive else {}
        # Company may never be silently switched once accounting exists.
        if "company_id" in vals:
            for r in self:
                if r.invoice_ids:
                    raise UserError(_("The company cannot be changed after accounting documents exist."))
        result=super().write(vals)
        if sensitive and not self.env.context.get("qimam_skip_security_audit"):
            for r in self:
                action="state" if sensitive=={"state"} else "sensitive_write"
                self.env["qimam.booking.security.audit"].log(r,action,sensitive,before.get(r.id),r._audit_snapshot(sensitive))
        return result

class StayBooking(models.Model):
    _inherit="qimam.stay.booking"

    def _audit_snapshot(self,names):
        self.ensure_one();result={}
        for name in names:
            field=self._fields.get(name)
            if not field:continue
            value=self[name]
            result[name]=value.id if field.type=="many2one" else value
        return result

    def write(self,vals):
        sensitive=set(vals)&SENSITIVE_STAY_FIELDS
        before={r.id:r._audit_snapshot(sensitive) for r in self} if sensitive else {}
        result=super().write(vals)
        if sensitive and not self.env.context.get("qimam_skip_security_audit"):
            for r in self:
                self.env["qimam.booking.security.audit"].log(r,"state" if sensitive=={"state"} else "sensitive_write",
                    sensitive,before.get(r.id),r._audit_snapshot(sensitive))
        return result
