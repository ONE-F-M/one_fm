# Copyright (c) 2026, ONE FM and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.page.roster.roster import (
	HELPDESK_MANAGED_ROSTER_EDIT_ROLES,
	check_employee_roster_permission,
	check_site_roster_permission,
	get_employee_roster_sites,
	is_site_roster_read_only,
)


class TestHelpdeskManagedRosterPermission(FrappeTestCase):
	"""
	WI-001692: roster edit rights on a Helpdesk-managed Operations Site.

	The site flag and role membership are patched rather than fixtured, so these run
	without creating Operations Sites, Shifts or Employees.
	"""

	# ------------------------------------------------------------------
	# AC4: a site that is not Helpdesk-managed keeps standard behaviour
	# ------------------------------------------------------------------

	def test_unmanaged_site_is_never_read_only(self):
		with patch("frappe.db.get_value", return_value=0):
			with patch("frappe.get_roles", return_value=["Site Supervisor"]):
				self.assertFalse(is_site_roster_read_only("SITE-TEST"))
				# and the gate must not raise
				check_site_roster_permission("SITE-TEST")

	def test_no_site_is_never_read_only(self):
		# Actions that cannot be attributed to a site fall through untouched.
		self.assertFalse(is_site_roster_read_only(None))
		check_site_roster_permission(None)

	# ------------------------------------------------------------------
	# AC3: the Site Supervisor of a managed site is read-only
	# ------------------------------------------------------------------

	def test_site_supervisor_is_read_only_on_managed_site(self):
		with patch("frappe.db.get_value", return_value=1):
			with patch("frappe.get_roles", return_value=["Site Supervisor", "Employee"]):
				self.assertTrue(is_site_roster_read_only("SITE-TEST"))
				with self.assertRaises(frappe.ValidationError):
					check_site_roster_permission("SITE-TEST")

	# ------------------------------------------------------------------
	# AC2: Helpdesk roles keep full edit rights
	# ------------------------------------------------------------------

	def test_helpdesk_roles_keep_edit_rights(self):
		for role in sorted(HELPDESK_MANAGED_ROSTER_EDIT_ROLES):
			with patch("frappe.db.get_value", return_value=1):
				with patch("frappe.get_roles", return_value=[role]):
					self.assertFalse(is_site_roster_read_only("SITE-TEST"), msg=role)
					check_site_roster_permission("SITE-TEST")

	def test_helpdesk_operator_and_supervisor_are_both_allowed(self):
		# Named explicitly by the AC, so pinned independently of the constant.
		self.assertIn("Helpdesk Operator", HELPDESK_MANAGED_ROSTER_EDIT_ROLES)
		self.assertIn("Helpdesk Supervisor", HELPDESK_MANAGED_ROSTER_EDIT_ROLES)
		self.assertNotIn("Site Supervisor", HELPDESK_MANAGED_ROSTER_EDIT_ROLES)

	# ------------------------------------------------------------------
	# Employee-keyed payloads
	# ------------------------------------------------------------------

	def test_empty_payload_resolves_no_sites(self):
		# Guards against a query with an empty IN clause.
		self.assertEqual(get_employee_roster_sites([]), set())
		self.assertEqual(get_employee_roster_sites(None), set())
		self.assertEqual(get_employee_roster_sites([{}]), set())

	def test_payload_key_is_configurable(self):
		# Roster actions name the employee "employee"; bulk_employee_record_update
		# names it "name". Both must resolve.
		with patch(
			"frappe.get_all", return_value=[frappe._dict(name="EMP-1", site="SITE-A", shift=None)]
		):
			self.assertEqual(get_employee_roster_sites([{"employee": "EMP-1"}]), {"SITE-A"})
			self.assertEqual(get_employee_roster_sites([{"name": "EMP-1"}], key="name"), {"SITE-A"})
			# wrong key -> no employees found -> no sites (and no query)
			self.assertEqual(get_employee_roster_sites([{"name": "EMP-1"}]), set())

	def test_site_falls_back_to_the_employees_shift(self):
		calls = []

		def fake_get_all(doctype, **kwargs):
			calls.append(doctype)
			if doctype == "Employee":
				return [frappe._dict(name="EMP-1", site=None, shift="SHIFT-A")]
			return [frappe._dict(site="SITE-FROM-SHIFT")]

		with patch("frappe.get_all", side_effect=fake_get_all):
			self.assertEqual(
				get_employee_roster_sites([{"employee": "EMP-1"}]), {"SITE-FROM-SHIFT"}
			)

		# Two queries regardless of payload size - never one per employee.
		self.assertEqual(calls, ["Employee", "Operations Shift"])

	def test_bulk_payload_spanning_sites_is_blocked_on_the_managed_one(self):
		# A single action covering an unmanaged and a managed site must be refused:
		# the managed site cannot be slipped through alongside the unmanaged one.
		def fake_get_value(doctype, name, fieldname, *a, **k):
			return 1 if name == "SITE-MANAGED" else 0

		with patch(
			"frappe.get_all",
			return_value=[
				frappe._dict(name="EMP-1", site="SITE-OPEN", shift=None),
				frappe._dict(name="EMP-2", site="SITE-MANAGED", shift=None),
			],
		):
			with patch("frappe.db.get_value", side_effect=fake_get_value):
				with patch("frappe.get_roles", return_value=["Site Supervisor"]):
					with self.assertRaises(frappe.ValidationError):
						check_employee_roster_permission(
							[{"employee": "EMP-1"}, {"employee": "EMP-2"}]
						)
