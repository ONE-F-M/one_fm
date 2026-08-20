# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002092: what a multi-year renewal costs a Preparation row."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.preparation.preparation import (
	PER_YEAR_COST_FIELDS,
	YEAR_SCOPED_ACTIONS,
	get_grd_renewal_extension_cost,
	get_preparation_row_costing,
	years_in,
)

RENEWAL = YEAR_SCOPED_ACTIONS[1]  # Renewal (Non-Kuwaiti)
ANNUAL = {
	"work_permit_amount": 100,
	"medical_insurance_amount": 50,
	"residency_stamp_amount": 10,
	"civil_id_amount": 5,
}


def _master_rows(rows):
	settings = frappe.get_doc("HR Settings")
	settings.set("renewal_extension_cost", [])
	for row in rows:
		settings.append("renewal_extension_cost", row)
	settings.flags.ignore_permissions = True
	settings.save()
	frappe.clear_cache(doctype="HR Settings")


class TestYearsIn(FrappeTestCase):
	def test_it_reads_the_number_off_the_option(self):
		self.assertEqual(years_in("1 Year"), 1)
		self.assertEqual(years_in("2 Years"), 2)
		self.assertEqual(years_in("3 Years"), 3)

	def test_anything_unparseable_is_charged_a_single_year(self):
		"""Better the single-year rate than nothing at all."""
		for value in (None, "", "Years", "one year"):
			with self.subTest(value=value):
				self.assertEqual(years_in(value), 1)


class TestMultiYearCosting(FrappeTestCase):
	def setUp(self):
		_master_rows([
			dict(ANNUAL, renewal_or_extend=RENEWAL, no_of_years="1 Year"),
			dict(ANNUAL, renewal_or_extend=RENEWAL, no_of_years="2 Years"),
			dict(ANNUAL, renewal_or_extend=RENEWAL, no_of_years="3 Years"),
			dict(ANNUAL, renewal_or_extend="Extend 1 month"),
		])

	def test_the_annual_fees_are_multiplied_by_the_years(self):
		for years, multiplier in (("1 Year", 1), ("2 Years", 2), ("3 Years", 3)):
			with self.subTest(years=years):
				costing = get_preparation_row_costing(RENEWAL, years)
				for field in PER_YEAR_COST_FIELDS:
					self.assertEqual(costing[field], ANNUAL[field] * multiplier, field)

	def test_the_civil_id_is_never_multiplied(self):
		"""One card is issued for the whole period, whatever it costs."""
		for years in ("1 Year", "2 Years", "3 Years"):
			with self.subTest(years=years):
				self.assertEqual(
					get_preparation_row_costing(RENEWAL, years)["civil_id_amount"],
					ANNUAL["civil_id_amount"],
				)

	def test_the_master_table_still_reads_as_the_annual_rate(self):
		"""The multiplication is the row's, not HR Settings' - the master Total Amount is the
		annual figure and the two must not disagree about what a row means."""
		self.assertEqual(
			get_grd_renewal_extension_cost(RENEWAL, "3 Years")["work_permit_amount"],
			ANNUAL["work_permit_amount"],
		)

	def test_an_action_with_no_duration_is_not_multiplied(self):
		"""An extension is a one-off. The years field is hidden for it but not cleared, so a
		stale "3 Years" must not treble an extension's fees."""
		costing = get_preparation_row_costing("Extend 1 month", "3 Years")
		for field in PER_YEAR_COST_FIELDS:
			self.assertEqual(costing[field], ANNUAL[field], field)

	def test_an_unconfigured_action_still_returns_nothing(self):
		self.assertFalse(get_preparation_row_costing("Overseas", "1 Year"))

	def test_a_renewal_with_no_duration_still_returns_nothing(self):
		"""Unchanged from the master lookup: without the years there is no row to scale."""
		self.assertFalse(get_preparation_row_costing(RENEWAL))

	def test_the_multiplied_fields_are_the_three_annual_ones(self):
		self.assertEqual(
			PER_YEAR_COST_FIELDS,
			("work_permit_amount", "medical_insurance_amount", "residency_stamp_amount"),
		)
