# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime, today

from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	_local_seconds,
	_time_field,
)
from one_fm.one_fm.report.accommodation_dispatch_and_grooming_audit import (
	accommodation_dispatch_and_grooming_audit as report,
)
from one_fm.tests.utils import make_employee

BOARDING_TRIP = "ADGA-T1"
RETURN_TRIP = "ADGA-T2"
EARLY_CAMP_LEG = "2026-03-02T03:15:00.000Z"
LATER_CAMP_LEG = "2026-03-02T05:45:00.000Z"
NON_CAMP_LEG = "2026-03-02T01:00:00.000Z"


class TestAccommodationDispatchAndGroomingAudit(FrappeTestCase):
	def setUp(self):
		self.passed_emp = make_employee("adga_pass@example.com")
		self.failed_emp = make_employee("adga_fail@example.com")
		self.absent_emp = make_employee("adga_absent@example.com")
		self.uncovered_emp = make_employee("adga_uncovered@example.com")
		self.reliever = make_employee("adga_reliever@example.com", custom_is_rambo_reliever=1)
		self.driver = make_employee("adga_driver@example.com")

		self.camp = self._accommodation("ADGA Camp A")
		self.other_camp = self._accommodation("ADGA Camp B")
		self.vehicle = self._vehicle("ADGA-PLATE-1")
		self.manifest = self._manifest()
		self._route_plan_rows()

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	# ── fixtures ─────────────────────────────────────────────────────────────

	def _accommodation(self, label):
		if not frappe.db.exists("Accommodation Type", "Test Acc Type"):
			frappe.get_doc(
				{"doctype": "Accommodation Type", "accommodation_type": "Test Acc Type"}
			).insert(ignore_permissions=True)
		existing = frappe.db.get_value("Accommodation", {"accommodation": label}, "name")
		if existing:
			return existing
		return (
			frappe.get_doc({"doctype": "Accommodation", "accommodation": label, "type": "Test Acc Type", "status": "Active"})
			.insert(ignore_permissions=True)
			.name
		)

	def _vehicle(self, plate):
		if frappe.db.exists("Vehicle", plate):
			return plate
		if not frappe.db.exists("Location", "Test Location"):
			frappe.get_doc(
				{
					"doctype": "Location",
					"location_name": "Test Location",
					"latitude": 29.3759,
					"longitude": 47.9774,
					"geofence_radius": 100,
				}
			).insert(ignore_permissions=True)
		return (
			frappe.get_doc(
				{
					"doctype": "Vehicle",
					"license_plate": plate,
					"one_fm_vehicle_category": "Owned",
					"make": "Toyota",
					"one_fm_vehicle_type": "Bus",
					"model": "Coaster",
					"last_odometer": 1000,
					"location": "Test Location",
					"employee": self.driver.name,
					"custom_handover_date": today(),
					"fuel_type": "Diesel",
					"uom": "Litre",
					"seats": 15,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _manifest(self):
		"""One manifest: a four-row Boarding run and a Dropping Off run."""
		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = self.vehicle
		doc.schedule_date = today()
		boarding = {"trip_id": BOARDING_TRIP, "employee_action": "Boarding", "scheduled_time": "08:00:00"}
		doc.append(
			"transportation_manifest_details",
			{**boarding, "employee": self.passed_emp.name, "attendance_status": "Present", "qoa_status": "Pass"},
		)
		doc.append(
			"transportation_manifest_details",
			{
				**boarding,
				"employee": self.failed_emp.name,
				"attendance_status": "Present",
				"qoa_status": "Fail",
				"qoa_reason": "Grooming",
			},
		)
		doc.append(
			"transportation_manifest_details",
			{
				**boarding,
				"employee": self.absent_emp.name,
				"attendance_status": "Absent",
				"requires_reliever": 1,
				"reliever_employee": self.reliever.name,
			},
		)
		doc.append(
			"transportation_manifest_details",
			{**boarding, "employee": self.uncovered_emp.name, "attendance_status": "Absent"},
		)
		doc.append(
			"transportation_manifest_details",
			{
				"trip_id": RETURN_TRIP,
				"employee_action": "Dropping Off",
				"scheduled_time": "17:00:00",
				"employee": self.passed_emp.name,
			},
		)
		doc.save(ignore_permissions=True)

		# The controller derives stop numbers and camps from shipments; pin the shape this
		# test is about directly so it does not depend on that derivation.
		for row in doc.transportation_manifest_details:
			frappe.db.set_value(
				"Transportation Manifest Details",
				row.name,
				{
					"trip_id": row.trip_id,
					"employee_action": row.employee_action,
					"stop_sequence": 1,
					"pickup_accommodation": self.camp if row.employee_action == "Boarding" else None,
				},
			)
		return doc

	def _route_plan_rows(self):
		now = now_datetime()
		for stop_index, start_time, is_camp_leg in (
			(2, LATER_CAMP_LEG, 1),
			(1, EARLY_CAMP_LEG, 1),
			(0, NON_CAMP_LEG, 0),
		):
			frappe.get_doc(
				{
					"doctype": "Route Plan Assignment",
					"name": frappe.generate_hash(length=10),
					"trip_group": BOARDING_TRIP,
					"stop_index": stop_index,
					"start_time": start_time,
					"is_camp_leg": is_camp_leg,
					"creation": now,
					"modified": now,
					"owner": "Administrator",
					"modified_by": "Administrator",
				}
			).db_insert()

	def _run(self, **filters):
		_columns, data = report.execute({"date": today(), **filters})
		return data

	def _trips(self, data):
		return [row for row in data if row["indent"] == 0]

	def _ours(self, data):
		return [row for row in self._trips(data) if row["manifest"] == self.manifest.name]

	def _passenger(self, data, employee):
		return next(row for row in data if row["indent"] == 1 and row["employee"] == employee.name)

	def _set_all_passed(self):
		for row in self.manifest.transportation_manifest_details:
			if row.employee_action == "Boarding":
				frappe.db.set_value(
					"Transportation Manifest Details",
					row.name,
					{"attendance_status": "Present", "qoa_status": "Pass", "qoa_reason": None},
				)

	# ── scaffold ─────────────────────────────────────────────────────────────

	def test_report_definition(self):
		path = os.path.join(os.path.dirname(report.__file__), "accommodation_dispatch_and_grooming_audit.json")
		with open(path) as f:
			doc = json.load(f)
		self.assertEqual(doc["report_type"], "Script Report")
		self.assertEqual(doc["is_standard"], "Yes")
		self.assertEqual(doc["ref_doctype"], "Transportation Manifest")

	def test_columns_are_one_list_with_boarding_time(self):
		columns, _data = report.execute({"date": today()})
		fieldnames = [column["fieldname"] for column in columns]
		self.assertIn("boarding_time", fieldnames)
		self.assertEqual(len(fieldnames), len(set(fieldnames)))

	# ── AC1 scope ────────────────────────────────────────────────────────────

	def test_dropping_off_run_is_absent(self):
		data = self._run()
		self.assertEqual([row["trip_id"] for row in self._ours(data)], [BOARDING_TRIP])
		self.assertNotIn(RETURN_TRIP, [row.get("trip_id") for row in data])

	def test_future_date_is_empty(self):
		self.assertEqual(self._run(date=add_days(today(), 3)), [])

	def test_user_without_read_access_gets_no_rows(self):
		email = "adga_noaccess@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "No Access", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		frappe.set_user(email)
		try:
			self.assertEqual(self._run(), [])
		finally:
			frappe.set_user("Administrator")

	# ── AC4 trip row ─────────────────────────────────────────────────────────

	def test_trip_row_values(self):
		trip = self._ours(self._run())[0]
		self.assertEqual(trip["indent"], 0)
		self.assertFalse(trip["parent_trip"])
		self.assertEqual(trip["headcount"], 4)
		self.assertEqual(trip["present"], 2)
		self.assertEqual(trip["vehicle"], self.vehicle)
		self.assertTrue(trip["compliance_summary"].startswith("1/4"))
		self.assertIn("25%", trip["compliance_summary"])
		self.assertEqual(trip["compliance_warnings"], 1)
		self.assertEqual(trip["lock_status"], "Not Started")
		self.assertEqual(trip["manifest"], self.manifest.name)
		self.assertEqual(trip["camp"], "ADGA Camp A")

	def test_departure_is_lowest_camp_leg_start(self):
		trip = self._ours(self._run())[0]
		self.assertEqual(trip["departure_time"], _time_field(_local_seconds(EARLY_CAMP_LEG)))

	def test_departure_blank_without_camp_leg(self):
		frappe.db.delete("Route Plan Assignment", {"trip_group": BOARDING_TRIP})
		self.assertEqual(self._ours(self._run())[0]["departure_time"], "")

	def test_lock_status_follows_active_stop(self):
		doc = frappe.get_doc("Transportation Manifest", self.manifest.name)
		doc.set_active_stop_for(BOARDING_TRIP, 1)
		self.assertEqual(self._ours(self._run())[0]["lock_status"], "In Progress (Stop 1)")
		doc.set_active_stop_for(BOARDING_TRIP, 2)
		self.assertEqual(self._ours(self._run())[0]["lock_status"], "Completed")

	# ── AC2 / AC3 passenger rows ─────────────────────────────────────────────

	def test_passenger_labels(self):
		data = self._run()
		children = [row for row in data if row["indent"] == 1]
		self.assertEqual(len(children), 4)
		for child in children:
			self.assertEqual(child["parent_trip"], self._ours(data)[0]["row_id"])

		passed = self._passenger(data, self.passed_emp)
		self.assertEqual(passed["attendance_result"], "Present")
		self.assertEqual(passed["appearance_result"], report.PASSED)
		self.assertIsNotNone(passed["boarding_time"])
		self.assertFalse(passed["reliever_pairing"])

		failed = self._passenger(data, self.failed_emp)
		self.assertEqual(failed["attendance_result"], "Present")
		self.assertEqual(failed["appearance_result"], "Failed")
		self.assertEqual(failed["failure_reason"], "Grooming")

		absent = self._passenger(data, self.absent_emp)
		self.assertEqual(absent["attendance_result"], "Absent")
		self.assertEqual(
			absent["reliever_pairing"], f"{absent['employee_name']} \u2794 {self.reliever.employee_name}"
		)
		self.assertIsNone(absent["boarding_time"])
		self.assertFalse(absent["appearance_result"])

		uncovered = self._passenger(data, self.uncovered_emp)
		self.assertEqual(uncovered["attendance_result"], "Absent (Uncovered)")
		self.assertFalse(uncovered["reliever_pairing"])

	# ── AC5 filters ──────────────────────────────────────────────────────────

	def test_each_compliance_option(self):
		self.assertEqual(len(self._ours(self._run(compliance="All Trips"))), 1)
		self.assertEqual(len(self._ours(self._run(compliance="Trips with Absentees"))), 1)
		self.assertEqual(len(self._ours(self._run(compliance="Trips with Grooming/Uniform Fails"))), 1)
		self.assertEqual(self._ours(self._run(compliance="100% Passed Trips")), [])

		self._set_all_passed()
		self.assertEqual(len(self._ours(self._run(compliance="100% Passed Trips"))), 1)
		self.assertEqual(self._ours(self._run(compliance="Trips with Absentees")), [])
		self.assertEqual(self._ours(self._run(compliance="Trips with Grooming/Uniform Fails")), [])

	def test_search_on_reliever_name_shows_whole_trip(self):
		data = self._run(search=self.reliever.employee_name)
		self.assertEqual(len(self._ours(data)), 1)
		self.assertEqual(len([row for row in data if row["indent"] == 1]), 4)

	def test_search_by_employee_and_miss(self):
		self.assertEqual(len(self._ours(self._run(search=self.absent_emp.name))), 1)
		self.assertEqual(self._ours(self._run(search="no-such-person-zzz")), [])

	def test_camp_filter(self):
		self.assertEqual(len(self._ours(self._run(camp=self.camp))), 1)
		self.assertEqual(self._run(camp=self.other_camp), [])
