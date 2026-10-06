# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

PREFIX="[QIMAM-DEMO]"

class BookingDemoRun(models.Model):
    _name="qimam.booking.demo.run"
    _description="Booking Demo Dataset Run"
    _order="id desc"
    name=fields.Char(required=True,default=lambda self:_("Integrated Booking Demo"))
    company_id=fields.Many2one("res.company",required=True,default=lambda self:self.env.company)
    branch_id=fields.Many2one("custom.branches",required=True)
    created_by=fields.Many2one("res.users",required=True,default=lambda self:self.env.user)
    created_at=fields.Datetime(default=fields.Datetime.now,required=True)
    state=fields.Selection([("building","Building"),("ready","Ready"),("failed","Failed")],default="building",required=True)
    summary=fields.Text()
    event_booking_ids=fields.Many2many("qimam.booking","qimam_demo_run_event_rel","run_id","booking_id")
    stay_booking_ids=fields.Many2many("qimam.stay.booking","qimam_demo_run_stay_rel","run_id","stay_id")

class BookingDemoBuilder(models.AbstractModel):
    _name="qimam.booking.demo.builder"
    _description="Integrated Booking Demo Builder"

    def _manager(self):
        if not self.env.user.has_group("qimamhd_booking_v2.group_booking_manager"):
            raise AccessError(_("Only Booking Managers can create demo data."))

    def _branch(self, branch_id=None):
        b=self.env["custom.branches"].browse(branch_id).exists() if branch_id else self.env.user.branch_id
        if not b or b not in self.env.user.allowed_branch_ids:
            raise AccessError(_("Select an allowed current branch before creating demo data."))
        return b

    def _find_or_create(self,model,domain,vals):
        rec=self.env[model].search(domain,limit=1)
        return rec or self.env[model].create(vals)

    def _sale_tax(self):
        Tax=self.env["account.tax"]
        tax=Tax.search([("company_id","=",self.env.company.id),("type_tax_use","=","sale"),("amount","=",15.0)],limit=1)
        if not tax:
            tax=Tax.create({"name":"VAT 15% - Qimam Demo","amount":15.0,"amount_type":"percent",
                            "type_tax_use":"sale","company_id":self.env.company.id})
        return tax

    def _customer(self,ref,name,mobile,email=""):
        Partner=self.env["res.partner"]
        rec=Partner.search([("ref","=",ref)],limit=1)
        return rec or Partner.create({"name":name,"ref":ref,"mobile":mobile,"phone":mobile,
                                      "email":email,"customer_rank":1})

    def _event(self,branch,partner,hall,date,periods,state,guest,note,services=None,discount=None):
        vals={"partner_id":partner.id,"branch_id":branch.id,"booking_date":date,"hall_id":hall.id,
              "guest_count":guest,"note":"%s %s"%(PREFIX,note),"hall_price_unit":hall.base_price,
              "hall_tax_ids":[(6,0,hall.tax_ids.ids)],
              "period_line_ids":[(0,0,{"period_id":p.id}) for p in periods]}
        if services:
            vals["service_line_ids"]=[(0,0,{"service_id":x.id,"quantity":1,"price_unit":x.price,
                                            "tax_ids":[(6,0,x.tax_ids.ids)]}) for x in services]
        # Demo builder is manager-only; set commercial snapshots explicitly.
        if discount: vals.update(discount)
        b=self.env["qimam.booking"].create(vals)
        # Historical demo states are set directly to demonstrate every stage without fake accounting side effects.
        b.write({"state":state})
        return b

    def _stay(self,branch,partner,resource,start,nights,state,note):
        r=self.env["qimam.stay.booking"].create({
            "partner_id":partner.id,"branch_id":branch.id,"resource_id":resource.id,
            "checkin_date":start,"checkout_date":start+timedelta(days=nights),
            "price_per_night":resource.base_price,"room_tax_ids":[(6,0,resource.tax_ids.ids)],
            "note":"%s %s"%(PREFIX,note)})
        r.write({"state":state})
        return r

    @api.model
    def build(self,branch_id=None):
        self._manager(); branch=self._branch(branch_id)
        # Idempotency: one ready dataset per company+branch.
        existing=self.env["qimam.booking.demo.run"].search([
            ("company_id","=",self.env.company.id),("branch_id","=",branch.id),("state","=","ready")],limit=1)
        if existing:
            return {"created":False,"run_id":existing.id,"message":_("Demo data already exists for this branch."),
                    "events":len(existing.event_booking_ids),"stays":len(existing.stay_booking_ids)}

        run=self.env["qimam.booking.demo.run"].create({"branch_id":branch.id,"company_id":self.env.company.id})
        try:
            with self.env.cr.savepoint():
                tax=self._sale_tax()
                # Master data
                periods=[]
                for code,name,a,b in [("DEMO_AM","الفترة الصباحية",8,13),("DEMO_PM","الفترة المسائية",14,19),("DEMO_NIGHT","الفترة الليلية",20,24)]:
                    periods.append(self._find_or_create("qimam.booking.period",
                        [("branch_id","=",branch.id),("code","=",code)],
                        {"name":name,"code":code,"time_from":a,"time_to":b,"branch_id":branch.id,"company_id":self.env.company.id}))
                halls=[]
                for code,name,cap,price in [("DEMO_ROYAL","قاعة رويال",350,8500),("DEMO_PEARL","قاعة اللؤلؤة",180,5200),("DEMO_FAMILY","قاعة العائلة",80,2800)]:
                    halls.append(self._find_or_create("qimam.booking.hall",
                        [("branch_id","=",branch.id),("code","=",code)],
                        {"name":name,"code":code,"capacity":cap,"base_price":price,"tax_ids":[(6,0,[tax.id])],
                         "branch_id":branch.id,"company_id":self.env.company.id,
                         "description":"%s قاعة تجريبية واقعية"%PREFIX}))
                services=[]
                for name,price in [("بوفيه ضيافة",3200),("تصوير المناسبة",1800),("تنسيق وزهور",2400),("شاشة وصوت",950),("ركن قهوة",750)]:
                    services.append(self._find_or_create("qimam.booking.service",
                        [("branch_id","=",branch.id),("name","=",name)],
                        {"name":name,"price":price,"tax_ids":[(6,0,[tax.id])],"branch_id":branch.id,"company_id":self.env.company.id}))
                package=self._find_or_create("qimam.booking.package",
                    [("branch_id","=",branch.id),("name","=","باقة ليلة متكاملة - Demo")],
                    {"name":"باقة ليلة متكاملة - Demo","description":"%s ضيافة + تصوير + تنسيق"%PREFIX,
                     "branch_id":branch.id,"company_id":self.env.company.id,
                     "line_ids":[(0,0,{"service_id":x.id,"quantity":1}) for x in services[:3]]})
                room_type=self._find_or_create("qimam.booking.resource.type",
                    [("branch_id","=",branch.id),("code","=","DEMO_ROOM")],
                    {"name":"غرفة فندقية","code":"DEMO_ROOM","booking_mode":"stay","icon":"room",
                     "branch_id":branch.id,"company_id":self.env.company.id})
                suite_type=self._find_or_create("qimam.booking.resource.type",
                    [("branch_id","=",branch.id),("code","=","DEMO_SUITE")],
                    {"name":"جناح","code":"DEMO_SUITE","booking_mode":"stay","icon":"apartment",
                     "branch_id":branch.id,"company_id":self.env.company.id})
                resources=[]
                for code,name,typ,floor,cap,price in [
                    ("D101","غرفة 101",room_type,"1",2,420),("D102","غرفة 102",room_type,"1",2,420),
                    ("D201","غرفة 201",room_type,"2",3,520),("DS01","جناح ملكي",suite_type,"3",5,1100)]:
                    resources.append(self._find_or_create("qimam.booking.resource",
                        [("branch_id","=",branch.id),("code","=",code)],
                        {"name":name,"code":code,"resource_type_id":typ.id,"floor":floor,"capacity":cap,
                         "base_price":price,"tax_ids":[(6,0,[tax.id])],"branch_id":branch.id,"company_id":self.env.company.id}))
                customers=[
                    self._customer("QDEMO-001","أحمد سالم العتيبي","0501234501","ahmed.demo@example.com"),
                    self._customer("QDEMO-002","نورة محمد القحطاني","0501234502","noura.demo@example.com"),
                    self._customer("QDEMO-003","خالد عبدالله الغامدي","0501234503"),
                    self._customer("QDEMO-004","ريم فهد الدوسري","0501234504"),
                    self._customer("QDEMO-005","شركة آفاق للمناسبات","0112345678","events.demo@example.com"),
                    self._customer("QDEMO-006","سارة علي الحربي","0501234506"),
                ]
                today=fields.Date.context_today(self)
                events=[
                    self._event(branch,customers[0],halls[0],today+timedelta(days=14),[periods[2]],"draft",220,"طلب جديد لم يثبت بعد",services[:2]),
                    self._event(branch,customers[1],halls[1],today+timedelta(days=7),[periods[1]],"hold",140,"حجز مؤقت بانتظار قرار العميل",[services[4]]),
                    self._event(branch,customers[2],halls[0],today+timedelta(days=21),[periods[0]],"confirmed",300,"حجز مؤكد كامل",[services[0],services[2]]),
                    self._event(branch,customers[4],halls[2],today+timedelta(days=2),[periods[1]],"preparing",70,"تجهيزات المناسبة قيد التنفيذ",[services[3]]),
                    self._event(branch,customers[3],halls[1],today,[periods[2]],"event",160,"مناسبة اليوم",[services[0],services[3]]),
                    self._event(branch,customers[5],halls[2],today-timedelta(days=5),[periods[0]],"completed",60,"مناسبة مكتملة",[services[4]]),
                    self._event(branch,customers[0],halls[0],today+timedelta(days=30),[periods[0],periods[1],periods[2]],"confirmed",330,"حجز يوم كامل - جميع الفترات",[services[0],services[1],services[2]],{"discount_type":"percent","discount_value":10}),
                    self._event(branch,customers[3],halls[1],today+timedelta(days=35),[periods[0]],"cancelled",120,"مثال حجز ملغي",[]),
                ]
                # Package snapshot example.
                events[6].write({"package_id":package.id})
                stays=[
                    self._stay(branch,customers[0],resources[0],today+timedelta(days=10),2,"draft","استفسار/مسودة إقامة"),
                    self._stay(branch,customers[1],resources[1],today+timedelta(days=5),3,"hold","غرفة ممسوكة مؤقتًا"),
                    self._stay(branch,customers[2],resources[2],today+timedelta(days=15),4,"confirmed","إقامة مؤكدة"),
                    self._stay(branch,customers[3],resources[3],today-timedelta(days=1),3,"checked_in","النزيل داخل الجناح الآن"),
                    self._stay(branch,customers[4],resources[0],today-timedelta(days=8),2,"checked_out","إقامة مكتملة"),
                    self._stay(branch,customers[5],resources[2],today+timedelta(days=28),2,"cancelled","مثال إقامة ملغاة"),
                ]
                # Readiness examples for the preparing event without relying on global templates.
                for seq,name,category,state,block in [
                    (10,"تأكيد ترتيب القاعة","venue","done",True),(20,"فحص السلامة والمخارج","safety","done",True),
                    (30,"تجهيز نظام الصوت","service","progress",True),(40,"تأكيد عدد الضيوف","guest","todo",False)]:
                    self.env["qimam.booking.operation.item"].sudo().create({
                        "booking_id":events[3].id,"branch_id":branch.id,"sequence":seq,"name":name,
                        "category":category,"timing":"before","required":True,"blocks_event":block,"state":state})
                run.write({"state":"ready","event_booking_ids":[(6,0,[x.id for x in events])],
                           "stay_booking_ids":[(6,0,[x.id for x in stays])],
                           "summary":_("Created: 3 periods, 3 halls, 5 services, 1 package, 2 resource types, 4 rooms/suites, 6 customers, 8 event scenarios and 6 stay scenarios.")})
            return {"created":True,"run_id":run.id,"events":8,"stays":6,
                    "message":_("Integrated demo data created successfully.")}
        except Exception as exc:
            run.sudo().write({"state":"failed","summary":str(exc)})
            raise

