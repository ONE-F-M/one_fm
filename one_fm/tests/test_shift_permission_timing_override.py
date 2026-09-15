# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-001836: a Shift Permission auto-fetches the override day's own Shift Type.

No production code changed for this story either. Both places a Shift Permission gets its
Shift Type from already read a day-resolved source:

  - the Desk path, shift_permission.fetch_approver, reads it off the Shift Assignment for
    that date, which WI-001833 made the override's
  - the mobile path, api.mobile.shift_permission.get_shift_details, reads it off the
    Employee Schedule for that date, which WI-001832 made the override's

The tests are the deliverable: proof for the approver-facing field the story is about, and
a guard against either path being pointed back at Operations Shift.shift_type.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from one_fm.api.mobile.shift_permission import get_shift_details
from one_fm.operations.doctype.shift_permission.shift_permission import fetch_approver


def _an_operations_shift():
	name = frappe.db.get_value(
		"Operations Shift",
		{"status": "Active", "shift_type": ["is", "set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active Operations Shift on this site to test against")
	return name


def _an_active_employee():
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestShiftPermissionTimingOverride(FrappeTestCase):
	def setUp(self):
		# A Shift Assignment cannot be dated later than today, so the override goes on
		# today's own day of the week and the default case uses yesterday.
		self.override_date = today()
		self.override_day = getdate(self.override_date).strftime("%A")
		self.default_date = add_days(self.override_date, -1)

		self.employee = _an_active_employee()
		self.shift_name = _an_operations_shift()
		self.shift = frappe.get_doc("Operations Shift", self.shift_name)
		self.default_type = self.shift.shift_type

		default_start = frappe.db.get_value("Shift Type", self.default_type, "start_time")
		self.override_type = frappe.db.get_value(
			"Shift Type",
			{"name": ["!=", self.default_type], "start_time": [">", default_start]},
			"name",
			order_by="start_time asc",
		)
		if not self.override_type:
			self.skipTest("No later-starting Shift Type on this site to override with")

		self._set_override(True)

	def tearDown(self):
		self._set_override(False)
		for date in (self.override_date, self.default_date):
			frappe.db.delete("Shift Assignment", {"employee": self.employee, "start_date": date})
			frappe.db.delete("Employee Schedule", {"employee": self.employee, "date": date})

	def _set_override(self, on):
		frappe.db.set_value(
			"Operations Shift", self.shift_name, "shift_timing_override_required", int(on),
			update_modified=False,
		)
		frappe.db.delete(
			"Operations Shift Timing",
			{"parent": self.shift_name, "parenttype": "Operations Shift"},
		)
		if on:
			frappe.get_doc({
				"doctype": "Operations Shift Timing",
				"parent": self.shift_name,
				"parenttype": "Operations Shift",
				"parentfield": "operations_shift_timing",
				"idx": 1,
				"day_of_week": self.override_day,
				"shift_type": self.override_type,
			}).db_insert()
		frappe.clear_document_cache("Operations Shift", self.shift_name)

	def _assignment(self, date):
		frappe.db.delete("Shift Assignment", {"employee": self.employee, "start_date": date})
		assignment = frappe.get_doc({
			"doctype": "Shift Assignment",
			"employee": self.employee,
			"company": frappe.defaults.get_user_default("company"),
			"shift": self.shift_name,
			"shift_type": self.default_type,
			"start_date": date,
			"status": "Active",
			"roster_type": "Basic",
		})
		assignment.flags.ignore_permissions = True
		assignment.insert(ignore_permissions=True)
		assignment.submit()
		return assignment

	def _schedule(self, date):
		frappe.db.delete("Employee Schedule", {"employee": self.employee, "date": date})
		schedule = frappe.get_doc({
			"doctype": "Employee Schedule",
			"employee": self.employee,
			"date": date,
			"shift": self.shift_name,
			"site": self.shift.site,
			"project": self.shift.project,
			"employee_availability": "Working",
			"shift_type": self.default_type,
			"roster_type": "Basic",
		})
		schedule.flags.ignore_permissions = True
		schedule.insert()
		return schedule

	# --------------------------------------------------------------- the Desk path

	def test_the_permission_fetches_the_override_shift_type(self):
		assignment = self._assignment(self.override_date)

		fetched = fetch_approver(self.employee, self.override_date)

		self.assertEqual(fetched["shift_type"], self.override_type)
		self.assertEqual(fetched["shift_assignment"], assignment.name)

	def test_it_is_not_the_default_shift_type(self):
		# The wording of the criterion: "not the default shift type".
		self._assignment(self.override_date)

		self.assertNotEqual(
			fetch_approver(self.employee, self.override_date)["shift_type"], self.default_type
		)

	def test_the_operations_shift_is_still_reported(self):
		self._assignment(self.override_date)

		self.assertEqual(fetch_approver(self.employee, self.override_date)["shift"], self.shift_name)

	def test_a_default_day_fetches_the_default_shift_type(self):
		self._assignment(self.default_date)

		self.assertEqual(
			fetch_approver(self.employee, self.default_date)["shift_type"], self.default_type
		)

	def test_with_the_override_off_the_day_fetches_the_default(self):
		self._set_override(False)
		self._assignment(self.override_date)

		self.assertEqual(
			fetch_approver(self.employee, self.override_date)["shift_type"], self.default_type
		)

	# ------------------------------------------------------------- the mobile path

	def test_the_mobile_path_also_reports_the_override(self):
		self._schedule(self.override_date)
		self._assignment(self.override_date)

		shift, shift_type, assigned_shift, _approver = get_shift_details(
			self.employee, self.override_date
		)

		self.assertEqual(shift, self.shift_name)
		self.assertEqual(shift_type, self.override_type)
		self.assertTrue(assigned_shift)

	def test_the_mobile_path_reports_the_default_on_a_default_day(self):
		self._schedule(self.default_date)
		self._assignment(self.default_date)

		_shift, shift_type, _assigned_shift, _approver = get_shift_details(
			self.employee, self.default_date
		)

		self.assertEqual(shift_type, self.default_type)

	def test_both_paths_agree(self):
		# The two of them feeding an approver different hours for the same date is the
		# failure this story exists to prevent.
		self._schedule(self.override_date)
		self._assignment(self.override_date)

		_shift, mobile_type, _assigned, _approver = get_shift_details(
			self.employee, self.override_date
		)
		desk_type = fetch_approver(self.employee, self.override_date)["shift_type"]

		self.assertEqual(mobile_type, desk_type)
