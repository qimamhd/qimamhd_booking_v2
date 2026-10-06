# -*- coding: utf-8 -*-
import json
from odoo import fields,models,_
from odoo.exceptions import UserError
class BookingMigrationWizard(models.TransientModel):
    _name="qimam.booking.migration.wizard"
    _description="V1 to V2 Migration"
    branch_id=fields.Many2one("custom.branches",required=True,default=lambda s:s.env.user.branch_id,
                              domain=lambda s:[("id","in",s.env.user.allowed_branch_ids.ids)])
    limit=fields.Integer(default=500,required=True)
    preview_json=fields.Text(readonly=True)
    def action_preview(self):
        self.ensure_one()
        data=self.env["qimam.booking.migration.service"].preview(self.branch_id.id,self.limit)
        self.preview_json=json.dumps(data,ensure_ascii=False,indent=2,default=str)
        return {"type":"ir.actions.act_window","res_model":self._name,"res_id":self.id,"view_mode":"form","target":"new"}
    def action_execute(self):
        self.ensure_one()
        if not self.env.user.has_group("qimamhd_booking_v2.group_booking_manager"):
            raise UserError(_("Only Booking Managers may execute migration."))
        data=self.env["qimam.booking.migration.service"].migrate_events(self.branch_id.id,self.limit,False)
        self.preview_json=json.dumps(data,ensure_ascii=False,indent=2,default=str)
        return {"type":"ir.actions.act_window","res_model":self._name,"res_id":self.id,"view_mode":"form","target":"new"}
