# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from one_fm.one_fm.doctype.transportation_manifest.manifest_board import (
	get_active_accommodations,
	get_lobby_board,
	get_trip_time_slots,
	group_slots,
)

LEGS = "one_fm.one_fm.doctype.transportation_manifest.manifest_board._camp_legs"


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


class TestLobbyBoard(FrappeTestCase):
	"""get_lobby_board on manifests written here, filtered to trip ids starting LBT-."""

	def setUp(self):
		camps = {}
		for a in frappe.get_all("Accommodation", fields=["name", "accommodation", "transport_stop_location"]):
			if a.transport_stop_location and a.transport_stop_location not in {c.transport_stop_location for c in camps.values()}:
				camps[a.name] = a
		self.employees = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name", limit=12)
		with_driver = frappe.db.get_value("Vehicle", {"employee": ["is", "set"]}, "name")
		if len(camps) < 2 or len(self.employees) < 12 or not with_driver:
			self.skipTest("needs two camps on different stops, 12 Employees and a Vehicle with a driver")
		self.here, self.there = list(camps.values())[:2]
		self.vehicle = with_driver
		self.legs = patch(LEGS, return_value={})
		self.legs.start()

	def tearDown(self):
		self.legs.stop()
		frappe.set_user("Administrator")
		# FrappeTestCase rolls back per class; each test here reads by trip id.
		frappe.db.rollback()

	def _shipment(self, name, **values):
		doc = frappe.get_doc({"doctype": "Transportation Shipment", **values})
		doc.name = name
		doc.db_insert()
		return name

	def _manifest(self, day, rows, vehicle=None):
		"""rows: dicts of detail values; written after insert so validate cannot rewrite them."""
		doc = frappe.new_doc("Transportation Manifest")
		doc.vehicle_no = vehicle or self.vehicle
		doc.schedule_date = day
		doc.flags.ignore_mandatory = True
		for i, values in enumerate(rows):
			employee = values.get("employee") or self.employees[i]
			doc.append("transportation_manifest_details", {
				"employee": employee,
				"employee_name": frappe.db.get_value("Employee", employee, "employee_name"),
				"stop_name": values.get("stop_name", "Site A"),
				"trip_id": values["trip_id"], "trip_name": values["trip_id"],
				"employee_action": values.get("employee_action", "Boarding"),
			})
		doc.insert(ignore_permissions=True)
		for d, values in zip(doc.transportation_manifest_details, rows):
			frappe.db.set_value("Transportation Manifest Details", d.name, {
				"trip_time": values.get("trip_time", "14:00"),
				"pickup_accommodation": values.get("camp", self.here.name),
				**{k: v for k, v in values.items() if k in (
					"attendance_status", "qoa_status", "reliever_employee", "requires_reliever",
					"transportation_shipment", "scheduled_time",
				)},
			})
		return doc

	def _trips(self, board=None):
		board = board or get_lobby_board(self.here.name)
		return {t["trip_id"]: t for t in board["trips"] if t["trip_id"].startswith("LBT-")}

	def test_only_trips_with_a_row_from_this_camp(self):
		self._manifest(today(), [
			{"trip_id": "LBT-1"},
			{"trip_id": "LBT-2", "camp": self.there.name},
		])
		trips = self._trips()
		self.assertEqual(set(trips), {"LBT-1"})
		board = get_lobby_board(self.here.name)
		self.assertEqual(board["accommodation"], self.here.name)
		self.assertTrue(board["server_now"])

	def test_departure_is_schedule_date_and_trip_time(self):
		tomorrow = add_days(today(), 1)
		self._manifest(today(), [{"trip_id": "LBT-1", "trip_time": "14:30"}])
		self._manifest(tomorrow, [{"trip_id": "LBT-2", "trip_time": "06:05"}])
		trips = self._trips()
		self.assertEqual(trips["LBT-1"]["departure"], f"{today()}T14:30:00")
		self.assertEqual(trips["LBT-2"]["departure"], f"{tomorrow}T06:05:00")

	def test_manifests_outside_yesterday_to_tomorrow_are_not_read(self):
		self._manifest(add_days(today(), 2), [{"trip_id": "LBT-1"}])
		self.assertEqual(self._trips(), {})

	def test_empty_run_names_the_camps_that_board(self):
		self._manifest(today(), [{"trip_id": "LBT-1", "camp": self.there.name} for _ in range(3)])
		self.legs.stop()
		with patch(LEGS, return_value={"LBT-1": {"departure": "13:40", "qoa": "13:20"}}):
			trip = self._trips()["LBT-1"]
		self.legs.start()
		self.assertEqual(trip["passengers"], [])
		self.assertEqual(trip["joins_elsewhere"], [{"accommodation": self.there.accommodation, "count": 3}])
		self.assertEqual(trip["departure"], f"{today()}T13:40:00")
		self.assertEqual(trip["qoa"], "13:20")
		self.assertEqual(trip["own_leg"], "Outward")

	def test_absent_rider_gives_way_to_the_reliever(self):
		reliever = self.employees[11]
		absent = self.employees[1]
		self._manifest(today(), [
			{"trip_id": "LBT-1"},
			{"trip_id": "LBT-1", "employee": absent, "attendance_status": "Absent",
				"reliever_employee": reliever, "requires_reliever": 1},
			{"trip_id": "LBT-1", "attendance_status": "Absent"},
			{"trip_id": "LBT-1", "attendance_status": "Present", "qoa_status": "Fail"},
		])
		trip = self._trips()["LBT-1"]
		names = frappe.db.get_value("Employee", reliever, "employee_name"), frappe.db.get_value("Employee", absent, "employee_name")
		self.assertEqual(len(trip["passengers"]), 2)
		sub = [p for p in trip["passengers"] if p.get("is_reliever")]
		self.assertEqual(sub, [{"name": names[0], "drop_off": "Site A", "is_reliever": 1, "replaces": names[1]}])
		body = frappe.as_json(trip)
		for leaked in ("Absent", "Present", "Fail", "attendance_status", "qoa_status"):
			self.assertNotIn(leaked, body)

	def test_mixed_trip_shows_its_own_leg(self):
		out = self._shipment("LBT-SHIP-1", trip_direction="Mixed", pre_merge_trip_direction="Return")
		other = self._shipment("LBT-SHIP-2", trip_direction="Mixed", pre_merge_trip_direction="Outward")
		self._manifest(today(), [
			{"trip_id": "LBT-1", "transportation_shipment": out, "employee_action": "Dropping Off"},
			{"trip_id": "LBT-1", "transportation_shipment": other, "camp": self.there.name},
		])
		trip = self._trips()["LBT-1"]
		self.assertEqual((trip["direction"], trip["own_leg"]), ("Mixed", "Return"))
		self.assertEqual(trip["passengers"][0]["drop_off"], self.here.accommodation)

	def test_vehicle_capacity_and_driver_fallback(self):
		self._manifest(today(), [{"trip_id": "LBT-1"}])
		trip = self._trips()["LBT-1"]
		vehicle = frappe.db.get_value(
			"Vehicle", self.vehicle,
			["custom_max_passenger_capacity", "license_plate", "one_fm_vehicle_type", "employee"], as_dict=True,
		)
		driver = frappe.db.get_value("Employee", vehicle.employee, ["employee_name", "cell_number"], as_dict=True)
		self.assertEqual(trip["capacity"], vehicle.custom_max_passenger_capacity)
		self.assertEqual(trip["license_plate"], vehicle.license_plate)
		self.assertEqual(trip["vehicle_type"], vehicle.one_fm_vehicle_type)
		self.assertEqual(trip["driver"], driver.employee_name)
		self.assertEqual(trip["driver_mobile"], driver.cell_number)

	def test_manifest_driver_wins_over_vehicle_employee(self):
		doc = self._manifest(today(), [{"trip_id": "LBT-1"}])
		frappe.db.set_value("Transportation Manifest", doc.name, "driver_name", self.employees[10])
		trip = self._trips()["LBT-1"]
		self.assertEqual(trip["driver"], frappe.db.get_value("Employee", self.employees[10], "employee_name"))

	def test_paired_return_found_through_pair_group(self):
		out = self._shipment("LBT-SHIP-O", trip_direction="Outward", pair_group="LBT-PAIR")
		back = self._shipment("LBT-SHIP-R", trip_direction="Return", pair_group="LBT-PAIR")
		lone = self._shipment("LBT-SHIP-L", trip_direction="Outward", pair_group="LBT-ALONE")
		self._manifest(today(), [
			{"trip_id": "LBT-1", "transportation_shipment": out},
			{"trip_id": "LBT-3", "transportation_shipment": lone},
			{"trip_id": "LBT-2", "transportation_shipment": back, "trip_time": "22:40",
				"employee_action": "Dropping Off", "camp": self.there.name},
		])
		trips = self._trips()
		self.assertEqual(trips["LBT-1"]["paired_return"], {"trip_name": "LBT-2", "trip_time": "22:40"})
		self.assertIsNone(trips["LBT-3"]["paired_return"])

	def test_board_needs_manifest_read(self):
		frappe.set_user("Guest")
		self.assertRaises(frappe.PermissionError, get_lobby_board, self.here.name)
