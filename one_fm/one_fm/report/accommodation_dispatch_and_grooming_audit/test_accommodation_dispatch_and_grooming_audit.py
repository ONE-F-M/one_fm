# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import json
import os
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from one_fm.one_fm.report.accommodation_dispatch_and_grooming_audit import (
	accommodation_dispatch_and_grooming_audit as report,
)

MODULE = "one_fm.one_fm.report.accommodation_dispatch_and_grooming_audit.accommodation_dispatch_and_grooming_audit"


def _child(**kw):
	base = {
		"name": kw.get("employee", "x") + "-row",
		"parent": "TM-1",
		"idx": 1,
		"trip_id": "T-1",
		"stop_sequence": 1,
		"pickup_accommodation": "Mahboula Camp",
		"scheduled_time": "06:30:00",
		"employee": "EMP-1",
		"employee_name": "Binod Basnet",
		"attendance_status": None,
		"boarding_time": None,
		"qoa_status": None,
		"qoa_reason": None,
		"reliever_employee": None,
	}
	base.update(kw)
	return frappe._dict(base)


def _parent(**kw):
	base = {
		"name": "TM-1",
		"vehicle_no": "BUS-1",
		"license_plate": "PLATE-1",
		"driver_name": "EMP-D",
		"active_stop_by_trip": json.dumps({"T-1": 1}),
		"active_stop_sequence": 1,
	}
	base.update(kw)
	return frappe._dict(base)


