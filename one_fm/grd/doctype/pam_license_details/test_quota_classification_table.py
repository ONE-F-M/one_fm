# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002774: the Quota Classification table on PAM License Details."""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

# The six figures a row carries, and which of them a person types.
DERIVED_FIELDS = (
	"registered_numbers_of_employees",
	"number_of_visas_issued",
	"number_of_transfer_requests",
	"available_quota",
)
TYPED_FIELD = "allocated_quota"


def _definition(folder, filename):
	return json.loads(
		frappe.read_file(frappe.get_app_path("one_fm", "grd", "doctype", folder, filename))
	)


class TestTheChildTable(FrappeTestCase):
	def setUp(self):
		self.definition = _definition("quota_classification", "quota_classification.json")
		self.fields = {f["fieldname"]: f for f in self.definition["fields"]}

	def test_it_is_a_child_table(self):
		self.assertEqual(self.definition["istable"], 1)
		self.assertEqual(self.definition["module"], "GRD")

	def test_a_row_belongs_to_one_quota_type(self):
		self.assertEqual(self.fields["type_of_quota"]["fieldtype"], "Link")
		self.assertEqual(self.fields["type_of_quota"]["options"], "Quota Type")

	def test_it_carries_every_figure_the_story_lists(self):
		for fieldname in (TYPED_FIELD, *DERIVED_FIELDS):
			self.assertIn(fieldname, self.fields, fieldname)
			self.assertIn(fieldname, self.definition["field_order"], fieldname)

	def test_every_figure_is_visible_in_the_grid(self):
		"""The table is read at a glance; a column hidden behind the row editor is one
		nobody checks."""
		for fieldname in (TYPED_FIELD, *DERIVED_FIELDS, "type_of_quota"):
			self.assertEqual(self.fields[fieldname].get("in_list_view"), 1, fieldname)

	def test_the_grid_is_editable(self):
		"""Allocated Quota is typed into it."""
		self.assertEqual(self.definition["editable_grid"], 1)


class TestTheLicenceSection(FrappeTestCase):
	def setUp(self):
		self.definition = _definition("pam_license_details", "pam_license_details.json")
		self.fields = {f["fieldname"]: f for f in self.definition["fields"]}

	def test_the_licence_carries_the_table(self):
		self.assertEqual(self.fields["quota_classification"]["fieldtype"], "Table")
		self.assertEqual(self.fields["quota_classification"]["options"], "Quota Classification")

	def test_it_carries_the_total_headcount(self):
		self.assertEqual(self.fields["total_number_of_employees"]["fieldtype"], "Data")

	def test_they_sit_in_a_section_of_their_own(self):
		"""PAM Stats rations the licence by occupational sector; this rations it by quota
		type. Two different groupings of the same licence, read separately."""
		order = self.definition["field_order"]
		self.assertLess(
			order.index("quota_classification_section"), order.index("quota_classification")
		)
		self.assertLess(order.index("pam_license_stats"), order.index("quota_classification_section"))

	def test_the_sector_table_is_untouched(self):
		"""WI-002091's headcounts hang off pam_license_stats and must keep doing so."""
		self.assertEqual(self.fields["pam_license_stats"]["options"], "PAM License Stats")

	def test_nothing_the_licence_already_had_was_dropped(self):
		"""The BA site's copy has no lg_details_applicable; migrating from it must not
		take WI-002597's checkbox with it."""
		self.assertIn("lg_details_applicable", self.fields)
		self.assertIn("civil_id_number_for_licensing", self.fields)
