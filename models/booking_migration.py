# -*- coding: utf-8 -*-
import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class BookingMigrationMap(models.Model):
    _name="qimam.booking.migration.map"
    _description="V1 to V2 Migration Mapping"
    _order="id desc"
    _rec_name="legacy_display_name"

    legacy_model=fields.Char(required=True,index=True,readonly=True)
    legacy_id=fields.Integer(required=True,index=True,readonly=True)
    legacy_display_name=fields.Char(readonly=True)
    target_model=fields.Char(required=True,index=True,readonly=True)
    target_id=fields.Integer(index=True,readonly=True)
    branch_id=fields.Many2one("custom.branches",required=True,index=True,readonly=True)
    status=fields.Selection([("migrated","Migrated"),("skipped","Skipped"),("blocked","Blocked"),("error","Error")],
                            required=True,index=True,readonly=True)
    message=fields.Text(readonly=True)
    snapshot=fields.Text(readonly=True)
    migrated_at=fields.Datetime(default=fields.Datetime.now,readonly=True)
    migrated_by=fields.Many2one("res.users",default=lambda s:s.env.user,readonly=True)

    _sql_constraints=[
        ("legacy_target_unique","unique(legacy_model,legacy_id,target_model)",
         "A legacy record can only map once to a target model.")
    ]

