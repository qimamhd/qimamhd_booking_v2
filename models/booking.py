# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError, AccessError


BLOCKING_STATES = ("hold", "confirmed", "preparing", "event", "completed")


class Booking(models.Model):
    _name = "qimam.booking"
    _description = "Hall Booking"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "booking_date desc, id desc"

    name = fields.Char(
        string="Contract Number", required=True, copy=False, readonly=True,
        default=lambda self: _("New"), tracking=True
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("hold", "Temporary Hold"),
            ("confirmed", "Confirmed"),
            ("preparing", "Preparing"),
            ("event", "Event"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft", required=True, tracking=True, index=True
    )
    partner_id = fields.Many2one(
        "res.partner", string="Customer", required=True, tracking=True, index=True
    )
    booking_date = fields.Date(required=True, tracking=True, index=True)
    hall_id = fields.Many2one(
        "qimam.booking.hall", required=True, tracking=True, index=True,
        domain="[('company_id', '=', company_id)]"
    )
    period_line_ids = fields.One2many(
        "qimam.booking.period.line", "booking_id", string="Periods", copy=True
    )
    period_ids = fields.Many2many(
        "qimam.booking.period", compute="_compute_period_ids", string="Selected Periods"
    )
    optional_time_from = fields.Float(string="Optional Start Time")
    optional_time_to = fields.Float(string="Optional End Time")
    guest_count = fields.Integer(tracking=True)
    package_id = fields.Many2one(
        "qimam.booking.package", domain="[('company_id', '=', company_id)]"
    )
    service_line_ids = fields.One2many(
        "qimam.booking.service.line", "booking_id", string="Services", copy=True
    )
    note = fields.Text()
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id", readonly=True, store=True
    )
    hall_price_unit = fields.Monetary(
        string="Hall Contract Price", currency_field="currency_id", tracking=True,
        help="Price snapshot for this contract; it does not change when hall master price changes."
    )
    hall_tax_ids = fields.Many2many(
        "account.tax", "qimam_booking_hall_tax_rel", "booking_id", "tax_id",
        string="Hall Contract Taxes", domain=[("type_tax_use", "=", "sale")]
    )
    amount_untaxed = fields.Monetary(
        compute="_compute_amounts", store=True, currency_field="currency_id"
    )
    amount_tax = fields.Monetary(
        compute="_compute_amounts", store=True, currency_field="currency_id"
    )
    amount_total = fields.Monetary(
        compute="_compute_amounts", store=True, currency_field="currency_id", tracking=True
    )
    discount_type = fields.Selection(
        [("none", "No Discount"), ("amount", "Amount"), ("percent", "Percentage")],
        default="none"
    )
    discount_value = fields.Monetary(currency_field="currency_id")
    invoice_ids = fields.One2many(
        "account.move", "qimam_booking_id", string="Invoices", readonly=True
    )
    invoice_count = fields.Integer(compute="_compute_invoice_count")
    amount_invoiced = fields.Monetary(
        compute="_compute_financial_status", currency_field="currency_id"
    )
    amount_credited = fields.Monetary(
        compute="_compute_financial_status", currency_field="currency_id"
    )
    amount_due = fields.Monetary(
        compute="_compute_financial_status", currency_field="currency_id"
    )
    amount_paid = fields.Monetary(
        compute="_compute_financial_status", currency_field="currency_id"
    )
    invoice_progress = fields.Float(compute="_compute_financial_status")
    financial_status = fields.Selection(
        [
            ("not_invoiced", "Not Invoiced"),
            ("draft_invoice", "Draft Invoice"),
            ("invoiced", "Invoiced"),
            ("partial", "Partially Paid"),
            ("paid", "Paid"),
            ("credit", "Credit / Reversal"),
        ],
        compute="_compute_financial_status",
        string="Financial Status",
    )
    hold_until = fields.Datetime(copy=False, tracking=True)
    payment_schedule_ids = fields.One2many(
        "qimam.booking.payment.schedule", "booking_id", string="Payment Schedule", copy=True
    )
    payment_schedule_count = fields.Integer(compute="_compute_payment_schedule_count")
    next_due_date = fields.Date(compute="_compute_due_summary")
    attention_level = fields.Selection([("ok","On Track"),("info","Follow Up"),("warning","Needs Attention")], compute="_compute_attention_level")
    attention_message = fields.Char(compute="_compute_attention_level")
    overdue_amount = fields.Monetary(
        compute="_compute_due_summary", currency_field="currency_id"
    )
    cancellation_reason = fields.Text(readonly=True, tracking=True)
    cancelled_by = fields.Many2one("res.users", readonly=True, copy=False)
    cancelled_at = fields.Datetime(readonly=True, copy=False)

    @api.depends("period_line_ids.period_id")
    def _compute_period_ids(self):
        for rec in self:
            rec.period_ids = rec.period_line_ids.mapped("period_id")

    @api.depends(
        "hall_price_unit",
        "hall_tax_ids",
        "service_line_ids.quantity",
        "service_line_ids.price_unit",
        "service_line_ids.tax_ids",
        "discount_type",
        "discount_value",
    )
    def _compute_amounts(self):
        for rec in self:
            raw_untaxed = rec.hall_price_unit or 0.0
            for line in rec.service_line_ids:
                raw_untaxed += line.price_unit * line.quantity

            discount_percent = 0.0
            if rec.discount_type == "percent":
                discount_percent = min(max(rec.discount_value, 0.0), 100.0)
            elif rec.discount_type == "amount" and raw_untaxed:
                discount_percent = min(max(rec.discount_value, 0.0), raw_untaxed) / raw_untaxed * 100.0

            untaxed = 0.0
            total = 0.0
            if rec.hall_price_unit:
                result = rec.hall_tax_ids.compute_all(
                    rec.hall_price_unit * (1.0 - discount_percent / 100.0),
                    currency=rec.currency_id, quantity=1.0,
                    product=False, partner=rec.partner_id
                )
                untaxed += result["total_excluded"]
                total += result["total_included"]

            for line in rec.service_line_ids:
                result = line.tax_ids.compute_all(
                    line.price_unit * (1.0 - discount_percent / 100.0),
                    currency=rec.currency_id, quantity=line.quantity,
                    product=line.service_id.product_id,
                    partner=rec.partner_id
                )
                untaxed += result["total_excluded"]
                total += result["total_included"]

            rec.amount_untaxed = untaxed
            rec.amount_tax = total - untaxed
            rec.amount_total = total

    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids.filtered(lambda m: m.state != "cancel"))

    def _compute_payment_schedule_count(self):
        for rec in self:
            rec.payment_schedule_count = len(rec.payment_schedule_ids)

    @api.depends(
        "payment_schedule_ids.due_date", "payment_schedule_ids.amount",
        "amount_paid", "state"
    )
    def _compute_due_summary(self):
        today = fields.Date.context_today(self)
        for rec in self:
            remaining_paid = rec.amount_paid
            overdue = 0.0
            next_due = False
            lines = rec.payment_schedule_ids.sorted(
                key=lambda x: (x.due_date or fields.Date.today(), x.sequence, x.id)
            )
            for line in lines:
                covered = min(max(remaining_paid, 0.0), line.amount)
                remaining_paid -= covered
                open_amount = max(line.amount - covered, 0.0)
                if open_amount <= rec.currency_id.rounding:
                    continue
                if line.due_date and line.due_date < today:
                    overdue += open_amount
                if not next_due and line.due_date:
                    next_due = line.due_date
            rec.overdue_amount = overdue
            rec.next_due_date = next_due

    @api.depends(
        "invoice_ids.state", "invoice_ids.type", "invoice_ids.amount_total",
        "invoice_ids.amount_residual", "invoice_ids.qimam_booking_factor"
    )
    def _compute_financial_status(self):
        for rec in self:
            active = rec.invoice_ids.filtered(lambda m: m.state != "cancel")
            posted = active.filtered(lambda m: m.state == "posted")
            invoices = posted.filtered(lambda m: m.type == "out_invoice")
            credits = posted.filtered(lambda m: m.type == "out_refund")

            invoiced = sum(invoices.mapped("amount_total"))
            credited = sum(credits.mapped("amount_total"))
            invoice_residual = sum(invoices.mapped("amount_residual"))
            credit_residual = sum(credits.mapped("amount_residual"))
            net_due = max(invoice_residual - credit_residual, 0.0)
            net_invoiced = max(invoiced - credited, 0.0)
            paid = max(net_invoiced - net_due, 0.0)

            invoice_factor = sum(invoices.mapped("qimam_booking_factor"))
            credit_factor = sum(credits.mapped("qimam_booking_factor"))
            progress = max(invoice_factor - credit_factor, 0.0) * 100.0

            rec.amount_invoiced = invoiced
            rec.amount_credited = credited
            rec.amount_due = net_due
            rec.amount_paid = paid
            rec.invoice_progress = min(progress, 100.0)

            if credits:
                rec.financial_status = "credit"
            elif not active:
                rec.financial_status = "not_invoiced"
            elif not posted:
                rec.financial_status = "draft_invoice"
            elif net_due <= rec.currency_id.rounding:
                rec.financial_status = "paid"
            elif paid > rec.currency_id.rounding:
                rec.financial_status = "partial"
            else:
                rec.financial_status = "invoiced"

    @api.depends("state", "overdue_amount", "hold_until", "financial_status", "invoice_progress")
    def _compute_attention_level(self):
        for rec in self:
            if rec.overdue_amount > rec.currency_id.rounding:
                rec.attention_level="warning"; rec.attention_message=_("There are overdue contractual dues.")
            elif rec.state=="hold":
                rec.attention_level="info"; rec.attention_message=_("Temporary hold is waiting for confirmation.")
            elif rec.state in ("confirmed","preparing") and rec.invoice_progress < 100:
                rec.attention_level="info"; rec.attention_message=_("Contract is not fully invoiced yet.")
            else:
                rec.attention_level="ok"; rec.attention_message=_("Everything looks on track.")

    def _net_invoiced_factor(self):
        """Posted economic exposure. Used for reporting only."""
        self.ensure_one()
        posted = self.invoice_ids.filtered(lambda m: m.state == "posted")
        invoices = posted.filtered(lambda m: m.type == "out_invoice")
        credits = posted.filtered(lambda m: m.type == "out_refund")
        return max(
            sum(invoices.mapped("qimam_booking_factor")) -
            sum(credits.mapped("qimam_booking_factor")),
            0.0
        )

    def _reserved_invoice_factor(self):
        """Capacity already consumed by active draft/posted invoices, net of posted credits.

        Draft invoices reserve invoice capacity so two drafts cannot each claim the same
        remaining percentage. Cancelled moves release that capacity.
        """
        self.ensure_one()
        active_invoices = self.invoice_ids.filtered(
            lambda m: m.type == "out_invoice" and m.state in ("draft", "posted")
        )
        posted_credits = self.invoice_ids.filtered(
            lambda m: m.type == "out_refund" and m.state == "posted"
        )
        return max(
            sum(active_invoices.mapped("qimam_booking_factor")) -
            sum(posted_credits.mapped("qimam_booking_factor")),
            0.0
        )

    def _lock_financial_capacity(self):
        self.ensure_one()
        self.env.cr.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
            ("qimam.booking.invoice", str(self.id)),
        )

    def _discount_percent(self):
        self.ensure_one()
        raw = (self.hall_price_unit or 0.0) + sum(
            line.price_unit * line.quantity for line in self.service_line_ids
        )
        if self.discount_type == "percent":
            return min(max(self.discount_value, 0.0), 100.0)
        if self.discount_type == "amount" and raw:
            return min(max(self.discount_value, 0.0), raw) / raw * 100.0
        return 0.0

    def _prepare_contract_invoice_lines(self, factor=1.0):
        self.ensure_one()
        discount = self._discount_percent()
        lines = []
        if self.hall_price_unit:
            lines.append((0, 0, {
                "name": _("Hall: %s") % self.hall_id.name,
                "quantity": factor,
                "price_unit": self.hall_price_unit,
                "discount": discount,
                "tax_ids": [(6, 0, self.hall_tax_ids.ids)],
            }))
        for line in self.service_line_ids:
            lines.append((0, 0, {
                "product_id": line.service_id.product_id.id or False,
                "name": line.service_id.name,
                "quantity": line.quantity * factor,
                "price_unit": line.price_unit,
                "discount": discount,
                "tax_ids": [(6, 0, line.tax_ids.ids)],
            }))
        return lines

    def _check_discount_authorization_vals(self, vals):
        if not ({"discount_type","discount_value"} & set(vals)):
            return
        dtype=vals.get("discount_type", self.discount_type if self else "none")
        dval=vals.get("discount_value", self.discount_value if self else 0.0)
        if dtype!="none" and float(dval or 0.0)>0.0 and not self.env.user.has_group("qimamhd_booking_v2.group_booking_supervisor"):
            raise AccessError(_("Only Booking Supervisors may apply or change discounts."))

    @api.model
    def create(self, vals):
        self._check_discount_authorization_vals(vals)
        if vals.get("name", _("New")) == _("New"):
            vals["name"] = self.env["ir.sequence"].next_by_code("qimam.booking") or _("New")
        hall_id = vals.get("hall_id")
        if hall_id and "hall_price_unit" not in vals:
            hall = self.env["qimam.booking.hall"].browse(hall_id)
            vals["hall_price_unit"] = hall.base_price
            if "hall_tax_ids" not in vals:
                vals["hall_tax_ids"] = [(6, 0, hall.tax_ids.ids)]
        rec = super().create(vals)
        rec._validate_booking_integrity()
        return rec

    @api.onchange("hall_id")
    def _onchange_hall_id_snapshot(self):
        if self.hall_id and self.state == "draft":
            self.hall_price_unit = self.hall_id.base_price
            self.hall_tax_ids = self.hall_id.tax_ids

    def write(self, vals):
        self._check_discount_authorization_vals(vals)
        critical = {"booking_date", "hall_id", "state", "company_id", "branch_id", "period_line_ids"}
        result = super().write(vals)
        if critical.intersection(vals):
            self._validate_booking_integrity()
        return result

    @api.constrains("booking_date", "hall_id", "state", "company_id")
    def _constraint_booking_integrity(self):
        self._validate_booking_integrity()

    @api.constrains("guest_count", "hall_id")
    def _check_capacity(self):
        for rec in self:
            if rec.guest_count < 0:
                raise ValidationError(_("Guest count cannot be negative."))
            if rec.hall_id.capacity and rec.guest_count > rec.hall_id.capacity:
                raise ValidationError(
                    _("Guest count (%s) exceeds hall capacity (%s).")
                    % (rec.guest_count, rec.hall_id.capacity)
                )

    def _validate_booking_integrity(self):
        for rec in self:
            if rec.hall_id and rec.hall_id.branch_id != rec.branch_id:
                raise ValidationError(_("The hall must belong to the booking branch."))
            if any(line.period_id.branch_id != rec.branch_id for line in rec.period_line_ids):
                raise ValidationError(_("All booking periods must belong to the booking branch."))
            if rec.state not in BLOCKING_STATES:
                continue
            if not rec.booking_date or not rec.hall_id or not rec.period_line_ids:
                raise ValidationError(
                    _("A blocking booking requires a date, hall, and at least one period.")
                )
            period_ids = rec.period_line_ids.mapped("period_id").ids
            if len(period_ids) != len(set(period_ids)):
                raise ValidationError(_("The same period cannot be selected twice."))

            # Transaction-level advisory lock serializes bookings for the same
            # company/hall/date. It closes the classic race where two users confirm
            # the same slot at the same instant.
            self.env.cr.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
                ("branch:%s:hall:%s" % (rec.branch_id.id, rec.hall_id.id), str(rec.booking_date)),
            )

            conflict = self.search([
                ("id", "!=", rec.id),
                ("branch_id", "=", rec.branch_id.id),
                ("hall_id", "=", rec.hall_id.id),
                ("booking_date", "=", rec.booking_date),
                ("state", "in", BLOCKING_STATES),
                ("period_line_ids.period_id", "in", period_ids),
            ], limit=1)
            if conflict:
                conflict_periods = conflict.period_line_ids.mapped("period_id").filtered(
                    lambda p: p.id in period_ids
                ).mapped("name")
                raise ValidationError(
                    _("Hall '%s' is already booked on %s for period(s): %s. Contract: %s")
                    % (
                        rec.hall_id.display_name,
                        rec.booking_date,
                        ", ".join(conflict_periods),
                        conflict.name,
                    )
                )

    def check_availability(self):
        self.ensure_one()
        self._validate_booking_integrity()
        return True

    def action_hold(self):
        for rec in self:
            if not rec.period_line_ids:
                raise ValidationError(_("Select at least one booking period."))
            rec._validate_booking_integrity()
            hours = int(self.env["ir.config_parameter"].sudo().get_param(
                "qimamhd_booking_v2.hold_hours", 24
            ) or 24)
            rec.write({
                "state": "hold",
                "hold_until": fields.Datetime.add(fields.Datetime.now(), hours=hours),
            })

    def action_confirm(self):
        for rec in self:
            rec._validate_booking_integrity()
            policy = rec.company_id.qimam_booking_confirmation_policy or "manual"
            posted_invoices = rec.invoice_ids.filtered(
                lambda m: m.type == "out_invoice" and m.state == "posted"
            )
            if policy == "invoice" and not posted_invoices:
                raise UserError(_("A posted customer invoice is required before confirmation."))
            if policy == "deposit":
                deposit_percent = max(min(rec.company_id.qimam_booking_default_deposit_percent or 0.0, 100.0), 0.0)
                required = rec.currency_id.round(rec.amount_total * deposit_percent / 100.0)
                if rec.amount_paid + rec.currency_id.rounding < required:
                    raise UserError(
                        _("A paid deposit of at least %s %s is required before confirmation.")
                        % (required, rec.currency_id.symbol or rec.currency_id.name)
                    )
            rec.write({"state": "confirmed", "hold_until": False})

    def action_prepare(self):
        self.write({"state": "preparing"})

    def action_start_event(self):
        self.write({"state": "event"})

    def action_complete(self):
        self.write({"state": "completed"})

    def action_reset_draft(self):
        for rec in self:
            if rec.invoice_ids.filtered(lambda m: m.state == "posted"):
                raise UserError(_("A booking with posted invoices cannot be reset to draft."))
            rec.write({"state": "draft", "hold_until": False})

    def action_open_cancel_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Cancel Booking"),
            "res_model": "qimam.booking.cancel.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_booking_id": self.id},
        }

    def action_view_invoices(self):
        self.ensure_one()
        action = self.env.ref("account.action_move_out_invoice_type").read()[0]
        action["domain"] = [("qimam_booking_id", "=", self.id)]
        action["context"] = {"default_qimam_booking_id": self.id, "default_partner_id": self.partner_id.id}
        return action

    def action_create_invoice(self):
        self.ensure_one()
        if self.state not in ("draft", "hold", "confirmed", "preparing", "event", "completed"):
            raise UserError(_("This booking cannot be invoiced in its current state."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Create Booking Invoice"),
            "res_model": "qimam.booking.invoice.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_booking_id": self.id},
        }



    def action_mission_control(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "qimam_mission_control",
            "name": _("Event Mission Control"),
            "context": {"active_id": self.id},
        }

    def action_payment_experience(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "qimam_payment_experience",
            "name": _("Payment & Confirmation"),
            "context": {"active_id": self.id},
        }

    def action_view_payment_schedule(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Payment Schedule"),
            "res_model": "qimam.booking.payment.schedule",
            "view_mode": "tree,form",
            "domain": [("booking_id", "=", self.id)],
            "context": {"default_booking_id": self.id},
        }

    def action_open_payment_schedule_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Build Payment Schedule"),
            "res_model": "qimam.booking.payment.schedule.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_booking_id": self.id},
        }

    def action_open_financial_reversal_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Financial Reversal"),
            "res_model": "qimam.booking.reversal.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_booking_id": self.id},
        }

    def action_reopen_cancelled(self):
        for rec in self:
            if rec.state != "cancelled":
                raise UserError(_("Only a cancelled booking can be reopened."))
            posted = rec.invoice_ids.filtered(lambda m: m.state == "posted")
            if posted:
                raise UserError(_(
                    "This booking still has posted accounting documents. "
                    "Resolve them before reopening the contract."
                ))
            # Lock the same hall/day key used by normal availability validation
            # before inspecting the slot. We do not mutate the cancelled record first.
            self.env.cr.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
                ("branch:%s:hall:%s" % (rec.branch_id.id, rec.hall_id.id), str(rec.booking_date)),
            )
            period_ids = rec.period_line_ids.mapped("period_id").ids
            conflict = self.search([
                ("id", "!=", rec.id),
                ("branch_id", "=", rec.branch_id.id),
                ("hall_id", "=", rec.hall_id.id),
                ("booking_date", "=", rec.booking_date),
                ("state", "in", BLOCKING_STATES),
                ("period_line_ids.period_id", "in", period_ids),
            ], limit=1)
            if conflict:
                raise UserError(_(
                    "The booking cannot be reopened because the hall/date/period is now occupied by %s."
                ) % conflict.name)
            rec.write({
                "state": "draft",
                "cancellation_reason": False,
                "cancelled_by": False,
                "cancelled_at": False,
            })
        return True


    @api.model
    def cron_release_expired_holds(self):
        now = fields.Datetime.now()
        expired = self.search([
            ("state", "=", "hold"),
            ("hold_until", "!=", False),
            ("hold_until", "<=", now),
        ])
        for booking in expired:
            posted = booking.invoice_ids.filtered(lambda m: m.state == "posted")
            if posted:
                booking.message_post(body=_(
                    "Temporary hold expired, but the slot was not released because posted accounting documents exist."
                ))
                continue
            drafts = booking.invoice_ids.filtered(lambda m: m.state == "draft")
            if drafts:
                drafts.button_cancel()
            booking.write({
                "state": "cancelled",
                "cancellation_reason": _("Temporary hold expired automatically."),
                "cancelled_by": False,
                "cancelled_at": now,
                "hold_until": False,
            })
        return True


