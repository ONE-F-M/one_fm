# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Employee Traceability Matrix server half.

Run with ``--skip-before-tests``. classify() and can_be_permanent() are pure, so most of
this needs no records at all.
"""

from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

# Imported before any test patches driver_employees: these modules bind it by name at
# import time, and a first import under a patch would keep the mock for the whole run.
from one_fm.one_fm.doctype.transportation_shipment import shipment_generator  # noqa: F401
from one_fm.one_fm.page.transportation_schedule import traceability_matrix as tm
from one_fm.one_fm.page.transportation_schedule.traceability_matrix import (
	MATRIX_ROLES,
	PERMANENT_WARNING,
	add_employee_to_shipment,
	create_shipment_for_employee,
	_missing_reason,
	_roster_row,
	_time_text,
	can_be_permanent,
	classify,
	get_traceability_matrix,
)

ROW_KEYS = {
	"id", "name", "designation", "operations_role", "project", "master_shift", "roster_shift", "roster_start",
	"roster_end", "camp", "room", "is_reliever", "reliever_name", "status", "badge_text",
	"subtext", "can_be_permanent", "legs",
}


def _ctx(**overrides):
	"""An active camp resident with a Working row and nothing else - the Missing case."""
	ctx = {
		"employee_status": "Active",
		"card": None,
		"card_status": None,
		"placement": None,
		"has_in": True,
		"checked_out": False,
		"on_leave": False,
		"availabilities": ["Working"],
		"is_driver": False,
	}
	ctx.update(overrides)
	return ctx


class TestClassify(FrappeTestCase):
	def test_assigned_to_a_live_vehicle(self):
		result = classify(_ctx(
			card="TSHIP-1", card_status="Assigned",
			placement={"vehicle_label": "VHL-0005 (Coaster)", "trip_id": "S-503"},
		))
		self.assertEqual(result["status"], "Assigned")
		self.assertEqual(result["badge_text"], "VHL-0005 (Coaster) · Trip S-503")

	def test_assigned_card_with_no_placement_in_the_plan_is_still_assigned(self):
		result = classify(_ctx(card="TSHIP-1", card_status="Assigned"))
		self.assertEqual(result["status"], "Assigned")

	def test_staged_in_the_unassigned_pool(self):
		result = classify(_ctx(card="TSHIP-POOL-0001", card_status="Unassigned"))
		self.assertEqual(result["status"], "Pool")
		self.assertEqual(result["badge_text"], "Unassigned Pool · TSHIP-POOL-0001")

	def test_missing_from_card(self):
		result = classify(_ctx())
		self.assertEqual(result["status"], "Missing")
		self.assertEqual(result["badge_text"], "MISSING FROM CARD")
		self.assertEqual(result["subtext"], "Eligible, but no shipment generated")

	def test_missing_carries_a_known_reason(self):
		result = classify(_ctx(missing_reason="Relieving Ann, but no shipment generated"))
		self.assertEqual(result["status"], "Missing")
		self.assertEqual(result["subtext"], "Relieving Ann, but no shipment generated")

	def test_stale_when_inactive_employee_is_on_a_card(self):
		result = classify(_ctx(employee_status="Left", card="TSHIP-1", card_status="Assigned"))
		self.assertEqual(result["status"], "Stale")
		self.assertEqual(result["badge_text"], "STALE BLOCK DETECTED")

	def test_stale_when_rider_has_no_in_row(self):
		result = classify(_ctx(has_in=False, card="TSHIP-1", card_status="Unassigned"))
		self.assertEqual(result["status"], "Stale")

	def test_stale_when_rider_has_checked_out(self):
		result = classify(_ctx(checked_out=True, card="TSHIP-1", card_status="Assigned"))
		self.assertEqual(result["status"], "Stale")

	def test_stale_beats_assigned(self):
		result = classify(_ctx(
			employee_status="Inactive", card="TSHIP-1", card_status="Assigned",
			placement={"vehicle_label": "V", "trip_id": "1"},
		))
		self.assertEqual(result["status"], "Stale")

	def test_no_open_in_is_live_out_exempt(self):
		for ctx in (_ctx(has_in=False), _ctx(checked_out=True)):
			result = classify(ctx)
			self.assertEqual(result["status"], "Exempt")
			self.assertEqual(result["badge_text"], "Self-Commuting / Exempt")
			self.assertEqual(result["subtext"], "Live-Out")

	def test_leave_is_exempt_on_leave(self):
		result = classify(_ctx(on_leave=True))
		self.assertEqual(result["status"], "Exempt")
		self.assertEqual(result["badge_text"], "No seat needed (on leave)")

	def test_day_off_and_client_day_off_are_exempt_on_leave(self):
		for availability in ("Day Off", "Client Day Off"):
			result = classify(_ctx(availabilities=[availability]))
			self.assertEqual(result["status"], "Exempt")
			self.assertEqual(result["badge_text"], "No seat needed (on leave)")

	def test_no_working_row_is_exempt_on_leave(self):
		result = classify(_ctx(availabilities=[]))
		self.assertEqual(result["status"], "Exempt")
		self.assertEqual(result["badge_text"], "No seat needed (on leave)")

	def test_driver_is_exempt(self):
		result = classify(_ctx(is_driver=True))
		self.assertEqual(result["status"], "Exempt")


class TestCanBePermanent(FrappeTestCase):
	def _row(self, shift="SHIFT-A", availability="Working", roster_type="Basic", relieving=0):
		return {
			"shift": shift, "employee_availability": availability,
			"roster_type": roster_type, "is_relieving_schedule": relieving,
		}

	def test_true_when_the_one_working_row_matches_the_master_shift(self):
		self.assertTrue(can_be_permanent([self._row()], "SHIFT-A"))

	def test_false_when_the_shift_differs_from_the_master(self):
		self.assertFalse(can_be_permanent([self._row("SHIFT-B")], "SHIFT-A"))

	def test_false_for_a_reliever(self):
		self.assertFalse(can_be_permanent([self._row(relieving=1)], "SHIFT-A"))

	def test_false_for_over_time_only(self):
		self.assertFalse(can_be_permanent([self._row(roster_type="Over-Time")], "SHIFT-A"))

	def test_extra_over_time_row_keeps_basic_eligibility(self):
		rows = [self._row(), self._row("SHIFT-B", roster_type="Over-Time")]
		self.assertTrue(can_be_permanent(rows, "SHIFT-A"))

	def test_over_time_row_on_master_shift_does_not_grant_eligibility(self):
		rows = [self._row("SHIFT-B"), self._row(roster_type="Over-Time")]
		self.assertFalse(can_be_permanent(rows, "SHIFT-A"))

	def test_false_with_two_basic_working_rows(self):
		self.assertFalse(can_be_permanent([self._row(), self._row("SHIFT-B")], "SHIFT-A"))

	def test_false_with_no_working_row_or_no_master_shift(self):
		self.assertFalse(can_be_permanent([self._row(availability="Day Off")], "SHIFT-A"))
		self.assertFalse(can_be_permanent([self._row()], None))


class TestRosterHelpers(FrappeTestCase):
	def test_basic_working_row_is_the_rostered_shift_over_over_time(self):
		rows = [
			{"shift": "OT", "employee_availability": "Working", "roster_type": "Over-Time"},
			{"shift": "BASIC", "employee_availability": "Working", "roster_type": "Basic"},
		]
		self.assertEqual(_roster_row(rows)["shift"], "BASIC")

	def test_missing_reason(self):
		self.assertIn("Ann", _missing_reason({"relieving_employee": "E1"}, "Ann", "A", "B"))
		self.assertIsNone(_missing_reason({}, None, "A", "B"))
		self.assertIsNone(_missing_reason({}, None, "A", "A"))

	def test_no_working_row_gives_none(self):
		self.assertIsNone(_roster_row([{"employee_availability": "Day Off", "roster_type": "Basic"}]))

	def test_midnight_is_a_stated_time(self):
		from datetime import timedelta

		self.assertEqual(_time_text(timedelta(0)), "00:00:00")
		self.assertEqual(_time_text(timedelta(hours=9)), "09:00:00")
		self.assertIsNone(_time_text(None))


class TestEndpoint(FrappeTestCase):
	def setUp(self):
		self._in_test = frappe.flags.in_test

	def tearDown(self):
		frappe.flags.in_test = self._in_test
		frappe.set_user("Administrator")

	def test_the_roles_are_the_agreed_ones(self):
		self.assertEqual(
			MATRIX_ROLES, ("Transportation Supervisor", "Transportation Manager", "System Manager")
		)

	def test_a_user_without_the_roles_is_refused(self):
		# frappe.only_for returns at once while frappe.flags.in_test is set
		frappe.flags.in_test = False
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			get_traceability_matrix()
		with self.assertRaises(frappe.PermissionError):
			add_employee_to_shipment("TS-X", "HR-EMP-X", "Today Only")
		with self.assertRaises(frappe.PermissionError):
			create_shipment_for_employee("HR-EMP-X", "LOC", "Outward", "Today Only")

	def test_an_authorised_user_gets_the_agreed_shape(self):
		result = get_traceability_matrix()

		logged = frappe.get_all(
			"Error Log", fields=["error"],
			order_by="creation desc", limit_page_length=1,
		)
		detail = (logged[0].error[-1500:] if logged else "") if result.get("status") == "error" else ""
		self.assertNotEqual(result.get("status"), "error", detail)
		self.assertIsInstance(result["rows"], list)
		self.assertTrue(result["synced_at"])
		if result["rows"]:
			self.assertEqual(ROW_KEYS - set(result["rows"][0]), set())


def _free_employee():
	"""An Active non-driver employee on no shipment card."""
	from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import driver_employees

	riding = set(frappe.get_all(
		"Transportation Shipment Employee", filters={"parenttype": "Transportation Shipment"}, pluck="employee_id"
	))
	candidates = [
		e for e in frappe.get_all("Employee", filters={"status": "Active"}, pluck="name", limit_page_length=200)
		if e not in riding
	]
	drivers = driver_employees(candidates)
	return next((e for e in candidates if e not in drivers), None)


class TestAddEmployeeToShipment(FrappeTestCase):
	def setUp(self):
		self.employee = _free_employee()
		if not self.employee:
			self.skipTest("no free Active employee on this site")

	def tearDown(self):
		frappe.db.rollback()

	def _card(self, status="Unassigned", direction="Outward"):
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = status
		doc.trip_direction = direction
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def _rows(self, card):
		return frappe.get_all(
			"Transportation Shipment Employee",
			filters={"parent": card},
			fields=["employee_id", "assignment_scope", "assigned_on"],
		)

	def test_a_pool_card_takes_the_rider_without_a_seat_check(self):
		card = self._card()
		with patch(
			"one_fm.one_fm.doctype.transportation_shipment.shipment_generator._SeatCheck.room"
		) as room:
			result = add_employee_to_shipment(f"TSHIP-{card}", self.employee, "Today Only")

		room.assert_not_called()
		self.assertEqual(result["headcount"], 1)
		self.assertEqual(result["card_id"], f"TSHIP-{card}")
		rows = self._rows(card)
		self.assertEqual(rows[0].assignment_scope, "Today Only")
		self.assertEqual(getdate(rows[0].assigned_on), getdate(today()))

	def test_a_full_placed_card_answers_over_capacity_and_writes_nothing(self):
		card = self._card(status="Assigned")
		load = {"vehicle": "V-1", "limit": 1, "load": 1}
		with patch(
			"one_fm.one_fm.doctype.transportation_shipment.shipment_generator._SeatCheck.room", return_value=0
		), patch.object(tm, "_vehicle_load", return_value=load):
			result = add_employee_to_shipment(card, self.employee, "Today Only")
			self.assertTrue(result["over_capacity"])
			self.assertEqual(result["limit"], 1)
			self.assertEqual(self._rows(card), [])

			result = add_employee_to_shipment(card, self.employee, "Today Only", override=1)

		self.assertEqual(result["headcount"], 1)
		self.assertEqual(len(self._rows(card)), 1)

	def test_a_placed_card_with_room_takes_the_rider(self):
		card = self._card(status="Assigned")
		with patch(
			"one_fm.one_fm.doctype.transportation_shipment.shipment_generator._SeatCheck.room", return_value=1
		):
			result = add_employee_to_shipment(card, self.employee, "Today Only")
		self.assertEqual(result["status"], "Assigned")
		self.assertEqual(result["headcount"], 1)

	def test_permanent_on_a_mismatched_shift_is_refused(self):
		card = self._card()
		with patch.object(tm, "can_be_permanent", return_value=False):
			with self.assertRaises(frappe.ValidationError) as caught:
				add_employee_to_shipment(card, self.employee, "Permanent")
		self.assertIn(PERMANENT_WARNING, str(caught.exception))
		self.assertEqual(self._rows(card), [])

	def test_permanent_on_a_matching_shift_is_allowed(self):
		card = self._card()
		with patch.object(tm, "can_be_permanent", return_value=True):
			add_employee_to_shipment(card, self.employee, "Permanent")
		self.assertEqual(self._rows(card)[0].assignment_scope, "Permanent")

	def test_a_second_card_in_the_same_direction_is_refused(self):
		first, second, back = self._card(), self._card(), self._card(direction="Return")
		add_employee_to_shipment(first, self.employee, "Today Only")
		with self.assertRaises(frappe.ValidationError):
			add_employee_to_shipment(second, self.employee, "Today Only")
		add_employee_to_shipment(back, self.employee, "Today Only")
		self.assertEqual(len(self._rows(back)), 1)

	def _merge(self, card, own):
		frappe.db.set_value(
			"Transportation Shipment", card, {"trip_direction": "Mixed", "pre_merge_trip_direction": own}
		)

	def test_merged_cards_keep_their_own_direction_in_the_matrix(self):
		outward, back = self._card(), self._card(direction="Return")
		add_employee_to_shipment(outward, self.employee, "Today Only")
		add_employee_to_shipment(back, self.employee, "Today Only")
		self._merge(outward, "Outward")
		self._merge(back, "Return")

		row = next(r for r in get_traceability_matrix()["rows"] if r["id"] == self.employee)
		legs = {leg["card"]: leg for leg in row["legs"]}
		self.assertEqual(legs[f"TSHIP-{outward}"]["own_direction"], "OUTBOUND")
		self.assertEqual(legs[f"TSHIP-{back}"]["own_direction"], "RETURN")
		self.assertEqual(legs[f"TSHIP-{back}"]["direction"], "Mixed")

		with self.assertRaises(frappe.ValidationError):
			add_employee_to_shipment(self._card(direction="Return"), self.employee, "Today Only")

	def test_a_driver_is_refused(self):
		card = self._card()
		with patch(
			"one_fm.one_fm.doctype.transportation_shipment.transportation_shipment.driver_employees",
			return_value={self.employee},
		):
			with self.assertRaises(frappe.ValidationError):
				add_employee_to_shipment(card, self.employee, "Today Only")

	def test_an_inactive_card_and_another_day_are_refused(self):
		card = self._card(status="Inactive")
		with self.assertRaises(frappe.ValidationError):
			add_employee_to_shipment(card, self.employee, "Today Only")
		with self.assertRaises(frappe.ValidationError):
			add_employee_to_shipment(self._card(), self.employee, "Today Only", date=add_days(today(), 1))


class TestCreateShipmentForEmployee(FrappeTestCase):
	def setUp(self):
		self.employee = _free_employee()
		self.stop = frappe.db.get_value("Location", {"location_type": "Stop Location"}, "name")
		self.acc = frappe.db.get_value("Accommodation", {}, "name")
		self.shift = frappe.db.get_value(
			"Operations Shift", {"status": "Active"}, ["name", "start_time", "end_time", "site", "project"], as_dict=True
		)
		if not (self.employee and self.stop and self.acc and self.shift):
			self.skipTest("needs an employee, a Stop Location, an Accommodation and an Operations Shift")
		checkin = frappe._dict(accommodation=self.acc, checked_out=0)
		for target, value in (
			("_latest_checkins", {self.employee: checkin}),
			("_roster_row", {"shift": self.shift.name}),
		):
			patcher = patch.object(tm, target, return_value=value)
			patcher.start()
			self.addCleanup(patcher.stop)

	def tearDown(self):
		frappe.db.rollback()

	def _create(self, **kwargs):
		args = dict(employee=self.employee, stop_location=self.stop, direction="Outward", scope="Today Only")
		args.update(kwargs)
		return create_shipment_for_employee(**args)

	def test_header_and_rider_are_prefilled(self):
		result = self._create()
		doc = frappe.get_doc("Transportation Shipment", result["card_id"][len("TSHIP-"):])

		self.assertEqual(doc.status, "Unassigned")
		self.assertEqual(doc.accommodation, self.acc)
		self.assertEqual(doc.stop_location, self.stop)
		self.assertEqual(doc.operations_shift, self.shift.name)
		self.assertEqual(str(doc.start_time), str(self.shift.start_time))
		self.assertEqual(str(doc.end_time), str(self.shift.end_time))
		self.assertEqual(doc.routing_type_badge, "Direct")
		self.assertEqual(doc.trip_direction, "Outward")
		self.assertTrue(doc.is_adhoc_journey)
		self.assertFalse(doc.source_doctype)
		self.assertEqual(getdate(doc.from_date), getdate(today()))
		self.assertEqual(getdate(doc.to_date), getdate(today()))
		self.assertEqual(doc.headcount, 1)
		row = doc.transportation_shipment_employee[0]
		self.assertEqual((row.employee_id, row.assignment_scope), (self.employee, "Today Only"))

	def test_a_location_that_is_not_a_stop_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self._create(stop_location="NOT-A-STOP-LOCATION-XYZ")

	def test_a_today_only_card_is_retired_the_next_day(self):
		from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
			deactivate_expired_shipments,
		)

		name = self._create()["card_id"][len("TSHIP-"):]
		with patch.object(frappe.db, "commit"):
			deactivate_expired_shipments(as_of=add_days(today(), 1))
		self.assertEqual(frappe.db.get_value("Transportation Shipment", name, "status"), "Inactive")

	def test_the_generator_never_claims_it_and_the_canvas_renders_it(self):
		from one_fm.one_fm.doctype.transportation_shipment import shipment_generator as gen
		from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
			_build_transportation_shipment_cards,
		)

		name = self._create(scope="Today Only")["card_id"][len("TSHIP-"):]
		self.assertNotIn(name, gen._live_cards())

		cards = _build_transportation_shipment_cards(
			lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
			lambda t: frappe.utils.get_datetime(f"{today()} {t}"),
			lambda doctype, docname: None,
			timedelta,
		)
		card = next((c for c in cards if c["shipment"] == name), None)
		self.assertIsNotNone(card)
		self.assertEqual(card["headcount"], 1)
		self.assertEqual(card["shift_name"], self.shift.name)


class TestRemovingRiders(FrappeTestCase):
	"""Remove from Card, the empty-card choice, cancelling and Clear All Stale Blocks."""

	def setUp(self):
		riding = set(frappe.get_all(
			"Transportation Shipment Employee", filters={"parenttype": "Transportation Shipment"}, pluck="employee_id"
		))
		self.emps = [
			e for e in frappe.get_all("Employee", filters={"status": "Active"}, pluck="name", limit_page_length=200)
			if e not in riding
		][:3]
		if len(self.emps) < 3:
			self.skipTest("needs three Active employees on no card")
		self._in_test = frappe.flags.in_test

	def tearDown(self):
		frappe.flags.in_test = self._in_test
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def _card(self, riders, direction="Outward", status="Unassigned", pair_group=None):
		doc = frappe.new_doc("Transportation Shipment")
		doc.status = status
		doc.trip_direction = direction
		doc.routing_type_badge = "Direct"
		doc.pair_group = pair_group
		for emp in riders:
			doc.append("transportation_shipment_employee", {"employee_id": emp, "employee_name": emp})
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def _place(self, card, headcount):
		plan = frappe.new_doc("Route Plan")
		plan.title = frappe.generate_hash("RP-TM", 8)
		plan.status = "Draft"
		plan.effective_from = today()
		plan.append("assignments", {
			"card_id": f"TSHIP-{card}", "transportation_shipment": card,
			"vehicle": "VHL-0005", "direction": "OUTBOUND", "headcount": headcount,
			"start_time": f"{today()}T06:00:00Z", "end_time": f"{today()}T07:00:00Z",
		})
		plan.flags.ignore_mandatory = True
		plan.flags.ignore_links = True
		plan.insert(ignore_permissions=True)
		return plan.name, plan.assignments[0].name

	def _depart(self, card):
		manifest = frappe.generate_hash("TM-TEST", 10)
		frappe.get_doc({
			"doctype": "Transportation Manifest", "name": manifest, "schedule_date": today(),
		}).db_insert()
		frappe.get_doc({
			"doctype": "Transportation Manifest Details", "name": frappe.generate_hash("TMD", 10),
			"parent": manifest, "parenttype": "Transportation Manifest",
			"parentfield": "transportation_manifest_details",
			"transportation_shipment": card, "employee": self.emps[0], "attendance_status": "Present",
		}).db_insert()

	def _riders(self, card):
		return frappe.get_all(
			"Transportation Shipment Employee", filters={"parent": card}, pluck="employee_id", order_by="idx asc"
		)

	def _comments(self, card):
		return frappe.db.count(
			"Comment",
			{"reference_doctype": "Transportation Shipment", "reference_name": card, "comment_type": "Info"},
		)

	def _status(self, card):
		return frappe.db.get_value("Transportation Shipment", card, "status")

	def test_one_leg_then_both_drops_a_seat_per_leg(self):
		a, b, c = self.emps
		out = self._card([a, b, c])
		back = self._card([a, b, c], direction="Return")
		_plan, out_row = self._place(out, 3)
		_plan, back_row = self._place(back, 3)

		result = tm.remove_from_cards(f'["{a}"]', f'["TSHIP-{out}"]', "Other")
		self.assertEqual(result["headcounts"], {f"TSHIP-{out}": 2})
		self.assertEqual(self._riders(out), [b, c])
		self.assertEqual(self._riders(back), [a, b, c])
		self.assertEqual(frappe.db.get_value("Route Plan Assignment", out_row, "headcount"), 2)
		self.assertEqual(frappe.db.get_value("Route Plan Assignment", back_row, "headcount"), 3)

		tm.remove_from_cards(f'["{b}"]', f'["TSHIP-{out}", "TSHIP-{back}"]', "Other")
		self.assertEqual(self._riders(out), [c])
		self.assertEqual(self._riders(back), [a, c])
		self.assertEqual(frappe.db.get_value("Route Plan Assignment", out_row, "headcount"), 1)
		self.assertEqual(frappe.db.get_value("Route Plan Assignment", back_row, "headcount"), 2)
		self.assertEqual((self._comments(out), self._comments(back)), (2, 1))
		self.assertEqual(self._status(out), "Unassigned")

	def test_an_employee_not_on_the_card_is_refused(self):
		a, b, _c = self.emps
		card = self._card([a])
		with self.assertRaises(frappe.ValidationError):
			tm.remove_from_cards(f'["{b}"]', f'["{card}"]', "Other")

	def test_the_last_rider_asks_before_writing(self):
		a = self.emps[0]
		card = self._card([a])

		result = tm.remove_from_cards(f'["{a}"]', f'["{card}"]', "Other")
		self.assertEqual(result, {"needs_choice": True, "empty_cards": [f"TSHIP-{card}"]})
		self.assertEqual(self._riders(card), [a])
		self.assertEqual(self._comments(card), 0)

		tm.remove_from_cards(f'["{a}"]', f'["{card}"]', "Other", on_empty="keep")
		self.assertEqual(self._riders(card), [])
		self.assertEqual(self._status(card), "Unassigned")

		other = self._card([a])
		result = tm.remove_from_cards(f'["{a}"]', f'["{other}"]', "Other", on_empty="cancel")
		self.assertEqual(result["cancelled"], [f"TSHIP-{other}"])
		self.assertEqual(self._status(other), "Inactive")

	def test_a_cancelled_card_stays_cancelled_when_its_block_leaves(self):
		from one_fm.one_fm.page.transportation_schedule.transportation_schedule import _sync_shipment_statuses

		a, b, _c = self.emps
		card = self._card([a, b], status="Assigned")
		plan, _row = self._place(card, 2)

		with patch.object(shipment_generator, "_lapsed", return_value={b}):
			result = tm.cancel_cards(f'["TSHIP-{card}"]', "Other", plan=plan)
		self.assertEqual(result["missing"], [a])
		self.assertEqual(self._status(card), "Inactive")
		self.assertEqual(self._comments(card), 1)

		_sync_shipment_statuses([], previously_linked={card})
		self.assertEqual(self._status(card), "Inactive")

	def test_a_card_on_another_plan_is_not_cancelled(self):
		card = self._card([self.emps[0]], status="Assigned")
		plan, _row = self._place(card, 1)
		with self.assertRaises(frappe.ValidationError):
			tm.cancel_cards(f'["{card}"]', "Other", plan="SOME-OTHER-PLAN")
		with self.assertRaises(frappe.ValidationError):
			tm.cancel_cards(f'["{card}"]', "Other")
		self.assertEqual(self._status(card), "Assigned")
		tm.cancel_cards(f'["{card}"]', "Other", plan=plan)
		self.assertEqual(self._status(card), "Inactive")

	def test_clear_stale_trusts_only_the_server(self):
		a, b, _c = self.emps
		shared = self._card([a, b])
		alone = self._card([a], direction="Return")

		with patch.object(shipment_generator, "_lapsed", side_effect=lambda ids: {e for e in ids if e == a}):
			result = tm.clear_stale(f'["{a}", "{b}"]')

		self.assertEqual(result["removed"], 1)
		self.assertEqual(result["skipped"], [{"employee": b, "reason": "Not stale"}])
		self.assertEqual(self._riders(shared), [b])
		self.assertEqual(self._riders(alone), [])
		self.assertEqual(self._status(shared), "Unassigned")
		self.assertEqual(self._status(alone), "Unassigned")

	def test_a_departed_card_is_locked(self):
		a, b, _c = self.emps
		card = self._card([a, b])
		self._depart(card)

		self.assertEqual(tm._departed_cards([card], today()), {card})
		with self.assertRaises(frappe.ValidationError):
			tm.remove_from_cards(f'["{a}"]', f'["{card}"]', "Other")
		with self.assertRaises(frappe.ValidationError):
			tm.cancel_cards(f'["{card}"]', "Other")
		with patch.object(shipment_generator, "_lapsed", return_value={a}):
			result = tm.clear_stale(f'["{a}"]')
		self.assertEqual(result["removed"], 0)
		self.assertIn({"employee": a, "reason": tm.DEPARTED_MESSAGE}, result["skipped"])
		self.assertEqual(self._riders(card), [a, b])

		row = next(r for r in get_traceability_matrix()["rows"] if r["id"] == a)
		leg = next(leg for leg in row["legs"] if leg["card"] == f"TSHIP-{card}")
		self.assertTrue(leg["departed"])

	def test_manage_card_lists_both_legs_and_flags_stale_riders(self):
		a, b, c = self.emps
		group = frappe.generate_hash("PG", 10)
		out = self._card([a, b], pair_group=group)
		back = self._card([a, c], direction="Return", pair_group=group)
		self._card([a], pair_group=group)  # same direction as out: not a twin
		self._depart(back)

		with patch.object(shipment_generator, "_lapsed", return_value={a}):
			result = tm.get_card_passengers(f"TSHIP-{out}")

		self.assertEqual(
			[(x["card"], x["own_direction"], x["departed"]) for x in result["cards"]],
			[(f"TSHIP-{out}", "OUTBOUND", False), (f"TSHIP-{back}", "RETURN", True)],
		)
		riders = {r["id"]: r for r in result["riders"]}
		self.assertEqual(set(riders), {a, b, c})
		self.assertEqual(result["riders"][0]["id"], a, "stale riders first")
		self.assertTrue(riders[a]["stale"])
		self.assertEqual(riders[a]["stale_reason"], "Checked out of accommodation")
		self.assertEqual(riders[a]["legs"], [f"TSHIP-{out}", f"TSHIP-{back}"])
		self.assertFalse(riders[b]["stale"])
		self.assertIsNone(riders[b]["stale_reason"])

	def test_a_user_without_the_roles_is_refused(self):
		frappe.flags.in_test = False
		frappe.set_user("Guest")
		for call in (
			lambda: tm.remove_from_cards('["E"]', '["TS-X"]'),
			lambda: tm.cancel_cards('["TS-X"]', "Other"),
			lambda: tm.clear_stale('["E"]'),
			lambda: tm.get_card_passengers("TS-X"),
		):
			with self.assertRaises(frappe.PermissionError):
				call()
