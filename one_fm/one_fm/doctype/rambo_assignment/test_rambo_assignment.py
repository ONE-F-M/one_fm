# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""Submitting a Rambo Assignment writes the reliever's Employee Schedule, cancelling it
restores a schedule it overwrote (or deletes one it created), and the Shift Assignment job
is scheduled.

Built on live Operations Shifts and an existing Employee, at a date far enough out that no
real roster row sits on it.
"""

from unittest.mock import patch

import frappe
from frappe.query_builder import DocType
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from one_fm.one_fm.doctype.transportation_manifest.transportation_manifest import _rambo_changed

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


@patch("one_fm.processor.sendemail")
@patch("one_fm.utils.send_push_notification")
class TestRamboAssignment(FrappeTestCase):
	def setUp(self):
		self.employee = _reliever()
		frappe.db.delete("Employee Schedule", {"employee": self.employee, "date": DATE})

	def _rambo(self, overnight=False):
		shift = _shift(overnight)
		site, project = frappe.db.get_value("Operations Shift", shift, ["site", "project"])
		doc = frappe.get_doc(
			{
				"doctype": "Rambo Assignment",
				"date": DATE,
				"employee": self.employee,
				"operations_shift": shift,
				"operations_site": site,
				"project": project,
				"roster_type": "Basic",
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def _schedule(self, rambo_name):
		return frappe.db.get_value(
			"Employee Schedule",
			{"rambo_assignment": rambo_name},
			["name", "shift", "is_rambo_schedule", "start_datetime", "end_datetime"],
			as_dict=True,
		)

	def test_rambo_assignment_is_submittable(self, *_):
		self.assertTrue(frappe.get_meta("Rambo Assignment").is_submittable)

	def test_submit_writes_the_reliever_schedule(self, *_):
		rambo = self._rambo()
		self.assertIsNone(self._schedule(rambo.name))

		rambo.submit()

		schedule = self._schedule(rambo.name)
		self.assertIsNotNone(schedule)
		self.assertEqual(schedule.shift, rambo.operations_shift)
		self.assertEqual(schedule.is_rambo_schedule, 1)

	def test_an_overnight_shift_ends_the_next_day(self, *_):
		rambo = self._rambo(overnight=True)

		rambo.submit()

		schedule = self._schedule(rambo.name)
		self.assertEqual(getdate(schedule.end_datetime), getdate(add_days(DATE, 1)))

	def test_cancel_removes_the_schedule(self, *_):
		rambo = self._rambo()
		rambo.submit()

		rambo.cancel()

		self.assertIsNone(self._schedule(rambo.name))

	def test_cancel_restores_a_schedule_the_reliever_already_had(self, *_):
		own_shift = _shift(overnight=True)
		site, project, shift_type = frappe.db.get_value(
			"Operations Shift", own_shift, ["site", "project", "shift_type"]
		)
		own = frappe.get_doc(
			{
				"doctype": "Employee Schedule",
				"employee": self.employee,
				"date": DATE,
				"employee_availability": "Working",
				"shift": own_shift,
				"shift_type": shift_type,
				"site": site,
				"project": project,
				"roster_type": "Basic",
			}
		)
		own.flags.ignore_permissions = True
		own.insert()

		rambo = self._rambo()
		rambo.submit()
		self.assertEqual(self._schedule(rambo.name).name, own.name)

		rambo.cancel()

		restored = frappe.db.get_value(
			"Employee Schedule",
			own.name,
			["shift", "site", "is_rambo_schedule", "rambo_assignment"],
			as_dict=True,
		)
		self.assertIsNotNone(restored, "the reliever's own schedule was deleted")
		self.assertEqual(restored.shift, own_shift)
		self.assertEqual(restored.site, site)
		self.assertFalse(restored.is_rambo_schedule)
		self.assertIsNone(restored.rambo_assignment)

	def test_the_shift_assignment_job_is_scheduled(self, *_):
		events = frappe.get_hooks("scheduler_events")["cron"]
		self.assertTrue(
			any("one_fm.api.tasks.rambo_shift_assignment" in jobs for jobs in events.values())
		)


class TestRamboChanged(FrappeTestCase):
	def test_the_same_values_are_not_a_change(self):
		doc = frappe._dict(employee="HR-EMP-1", date=getdate(DATE), is_rambo_reliever=0, start_time=None)
		self.assertFalse(
			_rambo_changed(doc, {"employee": "HR-EMP-1", "date": DATE, "is_rambo_reliever": 0, "start_time": ""})
		)

	def test_a_new_reliever_is_a_change(self):
		doc = frappe._dict(employee="HR-EMP-1")
		self.assertTrue(_rambo_changed(doc, {"employee": "HR-EMP-2"}))
