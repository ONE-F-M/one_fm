# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

"""Tests for the daily manifest compiler reliever clustering (MA1-14)."""

from types import SimpleNamespace

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from one_fm.tests.utils import make_employee
from one_fm.one_fm.doctype.transportation_manifest import manifest_compiler as mc


class TestManifestCompiler(FrappeTestCase):
	def setUp(self):
		self.emp = make_employee("mc_general@example.com").name
		self.reliever = make_employee("mc_reliever@example.com", custom_is_rambo_reliever=1).name
		self.non_reliever = make_employee("mc_nonreliever@example.com").name
		self.driver = make_employee("mc_driver@example.com").name

		if not frappe.db.exists("Location", "MC Test Location"):
			frappe.get_doc({
				"doctype": "Location", "location_name": "MC Test Location",
				"latitude": 29.3759, "longitude": 47.9774, "geofence_radius": 100,
			}).insert(ignore_permissions=True)

		if not frappe.db.exists("Vehicle", "MC-PLATE-1"):
			frappe.get_doc({
				"doctype": "Vehicle", "license_plate": "MC-PLATE-1",
				"one_fm_vehicle_category": "Owned", "make": "Toyota",
				"one_fm_vehicle_type": "Bus", "model": "Coaster", "last_odometer": 1000,
				"location": "MC Test Location", "custom_handover_date": today(),
				"employee": self.driver,
				"fuel_type": "Diesel", "uom": "Litre", "seats": 15,
			}).insert(ignore_permissions=True)
		self.vehicle = "MC-PLATE-1"

	def tearDown(self):
		frappe.db.rollback()

	# ── helpers ──────────────────────────────────────────────────────────────

	def _ensure_accommodation(self, label):
		if not frappe.db.exists("Accommodation Type", "MC Acc Type"):
			frappe.get_doc({"doctype": "Accommodation Type", "accommodation_type": "MC Acc Type"}).insert(ignore_permissions=True)
		existing = frappe.db.get_value("Accommodation", {"accommodation": label}, "name")
		if existing:
			return existing
		return frappe.get_doc({
			"doctype": "Accommodation", "accommodation": label, "type": "MC Acc Type",
		}).insert(ignore_permissions=True).name

	def _make_shipment(self, accommodation, badge="OSM"):
		return frappe.get_doc({
			"doctype": "Transportation Shipment", "accommodation": accommodation,
			"routing_type_badge": badge, "trip_direction": "Outward",
		}).insert(ignore_permissions=True).name

	def _make_schedule(self, employee, shift, is_rambo=1, availability="Working", roster="Basic"):
		doc = frappe.get_doc({
			"doctype": "Employee Schedule", "employee": employee, "date": today(),
			"shift": shift, "employee_availability": availability, "roster_type": roster,
			"is_rambo_schedule": is_rambo,
		})
		doc.insert(ignore_permissions=True)
		return doc.name

	# ── controller: shipment-less reliever camp is preserved and numbered ─────

	def test_merged_reliever_shares_existing_stop_number(self):
		"""A shipment-less reliever row keyed to an existing camp clusters under it (AC7/AC8)."""
		mahboula = self._ensure_accommodation("MC Mahboula")
		ship = self._make_shipment(mahboula, "OSM")

		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = self.vehicle
		doc.schedule_date = today()
		# General worker from a shipment stop at Mahboula.
		doc.append("transportation_manifest_details", {
			"employee": self.emp, "transportation_shipment": ship,
			"employee_action": "Boarding", "scheduled_time": "06:00:00",
		})
		# Reliever merged into the same camp — no shipment, camp pre-set by compiler.
		doc.append("transportation_manifest_details", {
			"employee": self.reliever, "pickup_accommodation": mahboula,
			"employee_action": "Boarding", "is_adhoc_stop": 0, "scheduled_time": "06:00:00",
		})
		doc.save()

		rows = doc.transportation_manifest_details
		self.assertEqual(rows[1].pickup_accommodation, mahboula)  # not wiped
		self.assertEqual(rows[1].stop_sequence, rows[0].stop_sequence)  # same stop
		self.assertEqual(rows[1].is_adhoc_stop, 0)

	def test_adhoc_reliever_gets_new_stop_and_keeps_flag(self):
		"""A reliever whose camp is off-route gets a new stop number, flag preserved (AC9)."""
		mahboula = self._ensure_accommodation("MC Mahboula")
		mangaf = self._ensure_accommodation("MC Mangaf")
		ship = self._make_shipment(mahboula, "OSM")

		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = self.vehicle
		doc.schedule_date = today()
		doc.append("transportation_manifest_details", {
			"employee": self.emp, "transportation_shipment": ship,
			"employee_action": "Boarding", "scheduled_time": "06:00:00",
		})
		doc.append("transportation_manifest_details", {
			"employee": self.reliever, "pickup_accommodation": mangaf,
			"employee_action": "Boarding", "is_adhoc_stop": 1, "scheduled_time": "06:15:00",
		})
		doc.save()

		rows = doc.transportation_manifest_details
		self.assertEqual(rows[1].pickup_accommodation, mangaf)
		self.assertNotEqual(rows[1].stop_sequence, rows[0].stop_sequence)
		self.assertEqual(rows[1].stop_sequence, 2)
		self.assertEqual(rows[1].is_adhoc_stop, 1)  # flag survives the controller

	# ── reliever source: Employee Schedule filtering ──────────────────────────

	def test_relievers_scheduled_today_filters(self):
		"""Only rambo, working, is_rambo_schedule rows for the date are returned."""
		shift = _ensure_operations_shift()
		self._make_schedule(self.reliever, shift, is_rambo=1, availability="Working")
		# Non-rambo employee on a rambo schedule -> excluded (not a reliever).
		self._make_schedule(self.non_reliever, shift, is_rambo=1, availability="Working")
		# Rambo but Day Off -> excluded (not working).
		self._make_schedule(self.reliever, shift, is_rambo=1, availability="Day Off", roster="Over-Time")

		result = mc._relievers_scheduled_today(today())
		emp_ids = {r.employee for r in result}
		self.assertIn(self.reliever, emp_ids)
		self.assertNotIn(self.non_reliever, emp_ids)
		# The reliever appears once even though two schedules exist for the shift.
		self.assertEqual(sum(1 for r in result if r.employee == self.reliever), 1)

	# ── target selection: merge vs adhoc ──────────────────────────────────────

	def test_pick_target_prefers_existing_camp_stop(self):
		"""Merge is chosen when a serving trip already stops at the reliever's camp."""
		cand_a = SimpleNamespace(vehicle="V1", trip_group="T1", stop_index=0, trip_name="A", start_time="")
		cand_b = SimpleNamespace(vehicle="V2", trip_group="T2", stop_index=0, trip_name="B", start_time="")
		manifest_stops = {("V2", "T2"): {"CAMP_X": object()}}

		target, is_merge = mc._pick_target([cand_a, cand_b], "CAMP_X", manifest_stops)
		self.assertTrue(is_merge)
		self.assertEqual(target.vehicle, "V2")

	def test_pick_target_falls_back_to_adhoc(self):
		"""With no existing camp stop, the first serving trip takes an adhoc detour."""
		cand_a = SimpleNamespace(vehicle="V1", trip_group="T1", stop_index=0, trip_name="A", start_time="")
		target, is_merge = mc._pick_target([cand_a], "CAMP_X", {})
		self.assertFalse(is_merge)
		self.assertEqual(target.vehicle, "V1")

	def test_pick_target_none_when_no_candidates(self):
		target, is_merge = mc._pick_target([], "CAMP_X", {})
		self.assertIsNone(target)
		self.assertFalse(is_merge)

	# ── manifest indexing helpers ─────────────────────────────────────────────

	def test_build_manifest_stops_and_reliever_exists(self):
		mahboula = self._ensure_accommodation("MC Mahboula")
		ship = self._make_shipment(mahboula, "OSM")

		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = self.vehicle
		doc.schedule_date = today()
		doc.append("transportation_manifest_details", {
			"employee": self.emp, "transportation_shipment": ship, "trip_id": "T1",
			"employee_action": "Boarding", "scheduled_time": "06:00:00",
		})
		doc.save()

		stops = mc._build_manifest_stops(doc)
		self.assertIn((self.vehicle, "T1"), stops)
		self.assertIn(mahboula, stops[(self.vehicle, "T1")])

		self.assertTrue(mc._reliever_row_exists(doc, self.emp, "T1"))
		self.assertFalse(mc._reliever_row_exists(doc, self.reliever, "T1"))


def _ensure_operations_shift():
	"""Return a usable Operations Shift name, creating a minimal one if needed."""
	existing = frappe.db.get_value("Operations Shift", {}, "name")
	if existing:
		return existing
	# Fall back: minimal shift (site is required in most envs, so reuse any site).
	site = frappe.db.get_value("Operations Site", {}, "name")
	doc = frappe.get_doc({
		"doctype": "Operations Shift", "shift_name": "MC Test Shift",
		"site": site, "start_time": "06:00:00", "end_time": "18:00:00",
	})
	doc.insert(ignore_permissions=True)
	return doc.name
