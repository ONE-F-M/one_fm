# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""The checks that refuse a Rambo Assignment submit or cancel. Writing the schedule, the
notifications and the Shift Assignment job run in the Rambo Assignment Processa maps and are
tested in test_rambo_assignment_processa_scripts.py.

Built on live Operations Shifts and an existing Employee, at a date far enough out that no
real roster row sits on it.
"""

from unittest.mock import patch

import frappe
from frappe.query_builder import DocType
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

DATE = add_days(today(), 900)


def _shift(overnight):
	"""An active Operations Shift whose Shift Type does (or does not) cross midnight."""
	OperationsShift = DocType("Operations Shift")
	ShiftType = DocType("Shift Type")
	rows = (
		frappe.qb.from_(OperationsShift)
		.join(ShiftType)
		.on(OperationsShift.shift_type == ShiftType.name)
		.select(OperationsShift.name, ShiftType.start_time, ShiftType.end_time)
		.where(OperationsShift.status == "Active")
	).run(as_dict=True)
	for row in rows:
		if (row.start_time > row.end_time) == overnight:
			return row.name
	raise frappe.DoesNotExistError("No suitable Operations Shift on this site")


def _reliever():
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site")
	return name


class TestRamboAssignment(FrappeTestCase):
	def setUp(self):
		self.employee = _reliever()

	def _rambo(self, **kw):
		shift = _shift(overnight=False)
		values = {"doctype": "Rambo Assignment", "date": DATE, "employee": self.employee, "operations_shift": shift, "roster_type": "Basic"}
		values.update(kw)
		doc = frappe.get_doc(values)
		doc.insert(ignore_permissions=True)
		return doc

	def test_rambo_assignment_is_submittable(self):
		self.assertTrue(frappe.get_meta("Rambo Assignment").is_submittable)

	def test_submit_needs_a_shift(self):
		rambo = self._rambo(operations_shift=None)
		self.assertRaises(frappe.ValidationError, rambo.validate_schedule_details)

	def test_submit_needs_a_shift_type(self):
		rambo = self._rambo()
		with patch.object(frappe.db, "get_value", return_value=None):
			self.assertRaises(frappe.ValidationError, rambo.validate_schedule_details)

	def test_a_complete_assignment_passes(self):
		self._rambo().validate_schedule_details()

	def test_cancel_is_refused_once_the_reliever_checked_in(self):
		rambo = self._rambo()
		with patch.object(frappe.db, "get_value", side_effect=["ES-1", "SA-1"]), patch.object(frappe.db, "exists", return_value=True):
			self.assertRaises(frappe.ValidationError, rambo.validate_not_checked_in)

	def test_cancel_is_allowed_before_check_in(self):
		rambo = self._rambo()
		with patch.object(frappe.db, "get_value", side_effect=["ES-1", "SA-1"]), patch.object(frappe.db, "exists", return_value=False):
			rambo.validate_not_checked_in()

	def test_the_shift_assignment_job_left_the_scheduler(self):
		events = frappe.get_hooks("scheduler_events")["cron"]
		self.assertFalse(any("one_fm.api.tasks.rambo_shift_assignment" in jobs for jobs in events.values()))
