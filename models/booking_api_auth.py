# -*- coding: utf-8 -*-
import hashlib, secrets
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import AccessError

ACCESS_MINUTES=30
REFRESH_DAYS=30

def _hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

class BookingApiSession(models.Model):
    _name="qimam.booking.api.session"
    _description="Booking API Session"
    _order="last_seen_at desc,id desc"
    _log_access=True

    user_id=fields.Many2one("res.users",required=True,index=True,ondelete="cascade")
    access_hash=fields.Char(required=True,index=True,copy=False)
    refresh_hash=fields.Char(required=True,index=True,copy=False)
    access_expires_at=fields.Datetime(required=True,index=True)
    refresh_expires_at=fields.Datetime(required=True,index=True)
    device_id=fields.Char(index=True)
    device_name=fields.Char()
    last_seen_at=fields.Datetime()
    revoked_at=fields.Datetime(index=True)
    active=fields.Boolean(compute="_compute_active")
    branch_id=fields.Many2one("custom.branches",related="user_id.branch_id",readonly=True)

    @api.depends("revoked_at","refresh_expires_at")
    def _compute_active(self):
        now=fields.Datetime.now()
        for rec in self: rec.active=not rec.revoked_at and rec.refresh_expires_at>now

    @api.model
    def issue(self,user,device_id=None,device_name=None):
        now=fields.Datetime.now()
        access=secrets.token_urlsafe(48);refresh=secrets.token_urlsafe(64)
        rec=self.sudo().create({
            "user_id":user.id,"access_hash":_hash(access),"refresh_hash":_hash(refresh),
            "access_expires_at":now+timedelta(minutes=ACCESS_MINUTES),
            "refresh_expires_at":now+timedelta(days=REFRESH_DAYS),
            "device_id":device_id or False,"device_name":device_name or False,"last_seen_at":now,
        })
        return rec,access,refresh

    @api.model
    def authenticate(self,token,device_id=None):
        if not token: raise AccessError(_("Missing access token."))
        now=fields.Datetime.now()
        rec=self.sudo().search([("access_hash","=",_hash(token)),("revoked_at","=",False)],limit=1)
        if not rec or rec.access_expires_at<=now: raise AccessError(_("Access token is invalid or expired."))
        if rec.device_id and rec.device_id!=(device_id or ""): raise AccessError(_("This session is bound to another device."))
        if not rec.user_id.active: raise AccessError(_("User is inactive."))
        rec.sudo().write({"last_seen_at":now})
        return rec

    @api.model
    def rotate(self,refresh_token,device_id=None):
        now=fields.Datetime.now()
        rec=self.sudo().search([("refresh_hash","=",_hash(refresh_token or "")),("revoked_at","=",False)],limit=1)
        if not rec or rec.refresh_expires_at<=now: raise AccessError(_("Refresh token is invalid or expired."))
        if rec.device_id and rec.device_id!=(device_id or ""): raise AccessError(_("This session is bound to another device."))
        user=rec.user_id
        # One-time refresh semantics: old pair is revoked before new pair is issued.
        rec.sudo().write({"revoked_at":now})
        return self.issue(user,rec.device_id,rec.device_name)

    def revoke(self):
        self.sudo().write({"revoked_at":fields.Datetime.now()})
        return True

    @api.model
    def cron_purge_expired(self):
        cutoff=fields.Datetime.now()-timedelta(days=7)
        self.sudo().search(["|",("refresh_expires_at","<",cutoff),("revoked_at","<",cutoff)]).unlink()
        return True
