# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from one_fm.one_fm.doctype.transportation_manifest.manifest_board import (
	get_active_accommodations,
	get_trip_time_slots,
	group_slots,
)


def _row(trip_time, vehicle, trip_id, action="Boarding"):
	return frappe._dict(
		trip_time=trip_time, vehicle_no=vehicle, trip_id=trip_id, trip_name=trip_id,
		manifest=f"TM-{vehicle}", employee_action=action,
	)


class TestGroupSlots(FrappeTestCase):
	def test_slots_are_ordered_by_time(self):
		slots = group_slots([_row("06:00", "V1", "702"), _row("04:00", "V1", "701")])
		self.assertEqual([s["trip_time"] for s in slots], ["04:00", "06:00"])

	def test_a_vehicle_appears_in_each_slot_it_runs_in(self):
		slots = group_slots([_row("04:00", "V1", "701"), _row("06:00", "V1", "702")])
		self.assertEqual([s["trips"][0]["trip_id"] for s in slots], ["701", "702"])

	def test_two_trips_of_one_vehicle_in_a_slot_count_once(self):
		slot = group_slots([
			_row("04:00", "V1", "701"), _row("04:00", "V1", "711"), _row("04:00", "V2", "201"),
		])[0]
		self.assertEqual(len(slot["trips"]), 3)
		self.assertEqual(slot["vehicles"], 2)

	def test_boarding_counts_boarding_rows_only(self):
		slot = group_slots([
			_row("04:00", "V1", "701"), _row("04:00", "V1", "701"),
			_row("04:00", "V1", "701", action="Dropping Off"),
		])[0]
		self.assertEqual(slot["boarding"], 2)
		self.assertEqual(slot["trips"][0]["boarding"], 2)

	def test_no_rows_no_slots(self):
		self.assertEqual(group_slots([]), [])


class TestBoardEndpoints(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_only_active_accommodations(self):
		names = {a.name for a in get_active_accommodations()}
		self.assertEqual(
			names, set(frappe.get_all("Accommodation", filters={"status": "Active"}, pluck="name"))
		)

	def test_accommodations_need_manifest_read(self):
		frappe.set_user("Guest")
		self.assertRaises(frappe.PermissionError, get_active_accommodations)
		self.assertRaises(frappe.PermissionError, get_trip_time_slots, "ACC-X")

	def test_unknown_camp_returns_nothing(self):
		self.assertEqual(get_trip_time_slots("No Such Accommodation"), [])

	def test_slots_filter_on_date_and_camp(self):
		vehicle = frappe.db.get_value("Vehicle", {}, "name")
		employee = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		camps = frappe.get_all("Accommodation", pluck="name", limit=2)
		if not (vehicle and employee and len(camps) == 2):
			self.skipTest("needs a Vehicle, an Employee and two Accommodations")

		day = add_days(today(), 400)
		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = vehicle
		doc.schedule_date = day
		doc.flags.ignore_mandatory = True
		for trip_time, camp in (("04:00", camps[0]), ("06:00", camps[1])):
			doc.append("transportation_manifest_details", {
				"employee": employee, "stop_name": "Board Test", "trip_id": trip_time,
				"trip_time": trip_time, "employee_action": "Boarding",
			})
		doc.insert(ignore_permissions=True)
		# The controller derives pickup_accommodation from a shipment; set it directly.
		for d, camp in zip(doc.transportation_manifest_details, camps):
			frappe.db.set_value("Transportation Manifest Details", d.name, "pickup_accommodation", camp)

		slots = get_trip_time_slots(camps[0], day)
		self.assertEqual([s["trip_time"] for s in slots], ["04:00"])
		self.assertEqual(slots[0]["trips"][0]["vehicle_no"], vehicle)
		self.assertEqual(get_trip_time_slots(camps[0], add_days(day, 1)), [])
		self.assertEqual([s["trip_time"] for s in get_trip_time_slots(None, day)], ["04:00", "06:00"])
