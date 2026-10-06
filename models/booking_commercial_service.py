# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import UserError

class BookingCommercialService(models.AbstractModel):
    _name="qimam.booking.commercial.service"
    _description="Booking Commercial Pricing Service"

    @api.model
    def catalog(self):
        company=self.env.company
        branch=self.env.user.branch_id
        services=self.env["qimam.booking.service"].search([("branch_id","=",branch.id),("active","=",True)],order="name")
        packages=self.env["qimam.booking.package"].search([("branch_id","=",branch.id),("active","=",True)],order="name")
        return {
            "services":[{"id":s.id,"name":s.name,"price":s.price,
                "currency":s.currency_id.symbol or s.currency_id.name} for s in services],
            "packages":[{"id":pkg.id,"name":pkg.name,"description":pkg.description or "",
                "lines":[{"service_id":line.service_id.id,"name":line.service_id.name,"quantity":line.quantity}
                         for line in pkg.line_ids]} for pkg in packages],
        }

    @api.model
    def quote_event(self, hall_id, partner_id, service_items=None, discount_type="none", discount_value=0.0):
        hall=self.env["qimam.booking.hall"].browse(int(hall_id or 0)).exists()
        partner=self.env["res.partner"].browse(int(partner_id or 0)).exists()
        if not hall or hall.branch_id != self.env.user.branch_id:
            raise UserError(_("Invalid hall."))
        service_items=service_items or []
        lines=[]
        raw=hall.base_price or 0.0
        for item in service_items:
            service=self.env["qimam.booking.service"].browse(int(item.get("id") or 0)).exists()
            qty=max(float(item.get("qty") or 0.0),0.0)
            if not service or service.branch_id != self.env.user.branch_id or qty <= 0:
                continue
            raw += service.price*qty
            lines.append((service,qty))
        dtype=discount_type if discount_type in ("none","amount","percent") else "none"
        dval=max(float(discount_value or 0.0),0.0)
        if dtype=="percent":
            pct=min(dval,100.0)
        elif dtype=="amount" and raw:
            pct=min(dval,raw)/raw*100.0
        else:
            pct=0.0
        untaxed=total=0.0
        hr=hall.tax_ids.compute_all(hall.base_price*(1-pct/100.0),currency=hall.currency_id,quantity=1.0,product=False,partner=partner)
        untaxed+=hr["total_excluded"]; total+=hr["total_included"]
        details=[{"name":hall.name,"qty":1,"base":hall.base_price,"kind":"hall"}]
        for service,qty in lines:
            tr=service.tax_ids.compute_all(service.price*(1-pct/100.0),currency=service.currency_id,quantity=qty,product=service.product_id,partner=partner)
            untaxed+=tr["total_excluded"];total+=tr["total_included"]
            details.append({"name":service.name,"qty":qty,"base":service.price*qty,"kind":"service"})
        return {"raw":raw,"discount_percent":pct,"discount_amount":raw*(pct/100.0),
                "untaxed":untaxed,"tax":total-untaxed,"total":total,
                "currency":hall.currency_id.symbol or hall.currency_id.name,"lines":details}

    @api.model
    def apply_to_event(self, booking_id, service_items=None, package_id=None, discount_type="none", discount_value=0.0):
        booking=self.env["qimam.booking"].browse(int(booking_id)).exists()
        if not booking or booking.branch_id != self.env.user.branch_id:
            raise UserError(_("Invalid booking."))
        if booking.state not in ("draft","hold"):
            raise UserError(_("Commercial configuration can only change before confirmation."))
        service_items=service_items or []
        commands=[(5,0,0)]
        for item in service_items:
            service=self.env["qimam.booking.service"].browse(int(item.get("id") or 0)).exists()
            qty=max(float(item.get("qty") or 0),0.0)
            if service and service.branch_id==self.env.user.branch_id and qty>0:
                commands.append((0,0,{"service_id":service.id,"quantity":qty,
                    "price_unit":service.price,"tax_ids":[(6,0,service.tax_ids.ids)]}))
        safe_discount_type=discount_type if discount_type in ("none","amount","percent") else "none"
        safe_discount_value=max(float(discount_value or 0.0),0.0)
        if safe_discount_type != "none" and safe_discount_value > 0 and not self.env.user.has_group("qimamhd_booking_v2.group_booking_supervisor"):
            raise UserError(_("Only a booking supervisor or manager may apply a discount."))
        vals={"service_line_ids":commands,"discount_type":safe_discount_type,
              "discount_value":safe_discount_value}
        if package_id:
            package=self.env["qimam.booking.package"].browse(int(package_id)).exists()
            if package and package.branch_id==self.env.user.branch_id: vals["package_id"]=package.id
        booking.write(vals)
        return {"id":booking.id,"total":booking.amount_total,"tax":booking.amount_tax,"untaxed":booking.amount_untaxed}
