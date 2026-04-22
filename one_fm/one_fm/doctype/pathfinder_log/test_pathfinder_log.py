# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestPathfinderLog(FrappeTestCase):
	"""Unit tests for the Pathfinder Log editability API."""

	PROCESS_NAME = "_Test Process Editability"

	def setUp(self):
		"""Create a test Process record once per test."""
		if not frappe.db.exists("Process", self.PROCESS_NAME):
			frappe.get_doc({
				"doctype": "Process",
				"process_name": self.PROCESS_NAME,
				"description": "Test process for pathfinder editability checks",
				"process_owner": "Administrator",
				"business_analyst": "Administrator",
			}).insert(ignore_permissions=True)

	def tearDown(self):
		"""Clean up Pathfinder Logs created during tests."""
		frappe.db.delete(
			"Pathfinder Log",
			{"process_name": self.PROCESS_NAME},
		)
		frappe.db.commit()

	def _create_log(self, status="Backlog"):
		"""Helper to create a Pathfinder Log with a given status."""
		doc = frappe.get_doc({
			"doctype": "Pathfinder Log",
			"process_name": self.PROCESS_NAME,
			"goal_description": "Test goal",
			"type": "Incremental Changes",
			"status": status,
		})
		doc.insert(ignore_permissions=True)
		# Force status outside normal flow for test isolation
		frappe.db.set_value(
			"Pathfinder Log", doc.name,
			"status", status,
			update_modified=True,
		)
		frappe.db.commit()
		return doc.name

	# ── is_process_editable ────────────────────────────────────────

	def test_no_log_returns_not_editable(self):
		"""Process with no Pathfinder Log should not be editable."""
		from one_fm.one_fm.doctype.pathfinder_log.pathfinder_api import (
			is_process_editable,
		)

		result = is_process_editable(self.PROCESS_NAME)
		self.assertFalse(result["editable"])
		self.assertIsNone(result["pathfinder_log"])
		self.assertIsNone(result["status"])

	def test_active_log_returns_editable(self):
		"""Process with a non-Deployed log should be editable."""
		from one_fm.one_fm.doctype.pathfinder_log.pathfinder_api import (
			is_process_editable,
		)

		log_name = self._create_log("Active")

		result = is_process_editable(self.PROCESS_NAME)
		self.assertTrue(result["editable"])
		self.assertEqual(result["pathfinder_log"], log_name)
		self.assertEqual(result["status"], "Active")

	def test_completed_log_returns_not_editable(self):
		"""Process where all logs are Deployed should not be editable."""
		from one_fm.one_fm.doctype.pathfinder_log.pathfinder_api import (
			is_process_editable,
		)

		self._create_log("Deployed")

		result = is_process_editable(self.PROCESS_NAME)
		self.assertFalse(result["editable"])


	def test_mixed_completed_and_active(self):
		"""If one log is Deployed and another is active, process is editable."""
		from one_fm.one_fm.doctype.pathfinder_log.pathfinder_api import (
			is_process_editable,
		)

		self._create_log("Deployed")
		active_log = self._create_log("Active")

		result = is_process_editable(self.PROCESS_NAME)
		self.assertTrue(result["editable"])
		self.assertEqual(result["pathfinder_log"], active_log)

	# ── bulk_check_process_editable ────────────────────────────────

	def test_bulk_check_maps_correctly(self):
		"""Bulk API should return per-process editability."""
		from one_fm.one_fm.doctype.pathfinder_log.pathfinder_api import (
			bulk_check_process_editable,
		)
		import json

		self._create_log("Active")

		result = bulk_check_process_editable(
			json.dumps([self.PROCESS_NAME, "Nonexistent Process"])
		)

		self.assertIn(self.PROCESS_NAME, result)
		self.assertTrue(result[self.PROCESS_NAME]["editable"])

		self.assertIn("Nonexistent Process", result)
		self.assertFalse(result["Nonexistent Process"]["editable"])

	def test_bulk_check_invalid_json_raises(self):
		"""Malformed JSON should raise a validation error, not a 500."""
		from one_fm.one_fm.doctype.pathfinder_log.pathfinder_api import (
			bulk_check_process_editable,
		)

		with self.assertRaises(frappe.ValidationError):
			bulk_check_process_editable("not valid json {{{")

	def test_empty_process_name_raises(self):
		"""Calling is_process_editable with empty name should raise."""
		from one_fm.one_fm.doctype.pathfinder_log.pathfinder_api import (
			is_process_editable,
		)

		with self.assertRaises(frappe.ValidationError):
			is_process_editable("")


