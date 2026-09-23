# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002789: one tap checks in everyone still unchecked at a boarding stop."""

import json
import shutil
import subprocess

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.api.doc_methods.transportation_manifest import PRESENT, QOA_PASS

HARNESS = frappe.get_app_path("one_fm", "tests", "js", "bulk_present_harness.js")
PAGE = frappe.get_app_path(
	"one_fm", "one_fm", "page", "transportation_manifest_page", "transportation_manifest_page.js"
)


def _button(employees, checker_state=None):
	"""Run the SHIPPED helpers and report what the stop header would draw."""
	out = subprocess.run(
		[
			"node",
			HARNESS,
			json.dumps({"employees": employees, "checkerState": checker_state or {}}),
		],
		capture_output=True,
		text=True,
		env={"PATH": "/usr/bin:/bin:/usr/local/bin"},
		check=True,
	)
	return json.loads(out.stdout)


class TestWhichChipsTheButtonPicksUp(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not shutil.which("node"):
			raise cls.failureException("node is needed to run the shipped rule")
		cls.stop = [
			{"row_id": "r1", "name": "Dilli"},
			{"row_id": "r2", "name": "Ram"},
			{"row_id": "r3", "name": "Bishnu"},
		]

	def test_it_picks_up_everybody_on_an_untouched_stop(self):
		self.assertEqual(_button(self.stop)["pending"], ["r1", "r2", "r3"])

	def test_it_leaves_a_chip_the_driver_already_decided_on(self):
		"""The action means "everyone I have not marked yet is here". Overwriting an
		Absent entered a moment ago would undo the one thing the driver did on purpose."""
		state = {"r1": {"attendance": "Absent"}, "r2": {"attendance": "Present"}}
		self.assertEqual(_button(self.stop, state)["pending"], ["r3"])

	def test_a_chip_with_a_failed_qoa_but_no_attendance_is_still_pending(self):
		"""Attendance is what decides; a stale qoa alone has not checked anybody in."""
		self.assertEqual(_button(self.stop, {"r1": {"qoa": "Fail"}})["pending"], ["r1", "r2", "r3"])

	def test_a_fully_checked_stop_gets_no_button(self):
		state = {row["row_id"]: {"attendance": "Present"} for row in self.stop}
		result = _button(self.stop, state)
		self.assertEqual(result["pending"], [])
		self.assertEqual(result["html"], "")

	def test_the_button_counts_only_who_is_left(self):
		state = {"r1": {"attendance": "Present"}}
		self.assertIn("Mark All Present (2)", _button(self.stop, state)["html"])

	def test_the_row_ids_ride_on_a_data_attribute(self):
		"""A row name in an onclick string is one apostrophe away from breaking the card."""
		html = _button(self.stop)["html"]
		self.assertIn("data-rows=", html)
		self.assertIn("window._mfst_markAllPresent(this)", html)

	def test_a_plain_string_employee_is_handled(self):
		"""Some stops carry names rather than row objects; those have no row to check in."""
		self.assertEqual(_button(["Dilli"], {"Dilli": {"attendance": "Present"}})["pending"], [])


class TestTheStopHeader(FrappeTestCase):
	def setUp(self):
		self.source = frappe.read_file(PAGE)

	def test_the_button_is_offered_on_an_active_stop_only(self):
		"""A locked or completed stop is not one anybody is checking in at."""
		self.assertIn("const bulkBtn = isActive ? bulkPresentBtnHtml(employees) : \"\";", self.source)

	def test_it_sits_beside_the_tap_hint(self):
		header = self.source.split('class="mfst-depart-emp-header"', 1)[1].split("</div>`", 1)[0]
		self.assertIn("Tap name to check in", self.source)
		self.assertIn("${bulkBtn}", header)

	def test_a_double_tap_cannot_send_the_stop_twice(self):
		handler = self.source.split("window._mfst_markAllPresent", 1)[1]
		self.assertIn('$(button).prop("disabled", true);', handler)

	def test_the_chips_are_redrawn_from_the_saved_rows(self):
		handler = self.source.split("window._mfst_markAllPresent", 1)[1]
		self.assertIn("window.checkerState[row.name]", handler)
		self.assertIn("renderRoute(activeView)", handler)


class TestTheEndpoint(FrappeTestCase):
	def test_it_stamps_present_and_pass(self):
		self.assertEqual(PRESENT, "Present")
		self.assertEqual(QOA_PASS, "Pass")

	def test_it_is_a_post(self):
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "one_fm", "api", "doc_methods", "transportation_manifest.py"
			)
		)
		bulk = source.split("def mark_manifest_rows_present", 1)[0]
		self.assertTrue(bulk.rstrip().endswith('@frappe.whitelist(methods=["POST"])'))

	def test_it_saves_the_manifest_once(self):
		"""Twenty chips checked in one at a time is twenty reads and twenty saves of the
		same document - slow at a departure, and the shape WI-002538's retry exists for."""
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "one_fm", "api", "doc_methods", "transportation_manifest.py"
			)
		)
		bulk = source.split("def _apply_bulk_present", 1)[1]
		self.assertEqual(bulk.count("doc.save()"), 1)
		self.assertIn('doc.check_permission("write")', bulk)

	def test_it_replays_on_a_save_conflict(self):
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "one_fm", "api", "doc_methods", "transportation_manifest.py"
			)
		)
		bulk = source.split("def mark_manifest_rows_present", 1)[1].split("def _apply_bulk_present", 1)[0]
		self.assertIn("retry_on_stale_timestamp", bulk)

	def test_it_refuses_rows_from_more_than_one_manifest(self):
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "one_fm", "api", "doc_methods", "transportation_manifest.py"
			)
		)
		self.assertIn("belong to more than one manifest", source)
