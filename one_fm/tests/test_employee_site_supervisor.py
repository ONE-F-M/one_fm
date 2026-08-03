# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for Employee.custom_site_supervisor_user (WI-001780).

The field carries the User of the supervisor on the employee's Operations Site, so
downstream documents can assign work to a person without re-deriving the chain.
It is resolved on save rather than with `fetch_from`, because the value is two hops
away and `tabEmployee` has no room for an intermediate link column.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.custom_field.employee import get_employee_custom_fields
from one_fm.overrides.employee import get_site_supervisor_user

FIELDNAME = "custom_site_supervisor_user"


def _field_def():
	return next(
		(
			f
			for f in get_employee_custom_fields()["Employee"]
			if f["fieldname"] == FIELDNAME
		),
		None,
	)


class TestSiteSupervisorFieldDefinition(FrappeTestCase):
	def test_the_field_is_defined_in_the_app(self):
		self.assertIsNotNone(_field_def())

	def test_it_links_to_user_and_is_read_only(self):
		field = _field_def()
		self.assertEqual(field["fieldtype"], "Link")
		self.assertEqual(field["options"], "User")
		# Resolved on save, so it must not be hand-editable.
		self.assertEqual(field["read_only"], 1)

	def test_it_does_not_use_fetch_from(self):
		# fetch_from walks a single hop; this value is two away. A fetch_from here
		# would silently resolve nothing.
		self.assertNotIn("fetch_from", _field_def())

	def test_only_one_site_supervisor_column_is_added(self):
		# tabEmployee has room for exactly one more varchar; a second Custom Field
		# would fail its ALTER and leave an orphan that breaks every Employee write.
		added = [
			f["fieldname"]
			for f in get_employee_custom_fields()["Employee"]
			if "site_supervisor" in f["fieldname"] and f["fieldtype"] == "Link"
		]
		self.assertEqual(added, [FIELDNAME])

	def test_the_column_exists_on_the_site(self):
		self.assertTrue(frappe.db.has_column("Employee", FIELDNAME))


class TestGetSiteSupervisorUser(FrappeTestCase):
	def test_no_site_resolves_to_nothing(self):
		self.assertIsNone(get_site_supervisor_user(None))
		self.assertIsNone(get_site_supervisor_user(""))

	def test_an_unknown_site_resolves_to_nothing(self):
		self.assertIsNone(get_site_supervisor_user("_no_such_operations_site"))

	def test_a_site_without_a_supervisor_resolves_to_nothing(self):
		site = frappe.db.get_value(
			"Operations Site", {"site_supervisor": ["is", "not set"]}, "name"
		)
		if not site:
			self.skipTest("every Operations Site on this site has a supervisor")
		self.assertIsNone(get_site_supervisor_user(site))

	def test_it_walks_site_then_supervisor_then_user(self):
		row = frappe.db.sql(
			"""
			select os.name as site, sup.user_id as user_id
			from `tabOperations Site` os
			join `tabEmployee` sup on sup.name = os.site_supervisor
			where ifnull(sup.user_id, '') != ''
			limit 1
			""",
			as_dict=True,
		)
		if not row:
			self.skipTest("no Operations Site with a supervisor holding a User")
		self.assertEqual(get_site_supervisor_user(row[0].site), row[0].user_id)


class TestResolvedOnSave(FrappeTestCase):
	"""The field must track the employee's site, not just be backfilled once."""

	def setUp(self):
		# `site` is read-only with fetch_from shift.site, so an employee holding a
		# shift has their site re-derived on every save and it cannot be steered from
		# a test. Picking a shift-less employee keeps `site` stable, which is what
		# these two tests actually vary.
		row = frappe.db.sql(
			"""
			select e.name, e.site
			from `tabEmployee` e
			join `tabOperations Site` os on os.name = e.site
			join `tabEmployee` sup on sup.name = os.site_supervisor
			where ifnull(sup.user_id, '') != '' and ifnull(e.shift, '') = ''
			limit 1
			""",
			as_dict=True,
		)
		if not row:
			self.skipTest("no shift-less employee on a site whose supervisor holds a User")
		self.employee = frappe.get_doc("Employee", row[0].name)
		self.employee.flags.ignore_mandatory = True
		self.expected = get_site_supervisor_user(row[0].site)

	def test_a_cleared_value_is_restored_on_save(self):
		self.employee.set(FIELDNAME, None)
		self.employee.save(ignore_permissions=True)
		self.assertEqual(self.employee.get(FIELDNAME), self.expected)

	def test_it_follows_the_employee_to_another_site(self):
		# Otherwise a transferred employee keeps pointing at their old supervisor.
		other = frappe.db.sql(
			"""
			select os.name
			from `tabOperations Site` os
			join `tabEmployee` sup on sup.name = os.site_supervisor
			where os.name != %s and ifnull(sup.user_id, '') != ''
			limit 1
			""",
			(self.employee.site,),
			as_dict=True,
		)
		if not other:
			self.skipTest("no second Operations Site with a supervisor holding a User")

		# `site` is read-only and fetched from `shift`, so it is set directly here;
		# in the desk it changes by reallocating the employee's shift.
		self.employee.site = other[0].name
		self.employee.save(ignore_permissions=True)

		self.assertEqual(
			self.employee.get(FIELDNAME), get_site_supervisor_user(other[0].name)
		)


class TestBackfillMatchesTheResolver(FrappeTestCase):
	"""The backfill and the save-time resolver must not drift apart."""

	def test_stored_values_agree_with_the_resolver(self):
		rows = frappe.get_all(
			"Employee",
			filters={"site": ["is", "set"]},
			fields=["name", "site", FIELDNAME],
			limit_page_length=50,
		)
		if not rows:
			self.skipTest("no employees with a site on this instance")
		for row in rows:
			self.assertEqual(
				row.get(FIELDNAME),
				get_site_supervisor_user(row.site),
				msg=f"{row.name} (site {row.site})",
			)

	def test_employees_without_a_site_have_no_supervisor_user(self):
		stale = frappe.db.count(
			"Employee", {"site": ["is", "not set"], FIELDNAME: ["is", "set"]}
		)
		self.assertEqual(stale, 0)
