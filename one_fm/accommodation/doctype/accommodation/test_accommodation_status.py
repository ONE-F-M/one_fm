# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002883: the Status field on Accommodation, as the business analyst's copy has it."""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.backfill_accommodation_status import DEFAULT_STATUS
from one_fm.patches.v15_0.widen_accommodation_list_view import LIST_VIEW, TOTAL_FIELDS

# What the BA site's Accommodation holds, read off it on 2026-09-24:
#   status | Select | options "\nActive\nInactive" | reqd 1 | in_list_view 1 |
#   in_standard_filter 1 | positioned after `type`
EXPECTED_OPTIONS = "\nActive\nInactive"


def _definition():
	return json.loads(
		frappe.read_file(
			frappe.get_app_path(
				"one_fm", "accommodation", "doctype", "accommodation", "accommodation.json"
			)
		)
	)


class TestTheStatusField(FrappeTestCase):
	def setUp(self):
		self.definition = _definition()
		self.field = next(
			f for f in self.definition["fields"] if f["fieldname"] == "status"
		)

	def test_it_offers_the_two_states_the_analyst_site_offers(self):
		"""Under Maintenance, Vacant and Occupied are on no site - inventing options makes
		up a vocabulary the business has not agreed."""
		self.assertEqual(self.field["options"], EXPECTED_OPTIONS)

	def test_the_first_option_is_blank(self):
		"""A Select whose first option is a real value silently answers for a record
		nobody has classified."""
		self.assertTrue(self.field["options"].startswith("\n"))

	def test_it_is_mandatory(self):
		self.assertEqual(self.field["reqd"], 1)

	def test_it_carries_no_default(self):
		"""The analyst's copy has none. A default plus a mandatory flag means every new
		accommodation is Active whether anybody looked at it or not."""
		self.assertNotIn("default", self.field)

	def test_it_shows_in_the_list_view(self):
		"""The one thing the acceptance criterion spells out."""
		self.assertEqual(self.field["in_list_view"], 1)

	def test_it_can_be_filtered_on(self):
		self.assertEqual(self.field["in_standard_filter"], 1)

	def test_it_sits_where_the_analyst_site_puts_it(self):
		order = self.definition["field_order"]
		self.assertEqual(order[order.index("type") + 1], "status")


class TestTheBackfill(FrappeTestCase):
	def test_it_fills_the_records_that_predate_the_field(self):
		"""Mandatory bites on save, so without this the accommodations already on the site
		could not be saved again until somebody opened each one."""
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "patches", "v15_0", "backfill_accommodation_status.py"
			)
		)
		self.assertIn('{"status": ["in", [None, ""]]}', source)
		self.assertEqual(DEFAULT_STATUS, "Active")

	def test_it_only_fills_what_is_blank(self):
		"""A status somebody has already chosen is not this patch's to overwrite."""
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "patches", "v15_0", "backfill_accommodation_status.py"
			)
		)
		self.assertNotIn('{"status": ["!=", DEFAULT_STATUS]}', source)

	def test_the_value_it_writes_is_an_option_the_field_offers(self):
		field = next(f for f in _definition()["fields"] if f["fieldname"] == "status")
		self.assertIn(DEFAULT_STATUS, field["options"].split("\n"))

	def test_it_waits_for_the_column(self):
		"""The column arrives with the DocType on migrate; filtering on a missing one
		fails the whole query."""
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "patches", "v15_0", "backfill_accommodation_status.py"
			)
		)
		self.assertIn('frappe.db.has_column(DOCTYPE, "status")', source)

	def test_it_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.backfill_accommodation_status", patches)


class TestTheListViewStillFitsPACINumber(FrappeTestCase):
	"""Adding Status spent the last column slot.

	Frappe draws the title, a tag column, then every in_list_view field, and slices the
	result by window width - 4 below 1367px, 6 up to 1919px, 10 above. Accommodation had
	four fields besides its title, which came to exactly six; Status made five, and
	measured on this bench at 1604px the header read

	    Code | Accommodation Name | Type | Status | Ownership | ID

	with PACI Number cut. A List View Settings cap of 8 keeps both at every width.
	"""

	def test_the_status_field_did_not_displace_paci_number(self):
		shown = [f["fieldname"] for f in _definition()["fields"] if f.get("in_list_view")]
		self.assertIn("status", shown)
		self.assertIn("accommodation_paci_number", shown)

	def test_the_cap_clears_every_column_the_list_draws(self):
		"""The title is the subject column and the tag column takes one of its own, so the
		cap has to clear the in_list_view fields by two."""
		shown = [f["fieldname"] for f in _definition()["fields"] if f.get("in_list_view")]
		self.assertGreaterEqual(int(TOTAL_FIELDS), len(shown) + 2)

	def test_the_cap_is_an_option_the_field_offers(self):
		options = frappe.get_meta("List View Settings").get_field("total_fields").options
		self.assertIn(TOTAL_FIELDS, options.split("\n"))

	def test_it_writes_only_the_cap(self):
		"""List View Settings also holds whichever columns an operator chose for
		themselves; a fixture would overwrite those on every migrate."""
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "patches", "v15_0", "widen_accommodation_list_view.py"
			)
		)
		self.assertIn('frappe.db.set_value(DOCTYPE, LIST_VIEW, "total_fields", TOTAL_FIELDS)', source)
		self.assertEqual(LIST_VIEW, "Accommodation")

	def test_it_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.widen_accommodation_list_view", patches)
