# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002775: the quota classes PAM allocates a licence's visas in."""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.seed_quota_types import QUOTA_TYPES

DOCTYPE = "Quota Type"


def _definition(module, folder, filename):
	return json.loads(
		frappe.read_file(frappe.get_app_path("one_fm", "grd", "doctype", folder, filename))
	)


class TestTheDocType(FrappeTestCase):
	def setUp(self):
		self.definition = _definition("grd", "quota_type", "quota_type.json")

	def test_a_quota_type_is_named_by_what_it_is_called(self):
		"""Every downstream count joins on the name, so the record has to BE the name."""
		self.assertEqual(self.definition["autoname"], "field:quota_type")
		self.assertEqual(self.definition["naming_rule"], "By fieldname")

	def test_two_types_cannot_share_a_name(self):
		field = next(
			f for f in self.definition["fields"] if f["fieldname"] == "quota_type"
		)
		self.assertEqual(field["unique"], 1)
		self.assertEqual(field["fieldtype"], "Data")

	def test_it_belongs_to_the_grd_module(self):
		self.assertEqual(self.definition["module"], "GRD")

	def test_it_is_not_a_child_table(self):
		"""It is a master a designation links to, not a row inside something else."""
		self.assertNotEqual(self.definition.get("istable"), 1)


class TestTheDesignationLink(FrappeTestCase):
	def setUp(self):
		self.definition = _definition(
			"grd", "pam_designation_list", "pam_designation_list.json"
		)

	def test_a_designation_belongs_to_one_quota_type(self):
		field = next(
			f for f in self.definition["fields"] if f["fieldname"] == "quota_type"
		)
		self.assertEqual(field["fieldtype"], "Link")
		self.assertEqual(field["options"], DOCTYPE)

	def test_it_is_on_the_form(self):
		self.assertIn("quota_type", self.definition["field_order"])

	def test_the_sector_link_is_untouched(self):
		"""WI-002091 counts a licence's workers through occupational_sector; the quota
		type is a second, separate grouping of the same designation."""
		sector = next(
			f for f in self.definition["fields"] if f["fieldname"] == "occupational_sector"
		)
		self.assertEqual(sector["options"], "Occupational Sector")
		self.assertEqual(sector["reqd"], 1)


class TestTheSeed(FrappeTestCase):
	def test_it_seeds_the_three_the_analyst_site_holds(self):
		self.assertEqual(QUOTA_TYPES, ("Basic", "Heavy Driver", "Light Driver"))

	def test_it_leaves_an_existing_record_alone(self):
		"""The business owns this master; a site that has renamed or added to it is not
		one this patch should argue with."""
		source = frappe.read_file(
			frappe.get_app_path("one_fm", "patches", "v15_0", "seed_quota_types.py")
		)
		self.assertIn("if frappe.db.exists(DOCTYPE, quota_type):", source)
		self.assertIn("continue", source)

	def test_it_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.seed_quota_types", patches)
