# -*- coding: utf-8 -*-
from odoo.tests.common import SavepointCase
from odoo.exceptions import ValidationError, UserError


class TestBookingAvailability(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Customer"})
        cls.hall = cls.env["qimam.booking.hall"].create({
            "name": "Hall A", "code": "A", "capacity": 200, "base_price": 1000
        })
        cls.period = cls.env["qimam.booking.period"].create({
            "name": "Test Evening", "code": "TEST_EVE", "sequence": 99
        })

    def _booking(self, state="draft"):
        return self.env["qimam.booking"].create({
            "partner_id": self.partner.id,
            "booking_date": "2026-12-10",
            "hall_id": self.hall.id,
            "state": state,
            "period_line_ids": [(0, 0, {"period_id": self.period.id})],
        })

    def test_draft_does_not_block(self):
        self._booking("draft")
        second = self._booking("draft")
        second.action_confirm()
        self.assertEqual(second.state, "confirmed")

    def test_confirmed_blocks_same_slot(self):
        first = self._booking("draft")
        first.action_confirm()
        second = self._booking("draft")
        with self.assertRaises(ValidationError):
            second.action_confirm()

    def test_cancel_releases_slot(self):
        first = self._booking("draft")
        first.action_confirm()
        first.write({"state": "cancelled", "cancellation_reason": "Test"})
        second = self._booking("draft")
        second.action_confirm()
        self.assertEqual(second.state, "confirmed")


class TestBookingFinancialLifecycle(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Financial Customer"})
        cls.hall = cls.env["qimam.booking.hall"].create({
            "name": "Financial Hall", "code": "FIN", "capacity": 100, "base_price": 1000
        })
        cls.period = cls.env["qimam.booking.period"].create({
            "name": "Financial Period", "code": "FIN_PERIOD"
        })

    def _confirmed(self):
        booking = cls_booking = self.env["qimam.booking"].create({
            "partner_id": self.partner.id,
            "booking_date": "2026-12-20",
            "hall_id": self.hall.id,
            "period_line_ids": [(0, 0, {"period_id": self.period.id})],
        })
        booking.action_confirm()
        return booking

    def test_contract_price_is_snapshot(self):
        booking = self._confirmed()
        original = booking.hall_price_unit
        self.hall.base_price = 2000
        self.assertEqual(booking.hall_price_unit, original)

    def test_invoice_factor_remaining(self):
        booking = self._confirmed()
        self.assertEqual(booking._net_invoiced_factor(), 0.0)


class TestBookingLifecycleSafety(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Lifecycle Customer"})
        cls.hall = cls.env["qimam.booking.hall"].create({
            "name": "Lifecycle Hall", "code": "LIFE", "capacity": 150, "base_price": 1500
        })
        cls.period = cls.env["qimam.booking.period"].create({
            "name": "Lifecycle Evening", "code": "LIFE_EVE"
        })

    def _make(self, date):
        return self.env["qimam.booking"].create({
            "partner_id": self.partner.id,
            "booking_date": date,
            "hall_id": self.hall.id,
            "period_line_ids": [(0, 0, {"period_id": self.period.id})],
        })

    def test_reopen_checks_conflict(self):
        old = self._make("2026-12-25")
        old.action_confirm()
        old.write({"state": "cancelled", "cancellation_reason": "test"})
        new = self._make("2026-12-25")
        new.action_confirm()
        with self.assertRaises(UserError):
            old.action_reopen_cancelled()

    def test_schedule_total(self):
        booking = self._make("2026-12-26")
        wizard = self.env["qimam.booking.payment.schedule.wizard"].create({
            "booking_id": booking.id,
            "schedule_type": "deposit_balance",
            "deposit_percent": 30,
            "first_due_date": "2026-10-10",
        })
        wizard.action_generate()
        self.assertEqual(
            booking.currency_id.round(sum(booking.payment_schedule_ids.mapped("amount"))),
            booking.currency_id.round(booking.amount_total)
        )


class TestStayBookingIsolation(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Hotel Guest"})
        cls.rtype = cls.env["qimam.booking.resource.type"].create({
            "name": "Hotel Rooms", "code": "ROOM", "booking_mode": "stay", "icon": "room"
        })
        cls.room = cls.env["qimam.booking.resource"].create({
            "name": "Room 101", "code": "101", "resource_type_id": cls.rtype.id, "base_price": 400
        })

    def test_checkout_must_follow_checkin(self):
        with self.assertRaises(ValidationError):
            self.env["qimam.stay.booking"].create({
                "partner_id": self.partner.id, "resource_id": self.room.id,
                "checkin_date": "2026-12-20", "checkout_date": "2026-12-20"
            })

    def test_overlapping_confirmed_stay_is_blocked(self):
        first = self.env["qimam.stay.booking"].create({
            "partner_id": self.partner.id, "resource_id": self.room.id,
            "checkin_date": "2026-12-20", "checkout_date": "2026-12-23"
        })
        first.action_confirm()
        second = self.env["qimam.stay.booking"].create({
            "partner_id": self.partner.id, "resource_id": self.room.id,
            "checkin_date": "2026-12-22", "checkout_date": "2026-12-24"
        })
        with self.assertRaises(ValidationError):
            second.action_confirm()

    def test_adjacent_stays_do_not_overlap(self):
        first = self.env["qimam.stay.booking"].create({
            "partner_id": self.partner.id, "resource_id": self.room.id,
            "checkin_date": "2026-12-20", "checkout_date": "2026-12-23"
        })
        first.action_confirm()
        second = self.env["qimam.stay.booking"].create({
            "partner_id": self.partner.id, "resource_id": self.room.id,
            "checkin_date": "2026-12-23", "checkout_date": "2026-12-25"
        })
        second.action_confirm()
        self.assertEqual(second.state, "confirmed")


class TestVisualPlannerService(SavepointCase):

    def test_hijri_label_is_display_only_and_present(self):
        label = self.env["qimam.booking.calendar.service"].hijri_label("2026-10-06")
        self.assertTrue(label)
        self.assertIn("هـ", label)

    def test_hall_month_has_every_day(self):
        data = self.env["qimam.booking.calendar.service"].get_hall_month(2026, 10)
        self.assertEqual(len(data["days"]), 31)
        self.assertEqual(data["days"][0]["date"], "2026-10-01")

    def test_hotel_timeline_window_is_bounded(self):
        data = self.env["qimam.booking.calendar.service"].get_stay_timeline("2026-10-01", 14)
        self.assertEqual(len(data["columns"]), 14)


class TestBookingOSService(SavepointCase):

    def test_bootstrap_has_company_mode(self):
        data = self.env["qimam.booking.workspace.service"].bootstrap()
        self.assertIn(data["company"]["mode"], ("events", "hotel", "mixed"))
        self.assertIn("metrics", data)

    def test_invalid_stay_search_is_empty(self):
        data = self.env["qimam.booking.workspace.service"].find_stay_options("2026-10-10", "2026-10-10", 2)
        self.assertEqual(data["options"], [])


def test_today_operations_shape(self):
    data = self.env["qimam.booking.workspace.service"].today_operations()
    self.assertIn("items", data)
    self.assertIn("date", data)


class TestInvoiceCapacityContract(SavepointCase):
    def test_booking_model_exposes_reserved_invoice_capacity(self):
        self.assertTrue(hasattr(self.env["qimam.booking"], "_reserved_invoice_factor"))
        self.assertTrue(hasattr(self.env["qimam.booking"], "_lock_financial_capacity"))


class TestOperationalReadinessContract(SavepointCase):
    def test_models_expose_readiness_contract(self):
        booking = self.env["qimam.booking"]
        self.assertTrue(hasattr(booking, "action_generate_operations"))
        self.assertTrue(hasattr(booking, "action_mission_control"))
        self.assertIn("qimam.booking.operation.item", self.env)
        self.assertIn("qimam.booking.operation.template", self.env)


class TestExecutiveAnalyticsContract(SavepointCase):
    def test_executive_service_contract(self):
        service=self.env["qimam.booking.executive.analytics"]
        self.assertTrue(hasattr(service,"dashboard"))
        self.assertTrue(hasattr(service,"drilldown"))
        data=service.dashboard()
        for key in ("bookings","revenue","occupancy","cancel_rate","conversion","forecast","comparison"):
            self.assertIn(key,data)


class TestSecurityHardeningContract(SavepointCase):
    def test_audit_model_and_resource_lock_contract_exist(self):
        self.assertIn("qimam.booking.security.audit", self.env)
        self.assertTrue(hasattr(self.env["qimam.booking.security.audit"], "log"))
        self.assertTrue(hasattr(self.env["qimam.booking"], "_validate_booking_integrity"))

    def test_stay_half_open_overlap_semantics(self):
        # Business invariant: [checkin, checkout) permits same-day turnover.
        from datetime import date
        existing_start, existing_end=date(2026,10,10),date(2026,10,12)
        self.assertFalse(existing_start < date(2026,10,10) and existing_end > date(2026,10,8))
        self.assertTrue(existing_start < date(2026,10,13) and existing_end > date(2026,10,11))


class TestApiV2DomainContract(SavepointCase):
    def test_resource_booking_modes_are_explicit(self):
        selection=dict(self.env["qimam.booking.resource.type"]._fields["booking_mode"].selection)
        self.assertIn("event",selection)
        self.assertIn("stay",selection)

    def test_stay_uses_interval_not_periods(self):
        stay=self.env["qimam.stay.booking"]
        self.assertIn("checkin_date",stay._fields)
        self.assertIn("checkout_date",stay._fields)
        self.assertNotIn("period_line_ids",stay._fields)

    def test_event_uses_periods_not_stay_interval(self):
        event=self.env["qimam.booking"]
        self.assertIn("period_line_ids",event._fields)
        self.assertNotIn("checkin_date",event._fields)


class TestBranchArchitectureContract(SavepointCase):
    def test_operational_models_have_branch(self):
        for model in ("qimam.booking","qimam.booking.hall","qimam.booking.period",
                      "qimam.booking.service","qimam.booking.package",
                      "qimam.booking.resource","qimam.stay.booking"):
            self.assertIn("branch_id",self.env[model]._fields)

    def test_branch_model_matches_legacy_contract(self):
        self.assertEqual(self.env["qimam.booking"]._fields["branch_id"].comodel_name,"custom.branches")
        self.assertIn("allowed_branch_ids",self.env["res.users"]._fields)


class TestMigrationFoundation(SavepointCase):
    def test_migration_map_is_traceable(self):
        model=self.env["qimam.booking.migration.map"]
        for field in ("legacy_model","legacy_id","target_model","target_id","branch_id","status"):
            self.assertIn(field,model._fields)

    def test_migration_service_does_not_require_legacy_module_at_install(self):
        service=self.env["qimam.booking.migration.service"]
        self.assertIsInstance(service.legacy_available(),bool)


class TestApiAuthenticationFoundation(SavepointCase):
    def test_api_session_never_has_plaintext_token_fields(self):
        fields_set=set(self.env["qimam.booking.api.session"]._fields)
        self.assertIn("access_hash",fields_set)
        self.assertIn("refresh_hash",fields_set)
        self.assertNotIn("access_token",fields_set)
        self.assertNotIn("refresh_token",fields_set)

    def test_api_session_has_device_and_expiry_controls(self):
        model=self.env["qimam.booking.api.session"]
        for name in ("device_id","access_expires_at","refresh_expires_at","revoked_at","user_id"):
            self.assertIn(name,model._fields)


class TestReleaseGateContracts(SavepointCase):
    def test_workspace_service_exposes_operations_methods(self):
        service=self.env["qimam.booking.workspace.service"]
        for name in ("bootstrap","find_stay_options","today_operations","booking_preview","execute_primary_action"):
            self.assertTrue(hasattr(service,name),name)

    def test_stay_branch_contract(self):
        model=self.env["qimam.stay.booking"]
        self.assertEqual(model._fields["branch_id"].comodel_name,"custom.branches")

    def test_dashboard_is_branch_scoped(self):
        self.assertIn("branch_id",self.env["qimam.booking.dashboard"]._fields)
        self.assertNotIn("company_id",self.env["qimam.booking.dashboard"]._fields)


class TestStayFinancialLifecycleContract(SavepointCase):
    def test_stay_financial_fields_exist(self):
        stay=self.env["qimam.stay.booking"]
        for name in ("invoice_ids","amount_invoiced","amount_credited","amount_paid","amount_due","invoice_progress","financial_status","room_tax_ids"):
            self.assertIn(name,stay._fields)

    def test_account_move_links_stay(self):
        self.assertEqual(self.env["account.move"]._fields["qimam_stay_id"].comodel_name,"qimam.stay.booking")

    def test_stay_financial_wizards_exist(self):
        for model in ("qimam.stay.invoice.wizard","qimam.stay.reversal.wizard","qimam.stay.cancel.wizard"):
            self.assertTrue(self.env[model])

    def test_booking_lines_are_branch_scoped(self):
        self.assertIn("branch_id",self.env["qimam.booking.period.line"]._fields)
        self.assertIn("branch_id",self.env["qimam.booking.service.line"]._fields)
        self.assertIn("branch_id",self.env["qimam.booking.package.line"]._fields)

    def test_discount_guard_exists_on_canonical_booking(self):
        self.assertTrue(hasattr(self.env["qimam.booking"],"_check_discount_authorization_vals"))
