# -*- coding: utf-8 -*-
import math
from datetime import date
from odoo import api, models

HIJRI_MONTHS = [
    "محرم","صفر","ربيع الأول","ربيع الآخر","جمادى الأولى","جمادى الآخرة",
    "رجب","شعبان","رمضان","شوال","ذو القعدة","ذو الحجة"
]

def _gregorian_to_jd(y, m, d):
    a=(14-m)//12
    y2=y+4800-a
    m2=m+12*a-3
    return d + (153*m2+2)//5 + 365*y2 + y2//4 - y2//100 + y2//400 - 32045

def _islamic_to_jd(y, m, d):
    return d + math.ceil(29.5*(m-1)) + (y-1)*354 + math.floor((3+11*y)/30) + 1948439 - 1

def _jd_to_islamic(jd):
    y=math.floor((30*(jd-1948439)+10646)/10631)
    m=min(12, math.ceil((jd-(29+_islamic_to_jd(y,1,1)))/29.5)+1)
    m=max(1,m)
    d=jd-_islamic_to_jd(y,m,1)+1
    return int(y),int(m),int(d)

class BookingCalendarService(models.AbstractModel):
    _name="qimam.booking.calendar.service"
    _description="Booking Calendar Presentation Service"

    @api.model
    def hijri_label(self, value):
        if not value:
            return ""
        if isinstance(value, str):
            value=date.fromisoformat(value)
        y,m,d=_jd_to_islamic(_gregorian_to_jd(value.year,value.month,value.day))
        return "%s %s %s هـ"%(d,HIJRI_MONTHS[m-1],y)

    @api.model
    def get_hall_month(self, year, month):
        import calendar
        Booking=self.env["qimam.booking"]
        Hall=self.env["qimam.booking.hall"]
        Period=self.env["qimam.booking.period"]
        days=calendar.monthrange(year,month)[1]
        halls=Hall.search([("branch_id","=",self.env.user.branch_id.id),("active","=",True)])
        periods=Period.search([("branch_id","=",self.env.user.branch_id.id),("active","=",True)])
        total_slots=len(halls)*len(periods)
        start=date(year,month,1); end=date(year,month,days)
        bookings=Booking.search([("branch_id","=",self.env.user.branch_id.id),("booking_date",">=",start),
            ("booking_date","<=",end),("state","in",["hold","confirmed","preparing","event","completed"])])
        result=[]
        for day in range(1,days+1):
            current=date(year,month,day)
            rows=bookings.filtered(lambda b:b.booking_date==current)
            used=sum(len(b.period_line_ids) for b in rows)
            holds=len(rows.filtered(lambda b:b.state=="hold"))
            result.append({
                "date":current.isoformat(),"day":day,"hijri":self.hijri_label(current),
                "bookings":len(rows),"used_slots":used,"free_slots":max(total_slots-used,0),
                "holds":holds,"capacity":total_slots,
            })
        return {"year":year,"month":month,"days":result,"hall_count":len(halls),"period_count":len(periods)}

    @api.model
    def get_stay_timeline(self, start_date, days=14):
        from datetime import timedelta
        if isinstance(start_date,str): start_date=date.fromisoformat(start_date)
        days=max(7,min(int(days),31))
        end_date=start_date+timedelta(days=days)
        Resource=self.env["qimam.booking.resource"]
        Stay=self.env["qimam.stay.booking"]
        resources=Resource.search([("branch_id","=",self.env.user.branch_id.id),("booking_mode","=","stay"),("active","=",True)],order="resource_type_id,sequence,name")
        stays=Stay.search([("branch_id","=",self.env.user.branch_id.id),("state","in",["hold","confirmed","checked_in"]),
            ("checkin_date","<",end_date),("checkout_date",">",start_date)])
        columns=[]
        for i in range(days):
            d=start_date+timedelta(days=i)
            columns.append({"date":d.isoformat(),"day":d.day,"weekday":d.strftime("%a"),"hijri":self.hijri_label(d)})
        rows=[]
        for resource in resources:
            cells=[]
            for i in range(days):
                d=start_date+timedelta(days=i)
                stay=stays.filtered(lambda s:s.resource_id==resource and s.checkin_date<=d<s.checkout_date)[:1]
                cells.append({"date":d.isoformat(),"stay_id":stay.id if stay else False,
                    "state":stay.state if stay else "available","guest":stay.partner_id.name if stay else ""})
            rows.append({"resource_id":resource.id,"name":resource.name,"code":resource.code,
                         "type":resource.resource_type_id.name,"floor":resource.floor or "","cells":cells})
        spans=[]
        for stay in stays:
            visible_start=max(stay.checkin_date,start_date)
            visible_end=min(stay.checkout_date,end_date)
            offset=(visible_start-start_date).days
            length=max((visible_end-visible_start).days,1)
            spans.append({
                "id":stay.id,"resource_id":stay.resource_id.id,"guest":stay.partner_id.name,
                "state":stay.state,"offset":offset,"length":length,
                "checkin":stay.checkin_date.isoformat(),"checkout":stay.checkout_date.isoformat()
            })
        return {"start":start_date.isoformat(),"days":days,"columns":columns,"rows":rows,"spans":spans}
