# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError
class StayReversalWizard(models.TransientModel):
    _name="qimam.stay.reversal.wizard"; _description="Hotel Stay Financial Reversal"
    stay_id=fields.Many2one("qimam.stay.booking",required=True,readonly=True)
    invoice_id=fields.Many2one("account.move",required=True,domain="[('qimam_stay_id','=',stay_id),('state','=','posted'),('type','=','out_invoice')]")
    reason=fields.Char(required=True)
    refund_method=fields.Selection([("refund","Create draft credit note"),("cancel","Reverse and reconcile")],default="refund",required=True)
    def action_reverse(self):
        self.ensure_one(); inv=self.invoice_id
        if inv.qimam_stay_id!=self.stay_id or inv.state!="posted": raise UserError(_("Select a posted invoice belonging to this stay."))
        rev=self.env["account.move.reversal"].with_context(active_model="account.move",active_ids=inv.ids).create({
            "refund_method":self.refund_method,"reason":self.reason,"date":fields.Date.context_today(self)})
        result=rev.reverse_moves()
        refunds=self.env["account.move"].search([("reversed_entry_id","=",inv.id),("type","=","out_refund")])
        vals={"qimam_stay_id":self.stay_id.id,"qimam_booking_invoice_kind":inv.qimam_booking_invoice_kind,"qimam_booking_factor":inv.qimam_booking_factor}
        if "branch_id" in self.env["account.move"]._fields: vals["branch_id"]=self.stay_id.branch_id.id
        refunds.write(vals); return result
