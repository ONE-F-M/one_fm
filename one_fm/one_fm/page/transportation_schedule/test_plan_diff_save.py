# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The board loads and saves through Route Plan Assignment records.

The load must hand the board exactly what it received while the assignments were a
child table, and a save must write only the cards the planner changed and the runs
those cards left or joined.
"""

import json
import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	load_assignments,
	save_assignments,
)
from one_fm.operations.doctype.route_plan.route_plan import (
	diff_cards,
	get_plan_rows,
)
from one_fm.operations.doctype.route_plan.test_route_plan import pin_three_passenger_seats
from one_fm.operations.doctype.route_plan_assignment.test_route_plan_assignment import (
	make_card_shipment,
	make_route_plan,
)

# What load_assignments returned on the code before the change for the plan in "rows",
# captured by running that code over these rows.
FIXTURE = json.loads(
	(pathlib.Path(__file__).parent / "load_assignments_fixture.json").read_text()
)
# Queries a load may make. The child-table load made two reads of the plan plus one for
# the shipments' names; a load now reads the header, the rows and the same names.
LOAD_QUERY_BUDGET = 6


def _store_fixture_rows(plan):
	"""The fixture rows, as child rows linked by the patch when the site still has the
	child-table columns, otherwise straight in as records."""
	from one_fm.patches.v15_0 import route_plan_assignment_standalone

	as_child = frappe.db.has_column("Route Plan Assignment", "parent")
	now = now_datetime()
	fields = list(FIXTURE["rows"][0]) + ["creation", "modified", "owner", "modified_by"]
	fields += ["parent", "parenttype", "parentfield"] if as_child else ["route_plan"]
	values = []
	for row in FIXTURE["rows"]:
		value = list(row.values()) + [now, now, "Administrator", "Administrator"]
		value += [plan, "Route Plan", "assignments"] if as_child else [plan]
		values.append(value)
	frappe.db.bulk_insert("Route Plan Assignment", fields=fields, values=values)
	if as_child:
		route_plan_assignment_standalone.execute()


def _vehicles(count):
	names = frappe.get_all("Vehicle", limit=count, pluck="name", order_by="name asc")
	if len(names) < count:
		raise frappe.ValidationError(f"needs {count} vehicles")
	return names


def _item(card, vehicle, start="06:00", end="07:00", trip=None, headcount=1, **extra):
	return {
		"cardId": card, "vehicleId": vehicle, "direction": "OUTBOUND",
		"start": f"2026-11-01T{start}:00.000Z", "end": f"2026-11-01T{end}:00.000Z",
		"tripId": trip, "tripName": trip, "headcount": headcount, **extra,
	}


def _save(plan, items, legs=None):
	return save_assignments(plan, json.dumps(items), "[]", json.dumps(legs or {}))


def _stamps(plan):
	return {row.card_id: str(row.modified) for row in get_plan_rows(plan, fields=["card_id", "modified"])}


class TestTheLoadIsUnchanged(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		# Once per class: the fixture rows have fixed names, and this class's tests share
		# one transaction.
		super().setUpClass()
		cls.plan = make_route_plan()
		_store_fixture_rows(cls.plan)

	def test_the_board_receives_what_it_did_before(self):
		result = load_assignments(self.plan)

		for item in result["swim_items"]:
			self.assertIn("rowModified", item)
			item.pop("rowModified")
		self.assertEqual(json.loads(json.dumps(result["swim_items"], default=str)), FIXTURE["swim_items"])
		self.assertEqual(json.loads(json.dumps(result["leg_timings"], default=str)), FIXTURE["leg_timings"])
		# A set on the old code, so its order was never fixed.
		self.assertEqual(sorted(result["assigned_cards"]), FIXTURE["assigned_cards"])

	def test_the_stops_of_each_trip_keep_their_order(self):
		def order(items):
			trips = {}
			for item in items:
				trips.setdefault(item["tripId"], []).append(item["cardId"])
			return trips

		self.assertEqual(order(load_assignments(self.plan)["swim_items"]), order(FIXTURE["swim_items"]))

	def test_the_load_reads_the_plan_in_a_handful_of_queries(self):
		load_assignments(self.plan)  # warm the meta cache

		with self.assertQueryCount(LOAD_QUERY_BUDGET):
			load_assignments(self.plan)

	def test_an_empty_plan_loads_empty_lanes(self):
		result = load_assignments(make_route_plan())

		self.assertEqual(
			(result["status"], result["swim_items"], result["leg_timings"], result["assigned_cards"]),
			("ok", [], {}, []),
		)


class TestTheIdentityRule(FrappeTestCase):
	"""A card is its card_id; only what the planner sets makes it changed."""

	def _row(self, **values):
		row = frappe._dict(
			card_id="C1", vehicle="V1", trip_group="T1", trip_name="S-101", transit_minutes=5,
			buffer_minutes=0, direction="OUTBOUND", start_time="2026-11-01T06:00:00.000Z",
			end_time="2026-11-01T07:00:00.000Z", stop_index=1, headcount=3, site="A",
		)
		row.update(values)
		return row

	def test_the_same_card_rewritten_by_the_board_is_unchanged(self):
		stored = {"C1": self._row()}
		# The board rebuilds the stamp text, renumbers stops 1..N and sends the live count.
		board = {"C1": self._row(start_time="2026-11-01T06:00:00Z", stop_index=4, headcount=9,
								 site="", trip_group="T1", transit_minutes="5")}

		self.assertEqual(diff_cards(stored, board), ([], [], []))

	def test_a_moved_or_retimed_card_is_changed(self):
		stored = {"C1": self._row()}

		for change in ({"vehicle": "V2"}, {"start_time": "2026-11-01T06:05:00.000Z"},
					   {"trip_name": "S-102"}, {"buffer_minutes": 2}, {"direction": "RETURN"}):
			self.assertEqual(diff_cards(stored, {"C1": self._row(**change)}), ([], ["C1"], []), change)

	def test_a_new_lifespan_date_is_a_change(self):
		stored = {"C1": self._row()}

		self.assertEqual(
			diff_cards(stored, {"C1": self._row(end_time="2026-11-09T07:00:00.000Z")}),
			([], ["C1"], []),
		)

	def test_new_and_removed_cards(self):
		self.assertEqual(diff_cards({"C1": self._row()}, {"C2": self._row(card_id="C2")}),
						 (["C2"], [], ["C1"]))


class TestASaveWritesOnlyWhatChanged(FrappeTestCase):
	def setUp(self):
		try:
			self.v1, self.v2, self.v3 = _vehicles(3)
		except frappe.ValidationError:
			self.skipTest("needs three vehicles")
		self.plan = make_route_plan()
		self.board = [
			_item("CARD-1", self.v1, "06:00", "06:30", trip="T-1"),
			_item("CARD-2", self.v1, "06:30", "07:00", trip="T-1"),
			_item("CARD-3", self.v1, "09:00", "10:00"),
			_item("CARD-4", self.v3, "06:00", "07:00", trip="T-4"),
		]
		_save(self.plan, self.board)

	def test_moving_one_card_writes_only_its_journeys(self):
		before = _stamps(self.plan)
		self.board[2]["vehicleId"] = self.v2

		_save(self.plan, self.board)

		after = _stamps(self.plan)
		self.assertNotEqual(after["CARD-3"], before["CARD-3"])
		# Same vehicle, other run, and another vehicle entirely: untouched.
		self.assertEqual(after["CARD-1"], before["CARD-1"])
		self.assertEqual(after["CARD-4"], before["CARD-4"])

	def test_saving_the_board_as_loaded_writes_nothing(self):
		loaded = load_assignments(self.plan)
		before = (_stamps(self.plan), frappe.db.get_value("Route Plan", self.plan, "modified"))

		result = save_assignments(
			self.plan, json.dumps(loaded["swim_items"]), "[]", json.dumps(loaded["leg_timings"])
		)

		self.assertEqual(result.get("unchanged"), 1)
		self.assertEqual((_stamps(self.plan), frappe.db.get_value("Route Plan", self.plan, "modified")), before)

	def test_a_new_card_is_inserted_and_a_removed_one_deleted(self):
		board = self.board[:3] + [_item("CARD-5", self.v2)]

		result = _save(self.plan, board)

		self.assertEqual(set(_stamps(self.plan)), {"CARD-1", "CARD-2", "CARD-3", "CARD-5"})
		self.assertEqual(result["changed"], {"inserted": 1, "updated": 0, "deleted": 1})
		self.assertIn("CARD-5", result["modified"])

	def test_a_real_save_stamps_the_plan_header(self):
		frappe.db.set_value("Route Plan", self.plan, "last_modified_at", "2026-01-01 00:00:00")
		self.board[0]["start"] = "2026-11-01T05:55:00.000Z"

		_save(self.plan, self.board)

		header = frappe.db.get_value("Route Plan", self.plan,
									 ["last_modified_by_user", "last_modified_at"], as_dict=True)
		self.assertEqual(header.last_modified_by_user, frappe.session.user)
		self.assertGreater(str(header.last_modified_at), "2026-01-01 00:00:00")


class TestARefusedSaveStoresNothing(FrappeTestCase):
	VEHICLE = "VHL-L-0022"

	def test_an_overloaded_bus_leaves_the_plan_as_it_was(self):
		if not frappe.db.exists("Vehicle", self.VEHICLE):
			self.skipTest(f"Fixture vehicle {self.VEHICLE} missing on this site")
		pin_three_passenger_seats(self.VEHICLE)
		# Shipment-backed: a run is judged only when its cards change, and cards are told
		# apart by their shipment.
		cards = [make_card_shipment(n) for n in (1, 1, 5)]
		if not all(cards):
			self.skipTest("needs an Accommodation and a Location")
		plan = make_route_plan()
		board = [_item(f"TSHIP-{cards[0]}", self.VEHICLE, trip="T-1"),
				 _item(f"TSHIP-{cards[1]}", self.VEHICLE, trip="T-1")]
		_save(plan, board)
		before = (
			_stamps(plan), frappe.db.get_value("Route Plan", plan, ["modified", "last_modified_at"]),
			frappe.get_all("Transportation Shipment", filters={"name": ["in", cards]},
						   fields=["name", "status"], order_by="name"),
		)

		with self.assertRaises(frappe.ValidationError) as caught:
			_save(plan, board + [_item(f"TSHIP-{cards[2]}", self.VEHICLE, trip="T-1", headcount=5)])

		self.assertIn("Capacity Exceeded", str(caught.exception))
		self.assertEqual(
			(
				_stamps(plan), frappe.db.get_value("Route Plan", plan, ["modified", "last_modified_at"]),
				frappe.get_all("Transportation Shipment", filters={"name": ["in", cards]},
							   fields=["name", "status"], order_by="name"),
			),
			before,
		)


class TestTheCampLegsOfATouchedRun(FrappeTestCase):
	"""Stored the same way the full rebuild stored them."""

	def setUp(self):
		vehicle = frappe.get_all("Vehicle", filters={"transport_stop_vehicle": 1}, limit=1, pluck="name")
		site = frappe.get_all("Location", limit=1, pluck="name")
		camp = frappe.get_all("Accommodation", limit=1, pluck="name")
		if not (vehicle and site and camp):
			self.skipTest("needs a transport vehicle, a Location and an Accommodation")
		self.vehicle = vehicle[0]
		self.shipments = []
		for start in ("08:00:00", "09:00:00"):
			doc = frappe.new_doc("Transportation Shipment")
			doc.update({"status": "Unassigned", "trip_direction": "Outward", "start_time": start,
						"end_time": "20:00:00", "stop_location": site[0], "accommodation": camp[0],
						"generation_key": frappe.generate_hash("TS-RPA", 10)})
			doc.append("transportation_shipment_employee", {"employee_id": "RPA-1", "employee_name": "Rider"})
			doc.flags.ignore_mandatory = True
			doc.flags.ignore_links = True
			doc.insert(ignore_permissions=True)
			self.shipments.append(doc.name)

	def test_the_stored_camp_legs_are_what_the_rebuild_produces(self):
		from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
			_stamp_leg_details,
		)

		plan = make_route_plan()
		board = [
			_item(f"TSHIP-{name}", self.vehicle, start, end, trip="RUN-1")
			for name, (start, end) in zip(self.shipments, (("05:00", "05:30"), ("05:40", "06:10")))
		]
		legs = {"RUN-1": {"departure": "2026-11-01T04:30:00.000Z", "camps": {}}}
		_save(plan, board, legs)

		stored = [row for row in get_plan_rows(plan) if row.is_camp_leg]
		expected = _stamp_leg_details(
			[frappe._dict(row) for row in get_plan_rows(plan) if not row.is_camp_leg], legs
		)
		fields = ("card_id", "stop_index", "action_type", "boarding_count", "drop_off_count",
				  "start_time", "end_time", "transit_minutes", "buffer_minutes", "is_home_leg")
		self.assertTrue(expected)
		self.assertEqual(
			[{f: row.get(f) for f in fields} for row in stored],
			[{f: row.get(f) for f in fields} for row in expected],
		)
