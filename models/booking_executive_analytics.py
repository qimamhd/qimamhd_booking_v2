# -*- coding: utf-8 -*-
from datetime import timedelta
from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class BookingExecutiveAnalytics(models.AbstractModel):
    _name="qimam.booking.executive.analytics"
    _description="Booking Executive Intelligence"

    @api.model
    def _dates(self, start_date=None, end_date=None):
        today=fields.Date.context_today(self)
        end=fields.Date.from_string(end_date) if end_date else today
        start=fields.Date.from_string(start_date) if start_date else end-timedelta(days=29)
        if end < start: raise UserError(_("End date must be after start date."))
        if (end-start).days > 366: raise UserError(_("Executive comparison is limited to 367 days per view."))
        return start,end

    @api.model
    def dashboard(self, start_date=None, end_date=None):
        company=self.env.company
        branch=self.env.user.branch_id
        start,end=self._dates(start_date,end_date)
        span=(end-start).days+1
        p_end=start-timedelta(days=1); p_start=p_end-timedelta(days=span-1)
        current=self._period(company,branch,start,end)
        previous=self._period(company,branch,p_start,p_end)
        current["comparison"]={
            "bookings":self._delta(current["bookings"],previous["bookings"]),
            "revenue":self._delta(current["revenue"],previous["revenue"]),
            "cancel_rate":self._delta(current["cancel_rate"],previous["cancel_rate"]),
            "occupancy":self._delta(current["occupancy"],previous["occupancy"]),
        }
        current.update({
            "start":start.isoformat(),"end":end.isoformat(),
            "previous_start":p_start.isoformat(),"previous_end":p_end.isoformat(),
            "currency":company.currency_id.symbol or company.currency_id.name,
            "forecast":self._forecast(company,branch,fields.Date.context_today(self)),
            "branch":{"id":branch.id,"name":branch.name},
            "business_mode":company.qimam_booking_business_mode or "events",
        })
        return current

    def _delta(self,current,previous):
        if not previous: return None if not current else 100.0
        return round((current-previous)/abs(previous)*100.0,1)

    def _period(self,company,branch,start,end):
        Booking=self.env["qimam.booking"]
        domain=[("branch_id","=",branch.id),("booking_date",">=",start),("booking_date","<=",end)]
        records=Booking.search(domain)
        active=records.filtered(lambda b:b.state!="cancelled")
        cancelled=records.filtered(lambda b:b.state=="cancelled")
        revenue=sum(active.filtered(lambda b:b.state in ("confirmed","preparing","event","completed")).mapped("amount_total"))
        cancel_rate=round(len(cancelled)/len(records)*100.0,1) if records else 0.0
        holds=len(records.filtered(lambda b:b.state=="hold"))
        confirmed=len(records.filtered(lambda b:b.state in ("confirmed","preparing","event","completed")))
        conversion=round(confirmed/(confirmed+holds)*100.0,1) if confirmed+holds else 0.0
        # Occupancy is sold hall-period slots / configured hall-period capacity across the selected days.
        halls=self.env["qimam.booking.hall"].search([("branch_id","=",branch.id),("active","=",True)])
        periods=self.env["qimam.booking.period"].search([("branch_id","=",branch.id),("active","=",True)])
        capacity=len(halls)*len(periods)*((end-start).days+1)
        occupied=sum(len(b.period_line_ids) for b in active.filtered(lambda x:x.state in ("hold","confirmed","preparing","event","completed")))
        occupancy=round(occupied/capacity*100.0,1) if capacity else 0.0
        hall_data=defaultdict(lambda:{"bookings":0,"revenue":0.0})
        service_data=defaultdict(lambda:{"qty":0.0,"revenue":0.0})
        for b in active:
            hall_data[b.hall_id.name]["bookings"]+=1
            if b.state in ("confirmed","preparing","event","completed"):
                hall_data[b.hall_id.name]["revenue"]+=b.amount_total
            for line in b.service_line_ids:
                d=service_data[line.service_id.name]; d["qty"]+=line.quantity; d["revenue"]+=line.price_unit*line.quantity
        top_halls=sorted([{"name":k,**v} for k,v in hall_data.items()],key=lambda x:(x["revenue"],x["bookings"]),reverse=True)[:5]
        top_services=sorted([{"name":k,**v} for k,v in service_data.items()],key=lambda x:(x["revenue"],x["qty"]),reverse=True)[:5]
        overdue=sum(active.mapped("overdue_amount"))
        return {"bookings":len(records),"active_bookings":len(active),"cancelled":len(cancelled),
                "revenue":revenue,"cancel_rate":cancel_rate,"holds":holds,"confirmed":confirmed,
                "conversion":conversion,"occupancy":occupancy,"overdue":overdue,
                "top_halls":top_halls,"top_services":top_services}

    def _forecast(self,company,branch,today):
        result=[]
        for days in (30,60,90):
            end=today+timedelta(days=days-1)
            recs=self.env["qimam.booking"].search([
                ("branch_id","=",branch.id),("booking_date",">=",today),("booking_date","<=",end),
                ("state","in",["confirmed","preparing","event"])
            ])
            result.append({"days":days,"bookings":len(recs),"value":sum(recs.mapped("amount_total"))})
        return result

    @api.model
    def drilldown(self, metric, start_date=None, end_date=None):
        start,end=self._dates(start_date,end_date)
        domain=[("branch_id","=",self.env.user.branch_id.id),("booking_date",">=",start),("booking_date","<=",end)]
        if metric=="cancelled": domain.append(("state","=","cancelled"))
        elif metric=="holds": domain.append(("state","=","hold"))
        elif metric=="revenue": domain.append(("state","in",["confirmed","preparing","event","completed"]))
        elif metric=="overdue": domain.append(("state","!=","cancelled"))
        elif metric!="bookings": raise UserError(_("Unsupported drill-down metric."))
        return {"type":"ir.actions.act_window","name":_("Bookings"),"res_model":"qimam.booking",
                "view_mode":"tree,form","domain":domain,"context":{}}