class TestAccommodationDispatchAndGroomingAudit(FrappeTestCase):
	def run_report(self, parents, children, filters=None, names=None):
		filters = {"date": today(), **(filters or {})}
		names = names if names is not None else {"EMP-D": "Driver Dan", "EMP-2": "Mohit Lal Chaudhary"}
		with patch(f"{MODULE}.fetch_parents", return_value=parents), patch(
			f"{MODULE}.fetch_children", return_value=children
		), patch(f"{MODULE}.fetch_employee_names", return_value=names):
			return report.execute(filters)

	# ── scaffold ────────────────────────────────────────────────────────────

	def test_report_definition(self):
		path = os.path.join(os.path.dirname(report.__file__), "accommodation_dispatch_and_grooming_audit.json")
		with open(path) as f:
			doc = json.load(f)
		self.assertEqual(doc["report_type"], "Script Report")
		self.assertEqual(doc["is_standard"], "Yes")
		self.assertEqual(doc["module"], "One Fm")
		self.assertEqual(doc["ref_doctype"], "Transportation Manifest")
		self.assertEqual(doc["prepared_report"], 0)
		self.assertEqual(doc["add_total_row"], 0)
		self.assertNotIn("&", doc["name"])
		self.assertEqual(
			{r["role"] for r in doc["roles"]},
			{"System Manager", "Operations Manager", "Transportation Manager", "Transportation Supervisor", "Fleet Manager"},
		)

	def test_js_has_export_button_and_no_inline_styles(self):
		path = os.path.join(os.path.dirname(report.__file__), "accommodation_dispatch_and_grooming_audit.js")
		with open(path) as f:
			js = f.read()
		self.assertIn("initial_depth: 0", js)
		self.assertIn("Export Audit Report", js)
		self.assertLess(js.index("expand_all_rows"), js.index("export_report"))
		self.assertNotIn("style=", js)

	# ── AC1 scope ───────────────────────────────────────────────────────────

	def test_only_camp_departures_are_listed(self):
		children = [
			_child(),
			# Return leg: Dropping Off rows never reach the report (fetch is Boarding only),
			# so model the other excluded shapes: no accommodation at Stop 1, and a later stop.
			_child(employee="EMP-5", trip_id="T-SHUTTLE", pickup_accommodation=None),
			_child(employee="EMP-6", trip_id="T-LATE", stop_sequence=2),
		]
		_, data = self.run_report([_parent()], children)
		trips = [r for r in data if r["indent"] == 0]
		self.assertEqual([t["trip_id"] for t in trips], ["T-1"])

	def test_future_date_returns_empty(self):
		_, data = self.run_report([_parent()], [_child()], {"date": add_days(today(), 3)})
		self.assertEqual(data, [])

	# ── AC2 / AC3 passenger classification ──────────────────────────────────

	def test_attendance_and_appearance_classification(self):
		present_pass = report.classify_passenger(_child(attendance_status="Present", qoa_status="Pass"))
		self.assertEqual(present_pass["attendance"], "Present")
		self.assertEqual(present_pass["appearance"], "Eligible & Dispatched")

		fail = report.classify_passenger(
			_child(attendance_status="Present", qoa_status="Fail", qoa_reason="Uniform")
		)
		self.assertEqual(fail["appearance"], "Failed")
		self.assertEqual(fail["failure_reason"], "Uniform")
		self.assertEqual(fail["failed"], 1)

		uncovered = report.classify_passenger(_child(attendance_status="Absent"))
		self.assertEqual(uncovered["attendance"], "Absent (Uncovered)")

		covered = report.classify_passenger(
			_child(attendance_status="Absent", reliever_employee="EMP-2"), "Mohit Lal Chaudhary"
		)
		self.assertEqual(covered["attendance"], "Absent")
		self.assertEqual(covered["reliever"], "Binod Basnet \u2794 Mohit Lal Chaudhary")

	def test_warning_total_counts_appearance_failures(self):
		children = [
			_child(employee="EMP-1", attendance_status="Present", qoa_status="Fail", qoa_reason="Grooming"),
			_child(employee="EMP-3", employee_name="Three", attendance_status="Present", qoa_status="Fail", qoa_reason="Uniform"),
			_child(employee="EMP-4", employee_name="Four", attendance_status="Present", qoa_status="Pass"),
		]
		_, data = self.run_report([_parent()], children)
		trip = data[0]
		self.assertEqual(trip["compliance_warnings"], 2)
		self.assertEqual(trip["compliance_summary"], "1/3 Passed")
		self.assertEqual(trip["headcount"], 3)

	# ── AC4 two-level structure ─────────────────────────────────────────────

	def test_two_level_rows_and_trip_fields(self):
		_, data = self.run_report([_parent()], [_child(attendance_status="Present", qoa_status="Pass")])
		trip, passenger = data
		self.assertEqual(trip["indent"], 0)
		self.assertEqual(passenger["indent"], 1)
		self.assertEqual(passenger["parent_row"], trip["row_id"])
		self.assertEqual(trip["departure_time"], "06:30")
		self.assertEqual(trip["vehicle"], "PLATE-1")
		self.assertEqual(trip["driver"], "Driver Dan")
		self.assertEqual(trip["camp"], "Mahboula Camp")
		self.assertEqual(trip["lock_status"], "In Progress (Stop 1)")

	def test_lock_status(self):
		self.assertEqual(report.get_lock_status(0, 2), "Not Started")
		self.assertEqual(report.get_lock_status(2, 2), "In Progress (Stop 2)")
		self.assertEqual(report.get_lock_status(3, 2), "Completed")

	# ── AC5 filters ─────────────────────────────────────────────────────────

	def _mixed_children(self):
		return [
			_child(employee="EMP-1", trip_id="T-OK", attendance_status="Present", qoa_status="Pass"),
			_child(employee="EMP-3", employee_name="Absent Abe", trip_id="T-ABS", attendance_status="Absent"),
			_child(employee="EMP-4", employee_name="Fail Fay", trip_id="T-FAIL", attendance_status="Present",
				qoa_status="Fail", qoa_reason="Grooming"),
		]

	def _parent_all(self):
		return _parent(active_stop_by_trip=json.dumps({"T-OK": 1, "T-ABS": 1, "T-FAIL": 1}))

	def _trip_ids(self, data):
		return [r["trip_id"] for r in data if r["indent"] == 0]

	def test_compliance_filter(self):
		for option, expected in (
			("All Trips", ["T-OK", "T-ABS", "T-FAIL"]),
			("100% Passed Trips", ["T-OK"]),
			("Trips with Absentees", ["T-ABS"]),
			("Trips with Grooming/Uniform Fails", ["T-FAIL"]),
		):
			_, data = self.run_report([self._parent_all()], self._mixed_children(), {"compliance": option})
			self.assertEqual(self._trip_ids(data), expected, option)

	def test_camp_filter(self):
		children = [_child(trip_id="T-A"), _child(employee="EMP-9", trip_id="T-B", pickup_accommodation="Farwaniya Camp")]
		_, data = self.run_report([_parent()], children, {"camp": "Farwaniya Camp"})
		self.assertEqual(self._trip_ids(data), ["T-B"])

	def test_search_by_employee_vehicle_and_driver(self):
		parents = [self._parent_all()]
		_, data = self.run_report(parents, self._mixed_children(), {"search": "abe"})
		self.assertEqual(self._trip_ids(data), ["T-ABS"])
		self.assertEqual(len(data), 2)  # trip + the matching passenger

		_, data = self.run_report(parents, self._mixed_children(), {"search": "emp-4"})
		self.assertEqual(self._trip_ids(data), ["T-FAIL"])

		_, data = self.run_report(parents, self._mixed_children(), {"search": "plate-1"})
		self.assertEqual(len(self._trip_ids(data)), 3)

		_, data = self.run_report(parents, self._mixed_children(), {"search": "driver dan"})
		self.assertEqual(len(self._trip_ids(data)), 3)

		_, data = self.run_report(parents, self._mixed_children(), {"search": "nobody"})
		self.assertEqual(data, [])
