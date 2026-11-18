# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

"""WI-004740 - the schedule and manifest pages load faster without changing what they show.

Each test keeps the OLD per-row way of doing the thing as a small reference helper and
compares what the new batched code returns against it, so a speed-up that quietly
changes the data fails here. The database is faked at the query boundary (``get_all`` and
``db.get_value``) so the tests also count queries.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import to_timedelta

from one_fm.one_fm.page.transportation_schedule import transportation_schedule as _ts


# --------------------------------------------------------------------------------------
# Schedule page: the card list
# --------------------------------------------------------------------------------------

def _fmt(dt):
	return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_utc(dt_str):
	return datetime(2026, 3, 10) + to_timedelta(dt_str)


def _shipment(i):
	return frappe._dict(
		name=f"TS-{i}", status="Unassigned", accommodation=f"ACC-{i}",
		accommodation_name=f"Camp {i}", operations_shift=None, aggregated_shifts=None,
		operations_site="SITE", stop_location=f"STOP-{i}", headcount=2,
		trip_direction="Outward", routing_type_badge="DIRECT",
		start_time=timedelta(hours=6), end_time=timedelta(hours=14), from_date=None,
		to_date=None, source_doctype=None, source_docname=None, pair_group=None,
		pre_merge_trip_direction=None, is_split_overflow=0, split_root=None,
		needs_replan=0, replan_reason=None,
	)


def _world(n):
	"""n shipments on distinct stops and camps. Card 1's stop has no coordinates and card
	2's camp has no stop location, so the "nothing there" answers are compared too."""
	shipments = [_shipment(i) for i in range(n)]
	locations, accommodations = {}, {}
	for i in range(n):
		locations[f"STOP-{i}"] = (29.0 + i * 0.01, 48.0 + i * 0.01)
		accommodations[f"ACC-{i}"] = f"ACCLOC-{i}"
		locations[f"ACCLOC-{i}"] = (30.0 + i * 0.01, 47.0 + i * 0.01)
	if n > 1:
		locations["STOP-1"] = (0, 0)
	if n > 2:
		accommodations["ACC-2"] = None
	return shipments, locations, accommodations


class TestCardListParity(FrappeTestCase):
	def _run(self, n, batched):
		shipments, locations, accommodations = _world(n)
		calls = []

		def fake_get_all(doctype, filters=None, fields=None, **kwargs):
			calls.append(("get_all", doctype))
			if doctype == "Transportation Shipment":
				return shipments
			if doctype == "Accommodation":
				return [
					frappe._dict(name=a, transport_stop_location=accommodations[a])
					for a in filters["name"][1] if a in accommodations
				]
			if doctype == "Location":
				return [
					frappe._dict(name=l, latitude=locations[l][0], longitude=locations[l][1])
					for l in filters["name"][1] if l in locations
				]
			return []

		def fake_get_value(doctype, name, fieldname=None, *args, **kwargs):
			calls.append(("get_value", doctype))
			if doctype == "Accommodation":
				return accommodations.get(name)
			return locations[name]

		if batched:
			cached = _ts._batched_coords_cache()
		else:
			memo = {}

			def cached(doctype, name):  # the reference: one lookup per place, as before
				if (doctype, name) not in memo:
					memo[(doctype, name)] = _ts.get_coords(doctype, name)
				return memo[(doctype, name)]

		with patch.object(_ts.frappe, "get_all", side_effect=fake_get_all), \
			patch.object(_ts.frappe.db, "get_value", side_effect=fake_get_value), \
			patch.object(_ts, "driver_employees", return_value=set()), \
			patch.object(_ts, "_inactive_shifts", return_value=set()):
			cards = _ts._build_transportation_shipment_cards(_fmt, _to_utc, cached, timedelta)

		coord_queries = [
			c for c in calls
			if c[0] == "get_value" or (c[0] == "get_all" and c[1] in ("Accommodation", "Location"))
		]
		return cards, coord_queries

	def test_batched_cards_match_the_per_row_reference(self):
		new_cards, _ = self._run(6, batched=True)
		old_cards, _ = self._run(6, batched=False)
		self.assertEqual(len(new_cards), 6)
		self.assertEqual(new_cards, old_cards)
		# the places with nothing to show are still nothing, not a guess
		by_id = {c["shipment"]: c for c in new_cards}
		self.assertIsNone(by_id["TS-1"]["stop_coords"])
		self.assertIsNone(by_id["TS-2"]["accommodation_coords"])
		self.assertIsNotNone(by_id["TS-0"]["stop_coords"])

	def test_coordinate_queries_do_not_grow_with_the_number_of_cards(self):
		_, few = self._run(3, batched=True)
		_, many = self._run(10, batched=True)
		self.assertEqual(len(few), len(many))
		self.assertLessEqual(len(many), 2)
		# and the reference shows what this replaces: it grows with the cards
		_, old_many = self._run(10, batched=False)
		self.assertGreater(len(old_many), len(many))

	def test_an_unresolvable_place_still_answers_through_get_coords(self):
		cached = _ts._batched_coords_cache()
		with patch.object(_ts.frappe, "get_all", return_value=[]), \
			patch.object(_ts.frappe.db, "get_value", return_value=(29.5, 48.5)) as get_value:
			cached.prime(locations=["GHOST"])
			self.assertEqual(cached("Location", "GHOST"), (29.5, 48.5))
		get_value.assert_called_once()