class BookingMigrationService(models.AbstractModel):
    _name="qimam.booking.migration.service"
    _description="Safe V1 to V2 Booking Migration"

    @api.model
    def legacy_available(self):
        return "hotel.master" in self.env

    def _map(self,legacy,target_model,status,message="",target_id=False,snapshot=None):
        vals={
            "legacy_model":legacy._name,"legacy_id":legacy.id,
            "legacy_display_name":legacy.display_name,"target_model":target_model,
            "target_id":target_id or False,"branch_id":legacy.branch_id.id,
            "status":status,"message":message,
            "snapshot":json.dumps(snapshot or {},ensure_ascii=False,default=str),
        }
        existing=self.env["qimam.booking.migration.map"].search([
            ("legacy_model","=",legacy._name),("legacy_id","=",legacy.id),("target_model","=",target_model)],limit=1)
        if existing:
            # Never remap a successful migration. Failed/blocked rows may be refreshed after correction.
            if existing.status=="migrated": return existing
            existing.write(vals);return existing
        return self.env["qimam.booking.migration.map"].create(vals)

    def _state(self,legacy):
        return {
            "initial_booking":"draft",
            "booking_done":"confirmed",
            "finish_booking":"completed",
            "cancel_booking":"cancelled",
        }.get(legacy.state,"draft")

    def _date(self,legacy):
        # V1 events may contain a range; V2 event availability is day + periods.
        # We only auto-migrate unambiguous single-day event contracts.
        start=legacy.booking_start_date
        end=legacy.booking_end_date
        if not start: raise ValidationError(_("Legacy booking has no start date."))
        if end and end != start:
            raise ValidationError(_("Multi-day legacy event requires explicit migration review; it is not converted to a hotel stay."))
        return start

    @api.model
    def preview(self,branch_id=None,limit=500):
        if not self.legacy_available():
            raise UserError(_("Legacy model hotel.master is not installed in this database."))
        branch=self.env["custom.branches"].browse(branch_id).exists() if branch_id else self.env.user.branch_id
        if branch not in self.env.user.allowed_branch_ids: raise UserError(_("Branch is not allowed."))
        rows=self.env["hotel.master"].search([("branch_id","=",branch.id)],limit=min(max(int(limit),1),5000))
        result={"branch_id":branch.id,"branch_name":branch.name,"total":len(rows),"ready":0,"blocked":0,"already_migrated":0,"items":[]}
        for old in rows:
            mapped=self.env["qimam.booking.migration.map"].search([
                ("legacy_model","=","hotel.master"),("legacy_id","=",old.id),("target_model","=","qimam.booking"),
                ("status","=","migrated")],limit=1)
            if mapped:
                result["already_migrated"]+=1;status="already_migrated";reason=mapped.target_id
            else:
                try:
                    self._date(old)
                    if not old.partner_id: raise ValidationError(_("Missing customer."))
                    if not old.department_id: raise ValidationError(_("Missing legacy hall/department."))
                    status="ready";reason="";result["ready"]+=1
                except Exception as exc:
                    status="blocked";reason=str(exc);result["blocked"]+=1
            result["items"].append({"legacy_id":old.id,"name":old.display_name,"status":status,"reason":reason})
        return result

    def _hall(self,legacy):
        # Deterministic mapping by legacy source ID stored in migration map.
        Map=self.env["qimam.booking.migration.map"]
        mapped=Map.search([("legacy_model","=",legacy.department_id._name),("legacy_id","=",legacy.department_id.id),
                           ("target_model","=","qimam.booking.hall"),("status","=","migrated")],limit=1)
        if mapped:
            hall=self.env["qimam.booking.hall"].browse(mapped.target_id).exists()
            if hall:return hall
        # Create one branch-scoped hall from legacy department; never merge same names across branches.
        vals={"name":legacy.department_id.display_name,"branch_id":legacy.branch_id.id,
              "company_id":legacy.company_id.id if legacy.company_id else self.env.company.id,
              "active":True}
        if "capacity" in legacy.department_id._fields and "capacity" in self.env["qimam.booking.hall"]._fields:
            vals["capacity"]=legacy.department_id.capacity or 0
        hall=self.env["qimam.booking.hall"].create(vals)
        self._map(legacy.department_id,"qimam.booking.hall","migrated","Legacy hall created",hall.id,
                  {"name":legacy.department_id.display_name})
        return hall

    def _default_period(self,legacy):
        # V1 had no canonical period occupancy. We must not pretend otherwise.
        # A dedicated branch period marks imported legacy occupancy.
        Period=self.env["qimam.booking.period"]
        p=Period.search([("branch_id","=",legacy.branch_id.id),("code","=","legacy_full_day")],limit=1)
        if not p:
            p=Period.create({"name":_("Legacy / Full Day"),"code":"legacy_full_day","branch_id":legacy.branch_id.id,
                             "company_id":legacy.company_id.id if legacy.company_id else self.env.company.id,
                             "active":True})
        return p

    @api.model
    def migrate_events(self,branch_id=None,limit=500,dry_run=True):
        preview=self.preview(branch_id,limit)
        if dry_run:return preview
        branch=self.env["custom.branches"].browse(preview["branch_id"])
        rows=self.env["hotel.master"].search([("branch_id","=",branch.id)],limit=min(max(int(limit),1),5000))
        summary={"branch_id":branch.id,"migrated":0,"blocked":0,"skipped":0,"errors":0}
        for old in rows:
            existing=self.env["qimam.booking.migration.map"].search([
                ("legacy_model","=","hotel.master"),("legacy_id","=",old.id),
                ("target_model","=","qimam.booking"),("status","=","migrated")],limit=1)
            if existing:summary["skipped"]+=1;continue
            try:
                date=self._date(old)
                if not old.partner_id or not old.department_id:
                    raise ValidationError(_("Customer and hall are required."))
                hall=self._hall(old);period=self._default_period(old)
                vals={
                    "name":old.name if "name" in old._fields and old.name else _("New"),
                    "partner_id":old.partner_id.id,"booking_date":date,"hall_id":hall.id,
                    "branch_id":old.branch_id.id,
                    "company_id":old.company_id.id if old.company_id else self.env.company.id,
                    "state":"draft",
                    "hall_price_unit":old.department_price if "department_price" in old._fields else 0.0,
                    "period_line_ids":[(0,0,{"period_id":period.id})],
                    "note":_("Migrated from V1 record %s. Original state: %s")%(old.id,old.state),
                }
                new=self.env["qimam.booking"].with_context(qimam_skip_security_audit=True).create(vals)
                target_state=self._state(old)
                # Migration preserves historical lifecycle without firing current workflow side effects.
                new.with_context(qimam_skip_security_audit=True).write({"state":target_state})
                self._map(old,"qimam.booking","migrated","Event contract migrated",new.id,{
                    "state":old.state,"booking_start_date":old.booking_start_date,
                    "booking_end_date":old.booking_end_date,"branch_id":old.branch_id.id,
                    "department_id":old.department_id.id,"partner_id":old.partner_id.id,
                })
                summary["migrated"]+=1
            except (ValidationError,UserError) as exc:
                self._map(old,"qimam.booking","blocked",str(exc),snapshot={"state":old.state})
                summary["blocked"]+=1
            except Exception as exc:
                self._map(old,"qimam.booking","error",str(exc),snapshot={"state":old.state})
                summary["errors"]+=1
        return summary