class TestSingleActiveLogValidation(FrappeTestCase):
	"""Ensure only one active (non-Deployed) Pathfinder Log per process."""

	PROCESS_A = "_Test Process Single Active A"
	PROCESS_B = "_Test Process Single Active B"

	def setUp(self):
		for proc in (self.PROCESS_A, self.PROCESS_B):
			if not frappe.db.exists("Process", proc):
				frappe.get_doc({
					"doctype": "Process",
					"process_name": proc,
					"description": "Test process for single-active validation",
					"process_owner": "Administrator",
					"business_analyst": "Administrator",
				}).insert(ignore_permissions=True)

	def tearDown(self):
		for proc in (self.PROCESS_A, self.PROCESS_B):
			frappe.db.delete("Pathfinder Log", {"process_name": proc})
		frappe.db.commit()

	def _create_log(self, process_name, status="Backlog"):
		doc = frappe.get_doc({
			"doctype": "Pathfinder Log",
			"process_name": process_name,
			"goal_description": "Test goal",
			"type": "Incremental Changes",
			"status": status,
		})
		doc.insert(ignore_permissions=True)
		if status != "Backlog":
			frappe.db.set_value(
				"Pathfinder Log", doc.name,
				"status", status,
				update_modified=True,
			)
			frappe.db.commit()
		return doc.name

	def test_first_log_succeeds(self):
		"""Creating the first non-Deployed log for a process should succeed."""
		name = self._create_log(self.PROCESS_A)
		self.assertTrue(frappe.db.exists("Pathfinder Log", name))

	def test_second_active_log_blocked(self):
		"""A second non-Deployed log for the same process should be blocked."""
		self._create_log(self.PROCESS_A, "Active")
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._create_log(self.PROCESS_A)
		self.assertIn("Only 1 active Pathfinder Log is allowed", str(ctx.exception))

	def test_allowed_after_completion(self):
		"""After the first log is Deployed, a new one should be allowed."""
		self._create_log(self.PROCESS_A, "Deployed")
		name = self._create_log(self.PROCESS_A)
		self.assertTrue(frappe.db.exists("Pathfinder Log", name))

	def test_resave_existing_active_log(self):
		"""Re-saving an already active log should not block itself."""
		name = self._create_log(self.PROCESS_A, "Active")
		doc = frappe.get_doc("Pathfinder Log", name)
		doc.save(ignore_permissions=True)  # should not raise

	def test_different_processes_allowed(self):
		"""Different processes can each have their own active log."""
		self._create_log(self.PROCESS_A)
		name_b = self._create_log(self.PROCESS_B)
		self.assertTrue(frappe.db.exists("Pathfinder Log", name_b))


class TestProcessClassificationValidation(FrappeTestCase):
	"""Ensure transition from 'Pending Process Classification' is blocked when Process is generic."""

	GENERIC_PROCESS = "_Test Generic Process"
	SPECIFIC_PROCESS = "_Test Specific Process"

	def setUp(self):
		if not frappe.db.exists("Process", self.GENERIC_PROCESS):
			frappe.get_doc({
				"doctype": "Process",
				"process_name": self.GENERIC_PROCESS,
				"description": "A generic placeholder process",
				"process_owner": "Administrator",
				"business_analyst": "Administrator",
				"is_generic": 1,
			}).insert(ignore_permissions=True)

		if not frappe.db.exists("Process", self.SPECIFIC_PROCESS):
			frappe.get_doc({
				"doctype": "Process",
				"process_name": self.SPECIFIC_PROCESS,
				"description": "An actual specific process",
				"process_owner": "Administrator",
				"business_analyst": "Administrator",
				"is_generic": 0,
			}).insert(ignore_permissions=True)

	def tearDown(self):
		for proc in (self.GENERIC_PROCESS, self.SPECIFIC_PROCESS):
			frappe.db.delete("Pathfinder Log", {"process_name": proc})
		frappe.db.commit()

	def _create_log(self, process_name, status="Backlog"):
		doc = frappe.get_doc({
			"doctype": "Pathfinder Log",
			"process_name": process_name,
			"goal_description": "Test goal",
			"type": "Incremental Changes",
			"status": status,
		})
		doc.insert(ignore_permissions=True)
		if status != "Backlog":
			frappe.db.set_value(
				"Pathfinder Log", doc.name,
				"status", status,
				update_modified=True,
			)
			frappe.db.commit()
		return doc.name

	def test_generic_process_blocks_transition(self):
		"""Transitioning away from 'Pending Process Classification' with a generic process should fail."""
		log_name = self._create_log(self.GENERIC_PROCESS, "Pending Process Classification")

		doc = frappe.get_doc("Pathfinder Log", log_name)
		doc.status = "Upcoming"
		with self.assertRaises(frappe.ValidationError) as ctx:
			doc.save(ignore_permissions=True)
		self.assertIn("is marked as generic", str(ctx.exception))

	def test_specific_process_allows_transition(self):
		"""Transitioning away from 'Pending Process Classification' with a non-generic process should succeed."""
		log_name = self._create_log(self.SPECIFIC_PROCESS, "Pending Process Classification")

		doc = frappe.get_doc("Pathfinder Log", log_name)
		doc.status = "Upcoming"
		doc.save(ignore_permissions=True)  # should not raise
		self.assertEqual(doc.status, "Upcoming")

	def test_resave_without_status_change_allowed(self):
		"""Saving a log in 'Pending Process Classification' without changing status should always succeed."""
		log_name = self._create_log(self.GENERIC_PROCESS, "Pending Process Classification")

		doc = frappe.get_doc("Pathfinder Log", log_name)
		doc.goal_description = "Updated goal"
		doc.save(ignore_permissions=True)  # should not raise

	def test_transition_allowed_after_switching_to_specific_process(self):
		"""After switching from a generic to a specific process, transition should succeed."""
		log_name = self._create_log(self.GENERIC_PROCESS, "Pending Process Classification")

		doc = frappe.get_doc("Pathfinder Log", log_name)
		doc.process_name = self.SPECIFIC_PROCESS
		doc.status = "Upcoming"
		doc.save(ignore_permissions=True)  # should not raise
		self.assertEqual(doc.status, "Upcoming")