class ResConfigSettings(models.TransientModel):
    _inherit="res.config.settings"

    qimam_demo_branch_id=fields.Many2one("custom.branches",string="Demo Branch",
        domain=lambda self:[("id","in",self.env.user.allowed_branch_ids.ids)],
        default=lambda self:self.env.user.branch_id)
    qimam_demo_exists=fields.Boolean(compute="_compute_qimam_demo_exists")
    qimam_demo_summary=fields.Char(compute="_compute_qimam_demo_exists")

    def _compute_qimam_demo_exists(self):
        Run=self.env["qimam.booking.demo.run"].sudo()
        for rec in self:
            branch=rec.qimam_demo_branch_id or self.env.user.branch_id
            run=Run.search([("company_id","=",self.env.company.id),("branch_id","=",branch.id),("state","=","ready")],limit=1) if branch else Run
            rec.qimam_demo_exists=bool(run)
            rec.qimam_demo_summary=run.summary if run else _("No demo dataset has been created for this branch.")

    def action_qimam_create_demo(self):
        self.ensure_one()
        result=self.env["qimam.booking.demo.builder"].build(self.qimam_demo_branch_id.id)
        return {"type":"ir.actions.client","tag":"display_notification",
                "params":{"title":_("Booking Demo"),"message":result["message"],"type":"success","sticky":False,
                          "next":{"type":"ir.actions.client","tag":"reload"}}}