class BookingPeriodLine(models.Model):
    _name = "qimam.booking.period.line"
    _description = "Booked Period"
    _order = "id"

    booking_id = fields.Many2one(
        "qimam.booking", required=True, ondelete="cascade", index=True
    )
    period_id = fields.Many2one(
        "qimam.booking.period", required=True, ondelete="restrict", index=True
    )
    company_id = fields.Many2one(related="booking_id.company_id", store=True, index=True)
    branch_id = fields.Many2one(related="booking_id.branch_id", store=True, index=True)

    _sql_constraints = [
        ("booking_period_uniq", "unique(booking_id, period_id)", "Period is already selected."),
    ]

    @api.constrains("period_id")
    def _check_period_company(self):
        for rec in self:
            if rec.period_id.company_id != rec.booking_id.company_id:
                raise ValidationError(_("Booking period must belong to the booking company."))
            rec.booking_id._validate_booking_integrity()


class BookingServiceLine(models.Model):
    _name = "qimam.booking.service.line"
    _description = "Booking Service Line"

    booking_id = fields.Many2one("qimam.booking", required=True, ondelete="cascade")
    service_id = fields.Many2one("qimam.booking.service", required=True)
    quantity = fields.Float(default=1.0, required=True)
    price_unit = fields.Monetary(currency_field="currency_id")
    tax_ids = fields.Many2many("account.tax", domain=[("type_tax_use", "=", "sale")])
    currency_id = fields.Many2one(related="booking_id.currency_id", readonly=True)
    branch_id = fields.Many2one(related="booking_id.branch_id", store=True, index=True)

    @api.onchange("service_id")
    def _onchange_service_id(self):
        if self.service_id:
            self.price_unit = self.service_id.price
            self.tax_ids = self.service_id.tax_ids

    @api.constrains("quantity", "price_unit")
    def _check_values(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError(_("Quantity must be greater than zero."))
            if rec.price_unit < 0:
                raise ValidationError(_("Price cannot be negative."))
            if rec.service_id.branch_id != rec.booking_id.branch_id:
                raise ValidationError(_("Service must belong to the booking branch."))
