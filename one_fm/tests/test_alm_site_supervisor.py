# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for Accommodation Leave Movement.site_supervisor (WI-001779).

The supervisor is fetched from the selected employee's Site Supervisor User, which
is a single hop from a local Link field - so `fetch_from` resolves it and no
controller code is needed.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

FIELD = "site_supervisor"
SOURCE = "employee.custom_site_supervisor_user"


class TestAlmSiteSupervisorField(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.meta = frappe.get_meta("Accommodation Leave Movement")

	def test_the_field_exists_and_links_to_user(self):
		df = self.meta.get_field(FIELD)
		self.assertIsNotNone(df)
		self.assertEqual(df.fieldtype, "Link")
		self.assertEqual(df.options, "User")

	def test_it_is_read_only(self):
		# Derived from the employee, so it must not be hand-editable.
		self.assertEqual(self.meta.get_field(FIELD).read_only, 1)

	def test_it_fetches_from_the_employees_site_supervisor_user(self):
		self.assertEqual(self.meta.get_field(FIELD).fetch_from, SOURCE)

	def test_the_source_field_exists_on_employee(self):
		# A single hop from the local `employee` link; if the source were renamed the
		# fetch would silently resolve nothing rather than error.
		self.assertTrue(frappe.get_meta("Employee").has_field("custom_site_supervisor_user"))

	def test_it_sits_next_to_the_employee_it_derives_from(self):
		order = [df.fieldname for df in self.meta.fields]
		self.assertEqual(order.index(FIELD), order.index("employee") + 1)


class TestAlmSiteSupervisorResolves(FrappeTestCase):
	"""The fetch has to actually populate on save, not merely be declared."""

	def setUp(self):
		row = frappe.db.sql(
			"""
			select name, custom_site_supervisor_user as supervisor_user
			from `tabEmployee`
			where ifnull(custom_site_supervisor_user, '') != '' and status = 'Active'
			limit 1
			""",
			as_dict=True,
		)
		if not row:
			self.skipTest("no Active employee carrying a site supervisor user")
		self.employee = row[0].name
		self.expected = row[0].supervisor_user

	def test_the_supervisor_is_filled_from_the_employee_on_insert(self):
		doc = frappe.get_doc({
			"doctype": "Accommodation Leave Movement",
			"naming_series": "HR-ALM-OUT-.YYYY.-",
			"type": "OUT",
			"employee": self.employee,
			"checkin_checkout_date_time": now_datetime(),
		})
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.site_supervisor, self.expected)

	def test_the_creator_is_recorded_without_a_duplicate_field(self):
		# Frappe stores the creating user in `owner` and the desk shows it as
		# "Created by", so no second field is kept in step with it.
		doc = frappe.get_doc({
			"doctype": "Accommodation Leave Movement",
			"naming_series": "HR-ALM-OUT-.YYYY.-",
			"type": "OUT",
			"employee": self.employee,
			"checkin_checkout_date_time": now_datetime(),
		})
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.owner, frappe.session.user)