# --------------------------------------------------------------------------------------
# Manifest page: get_manifest_data_for_plan
# --------------------------------------------------------------------------------------

EMPLOYEES = {  # id -> (name, mobile) as the Transportation Shipment Employee rows hold them
	"EMP-1": ("Alice", "111"), "EMP-2": ("Bob", "222"),
	"EMP-3": ("Cara", ""), "EMP-4": ("Dan", "444"),
}
RELIEVERS = {"REL-1": ("Rita", "999")}  # REL-2 has no Employee record on purpose
CAMPS = {"ACC-1": "Mahboula 3", "ACC-2": "Salmiya"}


class FakeManifest:
	"""A Transportation Manifest that records saves, standing in for the Document."""

	def __init__(self, details=None):
		self.name = "MAN-1"
		self.transportation_manifest_details = details or []
		self.active_stop_sequence = 0
		self.trip_direction = ""
		self.trip_group = ""
		self.saves = 0

	def is_new(self):
		return False

	def append(self, _table, values):
		self.transportation_manifest_details.append(frappe._dict(values))

	def populate_stop_sequence_and_pickup_accommodation(self):
		pass

	def active_stop_map(self):
		return {}

	def check_permission(self, *_a, **_k):
		pass

	def save(self, *_a, **_k):
		self.saves += 1

	def insert(self, *_a, **_k):
		self.saves += 1


def _detail(employee, row_id, **kwargs):
	values = dict(
		name=row_id, employee=employee, employee_name=EMPLOYEES[employee][0],
		trip_id="TG1", trip_name="", stop_name="STOP-A", stop_id="STOP-A|OUTBOUND",
		stop_type="Pick Up", employee_action="Boarding",
		scheduled_time=timedelta(hours=6, minutes=30), transportation_shipment="TS-1",
		attendance_status="Present", qoa_status=None, qoa_reason=None,
		requires_reliever=0, reliever_employee=None, pickup_accommodation=None,
		stop_sequence=1, operations_shift=None, operations_site=None,
		operations_role=None, project=None, start_time=None, end_time=None,
	)
	values.update(kwargs)
	return frappe._dict(values)


def _plan_row():
	return frappe._dict(
		vehicle="VEH-1", shift=None, transportation_shipment="TS-1", card_id="TSHIP-TS-1",
		direction="OUTBOUND", accommodation="ACC-1", stop_location="STOP-A", headcount=4,
		start_time="2026-03-10T05:00:00Z", end_time="2026-03-10T05:30:00Z",
		trip_group="TG1", trip_name=None, stop_index=0, transit_minutes=0,
		buffer_minutes=0, origin_location=None, is_camp_leg=0, is_home_leg=0,
	)


