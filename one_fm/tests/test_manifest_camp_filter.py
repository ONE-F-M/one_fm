# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Camp filter, counters and trip labels on the manifest page, run from the shipped JS."""

import json
import shutil
import subprocess

import frappe
from frappe.tests.utils import FrappeTestCase

HARNESS = frappe.get_app_path("one_fm", "tests", "js", "manifest_camp_filter_harness.js")


def _stop(trip, raw, direction, kind="dropoff"):
	return {"type": kind, "tripId": trip, "tripName": trip, "raw": raw, "direction": direction}


def _emp(row_id, camp, action="Boarding"):
	return {"row_id": row_id, "name": row_id, "pickup_accommodation": camp, "employee_action": action}


FIXTURE = {
	"parsed": [
		{"label": "V1", "stops": [
			_stop("701", "a_0_X_OUTBOUND", "OUTBOUND"),
			_stop("702", "b_1_Y_RETURN", "RETURN", "pickup"),
		]},
		{"label": "V2", "stops": [_stop("201", "c_2_Z_MIXED", "MIXED")]},
	],
	"shipmentEmployees": {
		"a_0_X_OUTBOUND": [_emp("r1", "ACC-1"), _emp("r2", "ACC-1")],
		"b_1_Y_RETURN": [_emp("r3", "ACC-2", "Dropping Off")],
		"c_2_Z_MIXED": [_emp("r4", "ACC-1")],
	},
	"shipmentOwnDirections": {"c_2_Z_MIXED": "RETURN"},
	"checkerState": {"r1": {"attendance": "Present", "qoa": "Fail"}, "r4": {"attendance": "Present", "qoa": "Pass"}},
	"slots": [
		{"vehicles": 2, "trips": [{"trip_name": "701"}, {"trip_name": "201"}]},
		{"vehicles": 1, "trips": [{"trip_name": "702"}]},
	],
}


def _run(**overrides):
	args = dict(FIXTURE, **overrides)
	out = subprocess.run(
		["node", HARNESS, json.dumps(args)],
		capture_output=True, text=True, check=True,
		env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
	)
	return json.loads(out.stdout)


class TestCampFilter(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not shutil.which("node"):
			raise cls.failureException("node is needed to run the shipped helpers")

	def test_all_accommodations_keeps_every_trip(self):
		self.assertEqual(
			_run()["vehicles"],
			[{"label": "V1", "trips": ["701", "702"]}, {"label": "V2", "trips": ["201"]}],
		)

	def test_a_camp_keeps_only_its_trips(self):
		self.assertEqual(
			_run(accommodation="ACC-1")["vehicles"],
			[{"label": "V1", "trips": ["701"]}, {"label": "V2", "trips": ["201"]}],
		)

	def test_a_camp_without_trips_leaves_no_vehicle_trips(self):
		vehicles = _run(accommodation="ACC-9")["vehicles"]
		self.assertTrue(all(not v["trips"] for v in vehicles))

	def test_counters_for_a_camp(self):
		self.assertEqual(
			_run(accommodation="ACC-1")["counters"],
			{"trips": 2, "boarding": 3, "checked": 2, "failed": 1},
		)

	def test_counters_count_boarding_rows_only(self):
		self.assertEqual(_run()["counters"]["boarding"], 3)
		self.assertEqual(_run()["counters"]["trips"], 3)

	def test_counters_follow_checker_state(self):
		state = {"r1": {"attendance": "Absent"}}
		counters = _run(accommodation="ACC-1", checkerState=state)["counters"]
		self.assertEqual((counters["checked"], counters["failed"]), (0, 0))

	def test_direction_labels(self):
		self.assertEqual(
			_run(accommodation="ACC-1")["directions"],
			["Outward", "Return", "Mixed trip · Return leg"],
		)

	def test_slot_line(self):
		self.assertEqual(_run()["slotLines"], ["2 vehicles · 701, 201", "1 vehicle · 702"])
