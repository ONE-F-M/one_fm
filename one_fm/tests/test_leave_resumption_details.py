# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-001873: the Resumption Confirmation Details block, and who HelpDesk is reminded about."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from one_fm.overrides.leave_application import (
	RESUMPTION_LEAVE_TYPES,
	get_employees_whose_leave_ends_in,
)

# The order the BA site has, top to bottom.
RESUMPTION_FIELD_ORDER = (
	"resumption_confirmation_details",
	"custom_could_the_employee_be_reached",
	"custom_action",
	"custom_reason_employee_not_reached",
	"custom_will_the_employee_return",
	"outcome",
	"custom_does_the_employee_need_additional_time_to_resume",
	"return_ticket_submitted",
	"actual_return_date",
	"column_break_resumption_details",
	"attach_return_ticket",
)


class TestTheResumptionBlock(FrappeTestCase):
	"""Asserted through get_meta, which is what the form renders from - so a Customize
	Form override of any of these fails here too."""

	def setUp(self):
		self.meta = frappe.get_meta("Leave Application")

	def test_the_fields_are_in_the_order_the_ba_site_has(self):
		fieldnames = [f.fieldname for f in self.meta.fields]
		positions = [fieldnames.index(name) for name in RESUMPTION_FIELD_ORDER]

		self.assertEqual(positions, sorted(positions), msg=str(RESUMPTION_FIELD_ORDER))

	def test_the_additional_time_question_comes_before_the_return_date_it_governs(self):
		fieldnames = [f.fieldname for f in self.meta.fields]

		self.assertLess(
			fieldnames.index("custom_does_the_employee_need_additional_time_to_resume"),
			fieldnames.index("actual_return_date"),
		)

	def test_the_section_is_only_for_shift_working_employees(self):
		depends_on = self.meta.get_field("resumption_confirmation_details").depends_on

		self.assertIn("doc.custom_shift_working", depends_on)
		# And still only for an approved Annual Leave or Leave Without Pay.
		self.assertIn("doc.workflow_state=='Approved'", depends_on)
		for leave_type in RESUMPTION_LEAVE_TYPES:
			self.assertIn(leave_type, depends_on)

	def test_a_return_date_is_not_demanded_while_more_time_is_being_asked_for(self):
		mandatory = self.meta.get_field("actual_return_date").mandatory_depends_on

		self.assertIn("doc.custom_will_the_employee_return == 'Yes'", mandatory)
		self.assertIn(
			"doc.custom_does_the_employee_need_additional_time_to_resume != 'Yes'", mandatory
		)

	def test_the_condition_reads_as_python_and_as_javascript(self):
		"""depends_on runs in the browser; the same string is also evaluated server-side
		for a mandatory check, so it has to be valid in both."""
		mandatory = self.meta.get_field("actual_return_date").mandatory_depends_on
		expression = mandatory.replace("eval:", "").replace("&&", "and").replace("||", "or")

		doc = frappe._dict(
			custom_will_the_employee_return="Yes",
			custom_does_the_employee_need_additional_time_to_resume="Yes",
		)
		self.assertFalse(frappe.safe_eval(expression, None, {"doc": doc}))

		doc.custom_does_the_employee_need_additional_time_to_resume = "No"
		self.assertTrue(frappe.safe_eval(expression, None, {"doc": doc}))


class TestWhoHelpdeskIsRemindedAbout(FrappeTestCase):
	"""WI-001873: Annual Leave *or* Leave Without Pay, Approved, and shift working."""

	def _a_submitted_leave(self, leave_type):
		"""An existing approved leave for a shift-working employee, off the site."""
		rows = frappe.db.sql(
			"""
			select la.name from `tabLeave Application` la
			join `tabEmployee` e on e.name = la.employee
			where la.docstatus = 1 and la.workflow_state = 'Approved'
			  and la.leave_type = %s and e.shift_working = 1
			limit 1
			""",
			leave_type,
		)
		return rows[0][0] if rows else None

	def test_both_leave_types_are_chased(self):
		self.assertEqual(set(RESUMPTION_LEAVE_TYPES), {"Annual Leave", "Leave Without Pay"})

	def test_a_leave_ending_in_the_window_is_reported_for_either_type(self):
		ends_in = 6
		# Named here rather than read off RESUMPTION_LEAVE_TYPES: iterating the constant
		# under test would let a regression that drops a type pass unnoticed, because the
		# loop would simply stop checking it.
		for leave_type in ("Annual Leave", "Leave Without Pay"):
			with self.subTest(leave_type=leave_type):
				name = self._a_submitted_leave(leave_type)
				if not name:
					self.skipTest(f"no approved {leave_type} for a shift-working employee")

				# Moved into the window inside the test transaction, then rolled back.
				frappe.db.set_value(
					"Leave Application", name, "to_date", add_days(today(), ends_in),
					update_modified=False,
				)
				employee = frappe.db.get_value("Leave Application", name, "employee")

				reported = get_employees_whose_leave_ends_in(leave_ends_in=ends_in)
				self.assertIn(employee, [row.employee for row in reported])

	def test_a_leave_outside_the_window_is_not_reported(self):
		name = self._a_submitted_leave("Annual Leave")
		if not name:
			self.skipTest("no approved Annual Leave for a shift-working employee")

		frappe.db.set_value(
			"Leave Application", name, "to_date", add_days(today(), 6), update_modified=False
		)
		employee = frappe.db.get_value("Leave Application", name, "employee")

		# The reminder is sent 7 days out, so a different offset must not pick it up.
		reported = get_employees_whose_leave_ends_in(leave_ends_in=3)
		self.assertNotIn(employee, [row.employee for row in reported])

	def test_an_employee_who_is_not_shift_working_is_left_alone(self):
		"""The whole block exists for people a duty roster depends on."""
		name = self._a_submitted_leave("Annual Leave")
		if not name:
			self.skipTest("no approved Annual Leave for a shift-working employee")

		employee = frappe.db.get_value("Leave Application", name, "employee")
		frappe.db.set_value(
			"Leave Application", name, "to_date", add_days(today(), 6), update_modified=False
		)
		frappe.db.set_value("Employee", employee, "shift_working", 0, update_modified=False)

		reported = get_employees_whose_leave_ends_in(leave_ends_in=6)
		self.assertNotIn(employee, [row.employee for row in reported])
