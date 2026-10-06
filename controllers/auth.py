# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied, AccessError
from .api import ok,fail,API_VERSION

def _device(payload):
    return (payload.get("device_id") or "").strip()[:128],(payload.get("device_name") or "").strip()[:128]

class BookingApiAuth(http.Controller):
    @http.route("/api/v2/auth/login",type="json",auth="none",methods=["POST"],csrf=False)
    def login(self,**payload):
        try:
            db=request.session.db or payload.get("db")
            login=(payload.get("login") or "").strip();password=payload.get("password") or ""
            if not db or not login or not password:return fail("INVALID_CREDENTIALS","Database, login and password are required.")
            uid=request.session.authenticate(db,login,password)
            if not uid:return fail("INVALID_CREDENTIALS","Invalid credentials.")
            env=request.env(user=uid)
            user=env["res.users"].browse(uid)
            if not user.has_group("qimamhd_booking_v2.group_booking_user"):
                request.session.logout(keep_db=True);return fail("ACCESS_DENIED","User is not allowed to use Booking API.")
            device_id,device_name=_device(payload)
            rec,access,refresh=env["qimam.booking.api.session"].issue(user,device_id,device_name)
            # Token API must not depend on the newly-created web session.
            request.session.logout(keep_db=True)
            return ok({"access_token":access,"refresh_token":refresh,"token_type":"Bearer",
                       "expires_in":1800,"refresh_expires_in":2592000})
        except AccessDenied:return fail("INVALID_CREDENTIALS","Invalid credentials.")
        except Exception:return fail("AUTHENTICATION_FAILED","Authentication failed.")

    @http.route("/api/v2/auth/refresh",type="json",auth="none",methods=["POST"],csrf=False)
    def refresh(self,**payload):
        try:
            db=request.session.db or payload.get("db")
            if not db:return fail("INVALID_PAYLOAD","Database is required.")
            # auth=none has no user env; registry env is available after db selection in normal Odoo JSON flow.
            device_id,_=_device(payload)
            rec,access,refresh=request.env["qimam.booking.api.session"].sudo().rotate(payload.get("refresh_token"),device_id)
            return ok({"access_token":access,"refresh_token":refresh,"token_type":"Bearer",
                       "expires_in":1800,"refresh_expires_in":2592000})
        except AccessError as exc:return fail("INVALID_REFRESH_TOKEN",str(exc))
        except Exception:return fail("AUTHENTICATION_FAILED","Refresh failed.")