class TestActiveStatusValidation(FrappeTestCase):
	"""Unit tests for _validate_active_status_conditions().

	Calls the method directly on in-memory docs so tests remain fast and
	independent of link-field validation (epic is a Link to Work Item; we
	only need the truthy/falsy check that the method itself performs).
	"""

	PROCESS = "_Test Active Status Val Process"

	def setUp(self):
		if not frappe.db.exists("Process", self.PROCESS):
			frappe.get_doc({
				"doctype": "Process",
				"process_name": self.PROCESS,
				"description": "Process for active-status validation tests",
				"process_owner": "Administrator",
				"business_analyst": "Administrator",
				"is_generic": 0,
			}).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.delete("Pathfinder Log", {"process_name": self.PROCESS})
		frappe.db.commit()

	def _make_doc(self, **overrides):
		"""Return an in-memory Pathfinder Log with all prerequisites satisfied by default."""
		doc = frappe.new_doc("Pathfinder Log")
		doc.process_name = self.PROCESS
		doc.goal_description = "Test goal"
		doc.type = "Incremental Changes"
		doc.status = "Active"
		doc.process_is_generic = 0
		# A non-empty string satisfies the truthy check; no link lookup is
		# done inside _validate_active_status_conditions itself.
		doc.epic = "FAKE-EPIC-REF"
		doc.process_folder_link = "https://drive.google.com/test-folder"
		for key, val in overrides.items():
			setattr(doc, key, val)
		return doc

	# ── Blocking scenarios ───────────────────────────────────────────────────

	def test_generic_process_blocks_active(self):
		"""Active is blocked when the selected process is marked Generic."""
		doc = self._make_doc(process_is_generic=1)
		with self.assertRaises(frappe.ValidationError) as ctx:
			doc._validate_active_status_conditions()
		self.assertIn("Generic", str(ctx.exception))

	def test_missing_epic_blocks_active(self):
		"""Active is blocked when the Epic field is empty."""
		doc = self._make_doc(epic="")
		with self.assertRaises(frappe.ValidationError) as ctx:
			doc._validate_active_status_conditions()
		self.assertIn("Epic", str(ctx.exception))

	def test_missing_folder_link_blocks_active(self):
		"""Active is blocked when the Process Folder Link field is empty."""
		doc = self._make_doc(process_folder_link="")
		with self.assertRaises(frappe.ValidationError) as ctx:
			doc._validate_active_status_conditions()
		self.assertIn("Process Folder Link", str(ctx.exception))

	def test_all_three_conditions_failing_single_throw(self):
		"""All three failing conditions must appear together in one ValidationError."""
		doc = self._make_doc(
			process_is_generic=1,
			epic="",
			process_folder_link="",
		)
		with self.assertRaises(frappe.ValidationError) as ctx:
			doc._validate_active_status_conditions()
		error_msg = str(ctx.exception)
		self.assertIn("Generic", error_msg)
		self.assertIn("Epic", error_msg)
		self.assertIn("Process Folder Link", error_msg)

	# ── Allowed scenarios ────────────────────────────────────────────────────

	def test_all_prerequisites_met_allows_active(self):
		"""No exception must be raised when all three prerequisites are satisfied."""
		doc = self._make_doc()  # all good by default
		doc._validate_active_status_conditions()  # must not raise

	def test_non_active_status_skips_validation(self):
		"""Guard must not fire for any status other than 'Active'."""
		blocking_overrides = dict(
			process_is_generic=1,
			epic="",
			process_folder_link="",
		)
		non_active_statuses = [
			"Backlog",
			"Pending Process Classification",
			"Upcoming",
			"On Hold",
			"Deployed",
		]
		for status in non_active_statuses:
			with self.subTest(status=status):
				doc = self._make_doc(status=status, **blocking_overrides)
				doc._validate_active_status_conditions()  # must not raise
