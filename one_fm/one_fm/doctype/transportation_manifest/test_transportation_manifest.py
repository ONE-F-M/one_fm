# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today
from one_fm.tests.utils import make_employee

class TestTransportationManifest(FrappeTestCase):
	def setUp(self):
		# Ensure we have test locations
		if not frappe.db.exists("Location", "Test Location"):
			loc = frappe.get_doc({
				"doctype": "Location",
				"location_name": "Test Location",
				"latitude": 29.3759,
				"longitude": 47.9774,
				"geofence_radius": 100
			}).insert(ignore_permissions=True)
			self.loc_name = loc.name
		else:
			self.loc_name = "Test Location"

		# Create test employees using existing test factories
		self.employee1_doc = make_employee("test_emp1@example.com")
		self.employee1 = self.employee1_doc.name
		
		self.employee2_doc = make_employee("test_emp2@example.com")
		self.employee2 = self.employee2_doc.name
		
		self.reliever_doc = make_employee("test_reliever@example.com", custom_is_rambo_reliever=1)
		self.reliever = self.reliever_doc.name

		self.driver_doc = make_employee("test_driver@example.com")
		self.driver = self.driver_doc.name

		# Create test vehicles to be independent of pre-existing database vehicles
		self.vehicle1_doc = frappe.get_doc({
			"doctype": "Vehicle",
			"license_plate": "TEST-PLATE-1",
			"one_fm_vehicle_category": "Owned",
			"make": "Toyota",
			"one_fm_vehicle_type": "Bus",
			"model": "Coaster",
			"last_odometer": 1000,
			"location": self.loc_name,
			"employee": self.driver,
			"custom_handover_date": today(),
			"fuel_type": "Diesel",
			"uom": "Litre",
			"seats": 15
		})
		if not frappe.db.exists("Vehicle", "TEST-PLATE-1"):
			self.vehicle1_doc.insert(ignore_permissions=True)
			self.vehicle1 = self.vehicle1_doc.name
		else:
			self.vehicle1 = "TEST-PLATE-1"

		self.vehicle2_doc = frappe.get_doc({
			"doctype": "Vehicle",
			"license_plate": "TEST-PLATE-2",
			"one_fm_vehicle_category": "Owned",
			"make": "Toyota",
			"one_fm_vehicle_type": "Bus",
			"model": "Coaster",
			"last_odometer": 1000,
			"location": self.loc_name,
			"employee": self.driver,
			"custom_handover_date": today(),
			"fuel_type": "Diesel",
			"uom": "Litre",
			"seats": 15
		})
		if not frappe.db.exists("Vehicle", "TEST-PLATE-2"):
			self.vehicle2_doc.insert(ignore_permissions=True)
			self.vehicle2 = self.vehicle2_doc.name
		else:
			self.vehicle2 = "TEST-PLATE-2"
		self.reliever = self.reliever_doc.name

	def tearDown(self):
		frappe.db.rollback()

	def test_qoa_fail_requires_reason(self):
		# Present + Fail QOA without reason must raise ValidationError
		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = self.vehicle1
		doc.schedule_date = today()
		doc.append("transportation_manifest_details", {
			"stop_name": "Test Stop",
			"employee": self.employee1,
			"attendance_status": "Present",
			"qoa_status": "Fail",
			"scheduled_time": "08:00:00"
		})
		self.assertRaises(frappe.ValidationError, doc.save)

		# Present + Fail QOA with reason must pass
		doc.transportation_manifest_details[0].qoa_reason = "Grooming"
		doc.save()

	def test_absent_clears_qoa(self):
		# Absent clears QOA status and reason
		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = self.vehicle1
		doc.schedule_date = today()
		doc.append("transportation_manifest_details", {
			"stop_name": "Test Stop",
			"employee": self.employee1,
			"attendance_status": "Absent",
			"qoa_status": "Fail",
			"qoa_reason": "Grooming",
			"scheduled_time": "08:00:00"
		})
		doc.save()
		self.assertEqual(doc.transportation_manifest_details[0].qoa_status, None)
		self.assertEqual(doc.transportation_manifest_details[0].qoa_reason, None)

	def test_present_qoa_fail_allows_reliever(self):
		# A Present worker who fails QOA can be flagged and assigned a reliever.
		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = self.vehicle1
		doc.schedule_date = today()
		doc.append("transportation_manifest_details", {
			"stop_name": "Test Stop",
			"employee": self.employee1,
			"attendance_status": "Present",
			"qoa_status": "Fail",
			"qoa_reason": "Uniform",
			"reliever_employee": self.reliever,
			"scheduled_time": "08:00:00"
		})
		doc.save()

		row = doc.transportation_manifest_details[0]
		# requires_reliever is auto-set when a reliever is assigned
		self.assertEqual(row.requires_reliever, 1)
		# QOA fields are preserved (not cleared, since the worker is Present)
		self.assertEqual(row.qoa_status, "Fail")
		self.assertEqual(row.qoa_reason, "Uniform")
		self.assertEqual(row.reliever_employee, self.reliever)

	def test_reliever_replacement_validation(self):
		# Assign reliever employee
		doc1 = frappe.new_doc("Transportation Manifest")
		doc1.vehicle_no = self.vehicle1
		doc1.schedule_date = today()
		doc1.append("transportation_manifest_details", {
			"stop_name": "Test Stop 1A",
			"employee": self.employee1,
			"attendance_status": "Absent",
			"reliever_employee": self.reliever,
			"scheduled_time": "08:00:00"
		})
		doc1.append("transportation_manifest_details", {
			"stop_name": "Test Stop 1B",
			"employee": self.employee1,
			"attendance_status": "Present",
			"scheduled_time": "09:00:00"
		})
		doc1.save()
		# check requires_reliever flag was set to 1
		self.assertEqual(doc1.transportation_manifest_details[0].requires_reliever, 1)

		# Try to use the same reliever in another overlapping manifest vehicle on the same date
		doc2 = frappe.new_doc("Transportation Manifest")
		doc2.vehicle_no = self.vehicle2
		doc2.schedule_date = today()
		doc2.append("transportation_manifest_details", {
			"stop_name": "Test Stop 2A",
			"employee": self.employee2,
			"attendance_status": "Absent",
			"reliever_employee": self.reliever,
			"scheduled_time": "08:30:00"  # overlapping time
		})
		doc2.append("transportation_manifest_details", {
			"stop_name": "Test Stop 2B",
			"employee": self.employee2,
			"attendance_status": "Present",
			"scheduled_time": "09:30:00"
		})
		self.assertRaises(frappe.ValidationError, doc2.save)

	def test_replaced_reliever_validation(self):
		# Flag reliever as replaced by making them absent/replaced on another manifest on the same date
		doc1 = frappe.new_doc("Transportation Manifest")
		doc1.vehicle_no = self.vehicle1
		doc1.schedule_date = today()
		doc1.append("transportation_manifest_details", {
			"stop_name": "Test Stop 1",
			"employee": self.reliever,
			"attendance_status": "Absent",
			"scheduled_time": "08:00:00"
		})
		doc1.save()

		# Try to select the same reliever for employee1 in another manifest
		doc2 = frappe.new_doc("Transportation Manifest")
		doc2.vehicle_no = self.vehicle2
		doc2.schedule_date = today()
		doc2.append("transportation_manifest_details", {
			"stop_name": "Test Stop 2",
			"employee": self.employee1,
			"attendance_status": "Absent",
			"reliever_employee": self.reliever,
			"scheduled_time": "12:00:00"
		})
		self.assertRaises(frappe.ValidationError, doc2.save)

	def test_same_manifest_reliever_validation(self):
		# 1. Test double booking same reliever within the same manifest
		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = self.vehicle1
		doc.schedule_date = today()
		doc.append("transportation_manifest_details", {
			"stop_name": "Stop 1",
			"employee": self.employee1,
			"attendance_status": "Absent",
			"reliever_employee": self.reliever,
			"scheduled_time": "08:00:00"
		})
		doc.append("transportation_manifest_details", {
			"stop_name": "Stop 2",
			"employee": self.employee2,
			"attendance_status": "Absent",
			"reliever_employee": self.reliever,
			"scheduled_time": "09:00:00"
		})
		self.assertRaises(frappe.ValidationError, doc.save)

		# 2. Test choosing a passenger from the same manifest as a reliever
		doc2 = frappe.new_doc("Transportation Manifest")
		doc2.vehicle_no = self.vehicle1
		doc2.schedule_date = today()
		doc2.append("transportation_manifest_details", {
			"stop_name": "Stop 1",
			"employee": self.employee1,
			"attendance_status": "Present",
			"scheduled_time": "08:00:00"
		})
		doc2.append("transportation_manifest_details", {
			"stop_name": "Stop 2",
			"employee": self.employee2,
			"attendance_status": "Absent",
			"reliever_employee": self.employee1,  # employee1 is passenger in same manifest
			"scheduled_time": "09:00:00"
		})
		self.assertRaises(frappe.ValidationError, doc2.save)

	def test_sync_appends_new_rows(self):
		"""sync_manifest_details should append new employee rows without duplicating existing ones."""
		from types import SimpleNamespace
		from one_fm.one_fm.doctype.transportation_manifest.manifest_sync import sync_manifest_details

		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = self.vehicle1
		doc.schedule_date = today()

		# First sync — 1 employee at 1 stop
		assignments = [SimpleNamespace(
			direction="OUTBOUND", card_id="C1", stop_location="Stop A",
			trip_group="TRIP_1", trip_name="Morning Run", start_time="06:00:00", end_time=None
		)]
		emp_map = {"C1": [{"id": self.employee1, "name": "Emp 1"}]}

		changed = sync_manifest_details(doc, assignments, emp_map, {})
		self.assertTrue(changed)
		self.assertEqual(len(doc.transportation_manifest_details), 1)

		# Second sync — add employee2 to same stop
		emp_map = {"C1": [{"id": self.employee1, "name": "Emp 1"}, {"id": self.employee2, "name": "Emp 2"}]}
		changed = sync_manifest_details(doc, assignments, emp_map, {})
		self.assertTrue(changed)
		self.assertEqual(len(doc.transportation_manifest_details), 2)

		# Third sync — same data, no changes
		changed = sync_manifest_details(doc, assignments, emp_map, {})
		self.assertFalse(changed)
		self.assertEqual(len(doc.transportation_manifest_details), 2)

		employees = {row.employee for row in doc.transportation_manifest_details}
		self.assertIn(self.employee1, employees)
		self.assertIn(self.employee2, employees)

	def test_sync_preserves_attendance_state(self):
		"""sync_manifest_details must not overwrite manual attendance/QOA fields."""
		from types import SimpleNamespace
		from one_fm.one_fm.doctype.transportation_manifest.manifest_sync import sync_manifest_details

		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = self.vehicle1
		doc.schedule_date = today()

		assignments = [SimpleNamespace(
			direction="OUTBOUND", card_id="C1", stop_location="Stop A",
			trip_group="TRIP_1", trip_name="Morning", start_time="06:00:00", end_time=None
		)]
		emp_map = {"C1": [{"id": self.employee1, "name": "Emp 1"}]}

		# Initial sync
		sync_manifest_details(doc, assignments, emp_map, {})
		doc.save()

		# Simulate dispatcher marking attendance
		doc.transportation_manifest_details[0].attendance_status = "Present"
		doc.transportation_manifest_details[0].qoa_status = "Pass"
		doc.save()

		# Re-sync with updated schedule time — manual fields must survive
		assignments[0].start_time = "06:30:00"
		changed = sync_manifest_details(doc, assignments, emp_map, {})

		# Must report a change so callers know to save
		self.assertTrue(changed)

		# Save and reload to verify persistence
		doc.save()
		doc.reload()

		row = doc.transportation_manifest_details[0]
		self.assertEqual(str(row.scheduled_time), "06:30:00")
		self.assertEqual(row.attendance_status, "Present")
		self.assertEqual(row.qoa_status, "Pass")



	def test_sync_backfills_stop_id_for_legacy_rows(self):
		"""Pre-existing rows without stop_id should be matched via derived key, not duplicated."""
		from types import SimpleNamespace
		from one_fm.one_fm.doctype.transportation_manifest.manifest_sync import sync_manifest_details

		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = self.vehicle1
		doc.schedule_date = today()

		# Simulate a legacy row (created before stop_id field existed)
		doc.append("transportation_manifest_details", {
			"stop_name": "Stop A",
			"employee": self.employee1,
			"trip_id": "TRIP_1",
			"stop_id": "",  # Legacy — no stop_id
			"stop_type": "Pick Up",
			"employee_action": "Boarding",
			"scheduled_time": "06:00:00",
			"attendance_status": "Present",
			"qoa_status": "Pass",
		})
		doc.save()

		# Sync with same data — should match the legacy row, NOT create a duplicate
		assignments = [SimpleNamespace(
			direction="OUTBOUND", card_id="C1", stop_location="Stop A",
			trip_group="TRIP_1", trip_name="Morning", start_time="06:00:00", end_time=None
		)]
		emp_map = {"C1": [{"id": self.employee1, "name": "Emp 1"}]}

		changed = sync_manifest_details(doc, assignments, emp_map, {})

		# Should have backfilled stop_id, not duplicated
		self.assertEqual(len(doc.transportation_manifest_details), 1)
		row = doc.transportation_manifest_details[0]
		self.assertEqual(row.stop_id, "Stop A|OUTBOUND")
		# Attendance preserved
		self.assertEqual(row.attendance_status, "Present")
		self.assertEqual(row.qoa_status, "Pass")

	# ── Stop Sequence / Pickup Accommodation auto-population ──────────────────

	def _ensure_accommodation(self, label):
		"""Create (once) an Accommodation record and return its docname."""
		if not frappe.db.exists("Accommodation Type", "Test Acc Type"):
			frappe.get_doc({
				"doctype": "Accommodation Type",
				"accommodation_type": "Test Acc Type",
			}).insert(ignore_permissions=True)

		existing = frappe.db.get_value("Accommodation", {"accommodation": label}, "name")
		if existing:
			return existing

		acc = frappe.get_doc({
			"doctype": "Accommodation",
			"accommodation": label,
			"type": "Test Acc Type",
		}).insert(ignore_permissions=True)
		return acc.name

	def _make_shipment(self, accommodation, badge):
		"""Create a Transportation Shipment for the given camp and routing badge."""
		ship = frappe.get_doc({
			"doctype": "Transportation Shipment",
			"accommodation": accommodation,
			"routing_type_badge": badge,
			"trip_direction": "Outward",
		}).insert(ignore_permissions=True)
		return ship.name

	def test_multi_stop_sequence_and_pickup_accommodation(self):
		"""OSM/OLM rows are numbered per unique accommodation in first-appearance order."""
		mahboula = self._ensure_accommodation("Mahboula Camp Test")
		mangaf = self._ensure_accommodation("Mangaf Camp Test")
		ship_mahboula = self._make_shipment(mahboula, "OSM")
		ship_mangaf = self._make_shipment(mangaf, "OSM")

		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = self.vehicle1
		doc.schedule_date = today()
		# Two Mahboula rows first, then one Mangaf row (mirrors the operational example)
		doc.append("transportation_manifest_details", {
			"employee": self.employee1, "transportation_shipment": ship_mahboula,
			"scheduled_time": "06:00:00",
		})
		doc.append("transportation_manifest_details", {
			"employee": self.employee2, "transportation_shipment": ship_mahboula,
			"scheduled_time": "06:00:00",
		})
		doc.append("transportation_manifest_details", {
			"employee": self.reliever, "transportation_shipment": ship_mangaf,
			"scheduled_time": "06:30:00",
		})
		doc.save()

		rows = doc.transportation_manifest_details
		# Mahboula rows -> Stop 1
		self.assertEqual(rows[0].pickup_accommodation, mahboula)
		self.assertEqual(rows[0].stop_sequence, 1)
		self.assertEqual(rows[1].pickup_accommodation, mahboula)
		self.assertEqual(rows[1].stop_sequence, 1)
		# Mangaf row -> Stop 2
		self.assertEqual(rows[2].pickup_accommodation, mangaf)
		self.assertEqual(rows[2].stop_sequence, 2)

	def test_direct_route_forces_stop_sequence_one(self):
		"""A Direct shipment row is always Stop Sequence 1 with its own camp as pickup."""
		camp = self._ensure_accommodation("Direct Camp Test")
		ship_direct = self._make_shipment(camp, "Direct")

		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = self.vehicle1
		doc.schedule_date = today()
		doc.append("transportation_manifest_details", {
			"employee": self.employee1, "transportation_shipment": ship_direct,
			"scheduled_time": "06:00:00",
		})
		doc.append("transportation_manifest_details", {
			"employee": self.employee2, "transportation_shipment": ship_direct,
			"scheduled_time": "06:00:00",
		})
		doc.save()

		for row in doc.transportation_manifest_details:
			self.assertEqual(row.stop_sequence, 1)
			self.assertEqual(row.pickup_accommodation, camp)

	# ── MA2-11: Multi-accommodation attendance-check sheet ────────────────────

	def _make_two_stop_manifest(self):
		"""Build a saved 2-stop manifest (Mahboula = Stop 1, Mangaf = Stop 2)."""
		import json as _json  # noqa: F401 (kept local; sheet API imports json itself)

		mahboula = self._ensure_accommodation("Sheet Mahboula")
		mangaf = self._ensure_accommodation("Sheet Mangaf")
		ship_mahboula = self._make_shipment(mahboula, "OSM")
		ship_mangaf = self._make_shipment(mangaf, "OSM")

		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = self.vehicle1
		doc.schedule_date = today()
		doc.append("transportation_manifest_details", {
			"employee": self.employee1, "transportation_shipment": ship_mahboula,
			"scheduled_time": "06:00:00",
		})
		doc.append("transportation_manifest_details", {
			"employee": self.employee2, "transportation_shipment": ship_mangaf,
			"scheduled_time": "06:30:00",
		})
		doc.save()
		return doc

	def test_sheet_groups_rows_by_stop(self):
		from one_fm.one_fm.doctype.transportation_manifest.manifest_sheet import get_manifest_sheet

		doc = self._make_two_stop_manifest()
		sheet = get_manifest_sheet(doc.name)

		self.assertEqual(len(sheet["stops"]), 2)
		self.assertEqual(sheet["stops"][0]["stop_sequence"], 1)
		self.assertEqual(sheet["stops"][1]["stop_sequence"], 2)
		self.assertEqual(sheet["active_stop_sequence"], 0)
		# Nothing triggered yet -> every stop locked, only Stop 1 can be triggered.
		self.assertEqual(sheet["stops"][0]["status"], "Locked")
		self.assertTrue(sheet["stops"][0]["can_trigger"])
		self.assertFalse(sheet["stops"][1]["can_trigger"])

	def test_sheet_flags_reliever_rows(self):
		from one_fm.one_fm.doctype.transportation_manifest.manifest_sheet import get_manifest_sheet

		doc = self._make_two_stop_manifest()
		# Assign a reliever to Stop 1's worker (Present + failed QOA path, with the
		# reliever flag set so the controller preserves reliever_employee).
		row = doc.transportation_manifest_details[0]
		row.attendance_status = "Present"
		row.qoa_status = "Fail"
		row.qoa_reason = "Uniform"
		row.requires_reliever = 1
		row.reliever_employee = self.reliever
		doc.save()

		sheet = get_manifest_sheet(doc.name)
		p1 = sheet["stops"][0]["passengers"][0]
		p2 = sheet["stops"][1]["passengers"][0]
		self.assertTrue(p1["is_reliever"])
		self.assertEqual(p1["reliever_employee"], self.reliever)
		self.assertFalse(p2["is_reliever"])

	def test_trigger_is_strictly_sequential(self):
		from one_fm.one_fm.doctype.transportation_manifest.manifest_sheet import (
			trigger_attendance_check,
		)

		doc = self._make_two_stop_manifest()

		# Cannot jump straight to Stop 2.
		self.assertRaises(frappe.ValidationError, trigger_attendance_check, doc.name, 2)

		# Stop 1 unlocks; it becomes Active, Stop 2 stays Locked.
		sheet = trigger_attendance_check(doc.name, 1)
		self.assertEqual(sheet["active_stop_sequence"], 1)
		self.assertEqual(sheet["stops"][0]["status"], "Active")
		self.assertEqual(sheet["stops"][1]["status"], "Locked")
		self.assertTrue(sheet["stops"][1]["can_trigger"])

	def test_save_only_active_stop_and_completed_stays_locked(self):
		from one_fm.one_fm.doctype.transportation_manifest.manifest_sheet import (
			trigger_attendance_check,
			save_stop_checks,
		)

		doc = self._make_two_stop_manifest()
		row1 = doc.transportation_manifest_details[0].name

		# Stop 2 is locked -> saving it must fail.
		self.assertRaises(
			frappe.ValidationError,
			save_stop_checks,
			doc.name, 2, [{"row_name": row1, "attendance_status": "Present"}],
		)

		# Unlock + save Stop 1.
		trigger_attendance_check(doc.name, 1)
		sheet = save_stop_checks(
			doc.name, 1, [{"row_name": row1, "attendance_status": "Present", "qoa_status": "Pass"}]
		)
		self.assertEqual(sheet["stops"][0]["passengers"][0]["attendance_status"], "Present")

		# Advance to Stop 2 -> Stop 1 is now Completed and frozen.
		trigger_attendance_check(doc.name, 2)
		doc.reload()
		doc.transportation_manifest_details[0].attendance_status = "Absent"
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_complete_stop_advances_pointer(self):
		from one_fm.one_fm.doctype.transportation_manifest.manifest_sheet import (
			trigger_attendance_check,
			complete_stop,
		)

		doc = self._make_two_stop_manifest()
		trigger_attendance_check(doc.name, 1)
		trigger_attendance_check(doc.name, 2)
		# Completing the final (active) stop locks everything.
		sheet = complete_stop(doc.name, 2)
		self.assertEqual(sheet["active_stop_sequence"], 3)
		self.assertTrue(sheet["all_completed"])
		self.assertTrue(all(s["status"] == "Completed" for s in sheet["stops"]))

