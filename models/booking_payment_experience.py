# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class BookingPaymentExperience(models.AbstractModel):
    _name="qimam.booking.payment.experience"
    _description="Booking Payment and Confirmation Experience"

    @api.model
    def snapshot(self, booking_id):
        b=self.env["qimam.booking"].browse(int(booking_id)).exists()
        if not b or b.branch_id not in self.env.user.allowed_branch_ids:
            raise UserError(_("Invalid booking."))
        policy=b.company_id.qimam_booking_confirmation_policy or "manual"
        deposit_pct=max(min(b.company_id.qimam_booking_default_deposit_percent or 0.0,100.0),0.0)
        deposit_required=b.currency_id.round(b.amount_total*deposit_pct/100.0) if policy=="deposit" else 0.0
        schedule=[]
        paid_left=b.amount_paid
        for line in b.payment_schedule_ids.sorted(key=lambda x:(x.due_date,x.sequence,x.id)):
            allocated=min(max(paid_left,0.0),line.amount); paid_left-=allocated
            schedule.append({"id":line.id,"name":line.name,"date":line.due_date.isoformat(),
                "amount":line.amount,"paid":allocated,"open":max(line.amount-allocated,0.0),"state":line.state})
        if policy=="manual":
            ready=True; gate=_("Ready for manual confirmation")
        elif policy=="invoice":
            ready=bool(b.invoice_ids.filtered(lambda m:m.type=="out_invoice" and m.state=="posted"))
            gate=_("Posted invoice found") if ready else _("Post a customer invoice to confirm")
        else:
            ready=b.amount_paid+b.currency_id.rounding>=deposit_required
            gate=_("Deposit requirement met") if ready else _("Deposit payment is still required")
        return {
            "id":b.id,"name":b.name,"state":b.state,"customer":b.partner_id.name,
            "currency":b.currency_id.symbol or b.currency_id.name,
            "total":b.amount_total,"paid":b.amount_paid,"due":b.amount_due,
            "invoice_progress":b.invoice_progress,"financial_status":b.financial_status,
            "policy":policy,"deposit_percent":deposit_pct,"deposit_required":deposit_required,
            "ready":ready,"gate":gate,"next_due":b.next_due_date.isoformat() if b.next_due_date else "",
            "overdue":b.overdue_amount,"schedule":schedule,
        }

    @api.model
    def build_schedule(self, booking_id, mode="deposit_balance", deposit_percent=30.0, count=3, first_due_date=None, interval_months=1):
        b=self.env["qimam.booking"].browse(int(booking_id)).exists()
        if not b or b.branch_id not in self.env.user.allowed_branch_ids:
            raise UserError(_("Invalid booking."))
        if b.state not in ("draft","hold","confirmed"):
            raise UserError(_("Payment schedule cannot be rebuilt in the current booking state."))
        first=fields.Date.from_string(first_due_date) if first_due_date else fields.Date.context_today(self)
        count=max(int(count or 0),2); interval=max(int(interval_months or 0),1)
        pct=max(min(float(deposit_percent or 0),99.0),1.0)
        b.payment_schedule_ids.unlink()
        total=b.amount_total; vals=[]
        if mode=="deposit_balance":
            deposit=b.currency_id.round(total*pct/100.0)
            vals=[
                {"name":_("Deposit"),"due_date":first,"amount":deposit,"sequence":10},
                {"name":_("Final balance"),"due_date":b.booking_date,"amount":b.currency_id.round(total-deposit),"sequence":20},
            ]
        elif mode=="equal":
            each=b.currency_id.round(total/count); allocated=0.0
            for i in range(count):
                amount=each if i<count-1 else b.currency_id.round(total-allocated)
                vals.append({"name":_("Installment %s")%(i+1),"due_date":first+relativedelta(months=i*interval),"amount":amount,"sequence":(i+1)*10})
                allocated+=amount
        else:
            raise UserError(_("Unknown payment schedule mode."))
        for v in vals:
            v["booking_id"]=b.id
            self.env["qimam.booking.payment.schedule"].create(v)
        return self.snapshot(b.id)

    @api.model
    def confirm(self, booking_id):
        b=self.env["qimam.booking"].browse(int(booking_id)).exists()
        if not b or b.branch_id not in self.env.user.allowed_branch_ids:
            raise UserError(_("Invalid booking."))
        b.action_confirm()
        return self.snapshot(b.id)
