# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class BookingMissionControl(models.AbstractModel):
    _name="qimam.booking.mission.control"
    _description="Event Mission Control"

    @api.model
    def board(self, booking_id):
        b=self.env["qimam.booking"].browse(int(booking_id)).exists()
        if not b or b.branch_id not in self.env.user.allowed_branch_ids:
            raise UserError(_("Invalid booking."))
        groups={"before":[],"day":[],"after":[]}
        for x in b.operation_item_ids:
            groups[x.timing].append({
                "id":x.id,"name":x.name,"category":x.category,"state":x.state,
                "required":x.required,"blocks":x.blocks_event,
                "responsible":x.responsible_id.name or _("Unassigned"),
                "note":x.note or "",
            })
        return {
            "id":b.id,"name":b.name,"customer":b.partner_id.name,"hall":b.hall_id.name,
            "date":b.booking_date.isoformat(),"state":b.state,
            "readiness":round(b.readiness_percent,1),"operational_status":b.operational_status,
            "blockers":b.blocking_operation_count,"items":groups,
            "financial":{"status":b.financial_status,"paid":b.amount_paid,"total":b.amount_total,
                         "currency":b.currency_id.symbol or b.currency_id.name},
        }

    @api.model
    def generate(self, booking_id):
        b=self.env["qimam.booking"].browse(int(booking_id)).exists()
        if not b or b.branch_id not in self.env.user.allowed_branch_ids: raise UserError(_("Invalid booking."))
        b.action_generate_operations()
        return self.board(b.id)

    @api.model
    def item_action(self, booking_id, item_id, action):
        b=self.env["qimam.booking"].browse(int(booking_id)).exists()
        item=self.env["qimam.booking.operation.item"].browse(int(item_id)).exists()
        if not b or not item or item.booking_id != b or b.branch_id not in self.env.user.allowed_branch_ids:
            raise UserError(_("Invalid operational item."))
        if action=="start": item.action_start()
        elif action=="done": item.action_done()
        elif action=="block": item.action_block()
        elif action=="reset": item.action_reset()
        else: raise UserError(_("Unknown action."))
        return self.board(b.id)

    @api.model
    def start_event(self, booking_id):
        b=self.env["qimam.booking"].browse(int(booking_id)).exists()
        if not b or b.branch_id not in self.env.user.allowed_branch_ids: raise UserError(_("Invalid booking."))
        b.action_start_event()
        return self.board(b.id)
