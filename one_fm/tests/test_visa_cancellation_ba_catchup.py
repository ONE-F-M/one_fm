# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002608: bring the Visa Cancellation Request doctype in line with the BA site.

The process map is imported separately. What is here is everything at DOCTYPE level, which
after diffing both copies over the API came to three things:

* ``pro_operator`` gains a depends_on, so it is shown only in the states that have one.
* ``grd_operator`` gains a read_only_depends_on with the same list.
* ``Visa Cancellation Rejected`` becomes ``Rejected by PRO``.

Everything else the diff turned up was noise: API defaults the stored JSON omits, and a
whitespace difference in one link_filters. Two genuine local-only fields are kept and are
covered below - dropping either would be a regression, not a migration.

The rename is the dangerous one, and the controller had already written down why:
is_standing() decides whether a refused cancellation still blocks its Visa Request by
comparing against that one string, so a row left on the old name reads as still standing
and its Visa Request can never be cancelled again.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.rename_visa_cancellation_rejected_state import (
	DOCTYPE,
	NEW_STATE,
	OLD_STATE,
	ensure_workflow_state,
	execute,
)
from one_fm.visa_management.doctype.visa_cancellation_request.visa_cancellation_request import (
	REJECTED_STATE,
	is_standing,
)

# The states the BA site shows pro_operator in. Named here so a silent truncation of the
# condition fails rather than passes.
CONDITION_STATES = (
	"Pending by PRO",
	"Pending for Work Permit Cancellation",
	"Visa Cancelled",
	"Pending GRD Manager Approval",
	"Pending By PAM",
	"Completed",
	"Pending by GRD Operator",
	"Rejected by PRO",
)

SEEDED = "WI-002608-VCR-"


def _clear():
	frappe.db.delete(DOCTYPE, {"name": ["like", SEEDED + "%"]})


class TestTheRenamedState(FrappeTestCase):
	def test_the_controller_uses_the_new_name(self):
		self.assertEqual(REJECTED_STATE, NEW_STATE)
		self.assertEqual(REJECTED_STATE, "Rejected by PRO")

	def test_the_old_name_is_gone_from_the_controller(self):
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "visa_management", "doctype", "visa_cancellation_request",
				"visa_cancellation_request.py",
			)
		)
		# Only the patch should still know the old string.
		self.assertNotIn(f'REJECTED_STATE = "{OLD_STATE}"', source)

	def test_a_refused_cancellation_no_longer_stands(self):
		self.assertFalse(is_standing(NEW_STATE))

	def test_a_row_left_on_the_old_name_would_still_stand(self):
		# This is the whole reason the data has to be migrated rather than just the string:
		# such a row blocks its Visa Request from ever being cancelled again.
		self.assertTrue(is_standing(OLD_STATE))

	def test_a_cancellation_with_no_state_at_all_still_stands(self):
		self.assertTrue(is_standing(None))


class TestTheDataMigration(FrappeTestCase):
	def setUp(self):
		_clear()
		self.addCleanup(_clear)

	def _seed(self, state):
		doc = frappe.new_doc(DOCTYPE)
		doc.name = SEEDED + (state or "NONE").replace(" ", "-")
		doc.set("workflow_state", state)
		doc.db_insert()
		return doc.name

	def test_a_row_on_the_old_name_is_moved_to_the_new_one(self):
		name = self._seed(OLD_STATE)

		execute()

		self.assertEqual(frappe.db.get_value(DOCTYPE, name, "workflow_state"), NEW_STATE)

	def test_rows_in_other_states_are_untouched(self):
		completed = self._seed("Completed")
		draft = self._seed("Draft")

		execute()

		self.assertEqual(frappe.db.get_value(DOCTYPE, completed, "workflow_state"), "Completed")
		self.assertEqual(frappe.db.get_value(DOCTYPE, draft, "workflow_state"), "Draft")

	def test_running_it_twice_changes_nothing_further(self):
		name = self._seed(OLD_STATE)

		execute()
		execute()

		self.assertEqual(frappe.db.get_value(DOCTYPE, name, "workflow_state"), NEW_STATE)

	def test_the_new_workflow_state_exists_afterwards(self):
		# A workflow_state naming a Workflow State that does not exist is a broken link on
		# every one of those documents.
		ensure_workflow_state()

		self.assertTrue(frappe.db.exists("Workflow State", NEW_STATE))

	def test_the_old_workflow_state_is_left_in_place(self):
		# Nothing references it - checked across every Workflow on the site - and deleting a
		# master that historical records and Version rows still name buys nothing.
		execute()

		self.assertTrue(frappe.db.exists("Workflow State", OLD_STATE))


class TestTheDisplayConditions(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.meta = frappe.get_meta(DOCTYPE)

	def _condition(self, fieldname, prop):
		import json

		path = frappe.get_app_path(
			"one_fm", "visa_management", "doctype", "visa_cancellation_request",
			"visa_cancellation_request.json",
		)
		fields = {f["fieldname"]: f for f in json.loads(frappe.read_file(path))["fields"]}
		return fields[fieldname].get(prop)

	def test_pro_operator_is_shown_only_in_the_listed_states(self):
		self.assertTrue(self._condition("pro_operator", "depends_on"))

	def test_grd_operator_is_read_only_in_the_listed_states(self):
		self.assertTrue(self._condition("grd_operator", "read_only_depends_on"))

	def test_both_conditions_list_every_state_the_ba_site_lists(self):
		for prop, fieldname in (("depends_on", "pro_operator"),
								("read_only_depends_on", "grd_operator")):
			condition = self._condition(fieldname, prop)
			for state in CONDITION_STATES:
				self.assertIn(f'"{state}"', condition, msg=f"{fieldname}.{prop}: {state}")

	def test_both_conditions_use_the_renamed_state(self):
		# The old name in a condition would simply never match once the map is imported.
		for prop, fieldname in (("depends_on", "pro_operator"),
								("read_only_depends_on", "grd_operator")):
			condition = self._condition(fieldname, prop)
			self.assertIn(NEW_STATE, condition)
			self.assertNotIn(OLD_STATE, condition)

	def test_the_two_conditions_are_identical(self):
		self.assertEqual(
			self._condition("pro_operator", "depends_on"),
			self._condition("grd_operator", "read_only_depends_on"),
		)


class TestWhatWasDeliberatelyNotMigrated(FrappeTestCase):
	"""The BA copy is missing two fields this site needs. Kept, not dropped."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.meta = frappe.get_meta(DOCTYPE)

	def test_the_cancellation_reason_field_is_kept(self):
		# Absent on the BA site, but WI-002611 is actively extending it to six options.
		# Removing it here would undo an approved story and drop a mandatory field.
		field = self.meta.get_field("cancellation_reason")
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Select")

	def test_the_workflow_state_field_is_kept(self):
		# The BA export leaves it out because Frappe adds it when a workflow is attached.
		# It is declared here, and removing it would drop the column the rename above writes.
		self.assertIsNotNone(self.meta.get_field("workflow_state"))

	def test_the_naming_series_is_kept(self):
		# The BA doctype is a Custom one with no autoname; ours names records VCR-OFM-.
		self.assertEqual(self.meta.autoname, "VCR-OFM-.#####")


class TestThePatchIsWiredUp(FrappeTestCase):
	def test_it_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn(
			"one_fm.patches.v15_0.rename_visa_cancellation_rejected_state", patches
		)