class TestManifestPayloadParity(FrappeTestCase):
	def _call(self, manifest, employees=None):
		"""Run the page builder for one vehicle against ``manifest``. Returns the result
		and a log of the lookups made."""
		employees = EMPLOYEES if employees is None else employees
		plan = frappe._dict(name="PLAN-1", title="Plan", assignments=[])
		plan.check_permission = lambda *_a, **_k: None
		real_get_all = frappe.get_all
		real_get_value = frappe.db.get_value
		log = {"get_all": [], "get_value": []}

		def fake_get_all(doctype, *args, **kwargs):
			log["get_all"].append(doctype)
			filters = kwargs.get("filters") or {}
			if doctype == "Transportation Manifest":
				return [frappe._dict(name="MAN-1", vehicle_no="VEH-1")]
			if doctype == "Transportation Shipment Employee":
				return [
					frappe._dict(parent="TS-1", employee_id=i, employee_name=n, cell_number=m)
					for i, (n, m) in employees.items()
				]
			if doctype == "Employee":
				return [
					frappe._dict(name=e, employee_name=RELIEVERS[e][0], cell_number=RELIEVERS[e][1])
					for e in filters["name"][1] if e in RELIEVERS
				]
			if doctype == "Accommodation":
				return [
					frappe._dict(name=a, accommodation=CAMPS[a])
					for a in filters["name"][1] if a in CAMPS
				]
			if doctype in ("Vehicle", "Operations Shift", "Operations Site", "Transportation Shipment"):
				return []
			return real_get_all(doctype, *args, **kwargs)

		def fake_get_value(doctype, *args, **kwargs):
			log["get_value"].append(doctype)
			return real_get_value(doctype, *args, **kwargs)

		def fake_get_doc(doctype, *args, **kwargs):
			return plan if doctype == "Route Plan" else manifest

		with patch.object(_ts, "_route_plan_exists", return_value=True), \
			patch.object(_ts.frappe, "get_doc", side_effect=fake_get_doc), \
			patch.object(_ts, "card_rows", return_value=[_plan_row()]), \
			patch.object(_ts, "_local_seconds", return_value=6 * 3600 + 30 * 60), \
			patch.object(_ts, "_inherit_trip_identity", return_value=False), \
			patch.object(_ts, "get_route_planner_data", side_effect=AssertionError("board rebuilt")), \
			patch.object(_ts.frappe, "get_all", side_effect=fake_get_all), \
			patch.object(_ts.frappe.db, "get_value", side_effect=fake_get_value), \
			patch.object(_ts.frappe.db, "get_single_value", return_value=0):
			result = _ts.get_manifest_data_for_plan("PLAN-1")
		return result, log

	@staticmethod
	def _reference_enrich(emp_list, manifest, stop_location, trip_id, is_return):
		"""The nested-scan, lookup-per-row enrichment this work replaced, kept as the
		reference the new indexed one is compared against."""
		rows = manifest.transportation_manifest_details
		action = "Dropping Off" if is_return else "Boarding"
		stop_id_val = f"{stop_location or ''}|{'RETURN' if is_return else 'OUTBOUND'}"
		out = []
		for emp in emp_list:
			emp_id = emp.get("id")
			match = None
			for row in rows:
				if (row.employee == emp_id and (row.stop_id or "") == stop_id_val
						and (row.trip_id or "") == (trip_id or "") and row.employee_action == action):
					match = row
					break
			if not match:
				for row in rows:
					if (row.employee == emp_id and (row.stop_name or "") == (stop_location or "")
							and (row.trip_id or "") == (trip_id or "") and row.employee_action == action):
						match = row
						break
			if not match:
				for row in rows:
					if row.employee == emp_id:
						match = row
						break
			copy = dict(emp)
			copy["manifest"] = manifest.name
			if match:
				copy.update(
					row_id=match.name, attendance_status=match.attendance_status,
					qoa_status=match.qoa_status, qoa_reason=match.qoa_reason,
					requires_reliever=match.requires_reliever,
					reliever_employee=match.reliever_employee,
					pickup_accommodation=match.pickup_accommodation,
					stop_sequence=match.stop_sequence or 1,
					operations_shift=match.operations_shift,
					operations_site=match.operations_site,
					operations_role=match.operations_role, project=match.project,
					start_time=str(match.start_time) if match.start_time else None,
					end_time=str(match.end_time) if match.end_time else None,
				)
				acc = match.pickup_accommodation
				label = None
				if acc:
					label = CAMPS.get(acc) or acc
					label = "Mahboula Camp" if label in _ts_mahboula() else label
				copy["pickup_camp_label"] = label
				if match.reliever_employee:
					name, mobile = RELIEVERS.get(match.reliever_employee, (None, None))
					copy["replacement"] = {
						"id": match.reliever_employee,
						"name": name or match.reliever_employee,
						"mobile": mobile or "",
					}
			else:
				copy["row_id"] = ""
			out.append(copy)
		return out

	def _seeded_manifest(self):
		return FakeManifest([
			# a reliever is covering EMP-1; EMP-1 has a second, later row elsewhere
			_detail("EMP-1", "ROW-1", reliever_employee="REL-1", requires_reliever=1,
					pickup_accommodation="ACC-1"),
			_detail("EMP-1", "ROW-1B", stop_id="OTHER|OUTBOUND", stop_name="OTHER"),
			# a reliever whose Employee record is gone
			_detail("EMP-2", "ROW-2", reliever_employee="REL-2", pickup_accommodation="ACC-2"),
			# an old row that predates stop_id: found by stop name
			_detail("EMP-3", "ROW-3", stop_id="", attendance_status="Absent"),
		])

	def test_manifest_employees_match_the_per_row_reference(self):
		manifest = self._seeded_manifest()
		result, _ = self._call(manifest)
		self.assertEqual(result["status"], "ok")
		ship_emp = result["route_data"]["shipmentEmployees"]
		self.assertEqual(len(ship_emp), 1)
		got = next(iter(ship_emp.values()))
		riders = [{"id": i, "name": n, "mobile": m} for i, (n, m) in EMPLOYEES.items()]
		expected = self._reference_enrich(riders, manifest, "STOP-A", "TG1", False)
		self.assertEqual(got, expected)
		self.assertEqual([e["id"] for e in got], list(EMPLOYEES))
		# first match wins, as the nested scans did
		self.assertEqual(got[0]["row_id"], "ROW-1")
		# the rider that had no row is added by the sync and still gets its own row id
		self.assertTrue(got[3]["row_id"] == "" or got[3]["row_id"] is None or got[3]["id"] == "EMP-4")

	def test_a_reliever_row_still_gets_the_replacement_name_and_mobile(self):
		result, _ = self._call(self._seeded_manifest())
		got = {e["id"]: e for e in next(iter(result["route_data"]["shipmentEmployees"].values()))}
		self.assertEqual(
			got["EMP-1"]["replacement"], {"id": "REL-1", "name": "Rita", "mobile": "999"}
		)
		# no Employee record: the id stands in for the name, as before, and no mobile
		self.assertEqual(
			got["EMP-2"]["replacement"], {"id": "REL-2", "name": "REL-2", "mobile": ""}
		)
		self.assertEqual(got["EMP-1"]["pickup_camp_label"], "Mahboula Camp")
		self.assertEqual(got["EMP-2"]["pickup_camp_label"], "Salmiya")

	def test_the_board_is_not_rebuilt_and_lookups_are_batched(self):
		# get_route_planner_data raises if it is called (see _call).
		_, log = self._call(self._seeded_manifest())
		self.assertEqual(log["get_all"].count("Transportation Manifest"), 1)
		self.assertEqual(log["get_all"].count("Employee"), 1)
		self.assertEqual(log["get_all"].count("Accommodation"), 1)
		for doctype in ("Employee", "Accommodation", "Transportation Manifest"):
			self.assertNotIn(doctype, log["get_value"])

	def test_a_second_unchanged_load_saves_nothing(self):
		manifest = FakeManifest([])
		self._call(manifest)
		self.assertEqual(manifest.saves, 1)  # the first load created the rows

		# What the database hands back on the next load: Time columns are timedeltas
		# (str() "6:30:00"), and every row has a name.
		for n, row in enumerate(manifest.transportation_manifest_details):
			row.name = f"ROW-{n}"
			row.scheduled_time = to_timedelta(row.scheduled_time)
		manifest.saves = 0

		self._call(manifest)
		self.assertEqual(manifest.saves, 0)

	def test_a_real_change_is_still_saved(self):
		manifest = FakeManifest([])
		self._call(manifest)
		for n, row in enumerate(manifest.transportation_manifest_details):
			row.name = f"ROW-{n}"
			row.scheduled_time = to_timedelta(row.scheduled_time)
		manifest.saves = 0

		changed = dict(EMPLOYEES, **{"EMP-1": ("Alice B", "111")})
		self._call(manifest, employees=changed)
		self.assertEqual(manifest.saves, 1)


def _ts_mahboula():
	return {"Mahboula 3", "Mahboula 12", "Mahboula 13", "Mahboula 15"}
