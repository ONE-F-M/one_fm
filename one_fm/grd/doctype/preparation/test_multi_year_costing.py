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

	def test_the_operator_can_actually_choose_a_duration(self):
		"""The field was gated on the Action being exactly "Renewal", which the Action field has
		not offered since it split in two - so it never appeared, the row was left on the
		"1 Year" the form defaults it to, and a master row configured for two or three years
		matched nothing and fetched zeros."""
		depends_on = frappe.get_meta("Preparation Record").get_field("no_of_years").depends_on

		for action in YEAR_SCOPED_ACTIONS:
			with self.subTest(action=action):
				self.assertIn(action, depends_on)

		# The value that made it dead: an Action nothing can be set to.
		self.assertNotEqual(depends_on, 'eval: doc.renewal_or_extend == "Renewal"')

	def test_the_duration_is_offered_for_exactly_the_scoped_actions(self):
		"""Anything else is a one-off, and a duration left on one would scope its lookup by a
		year it does not have."""
		depends_on = frappe.get_meta("Preparation Record").get_field("no_of_years").depends_on
		options = frappe.get_meta("Preparation Record").get_field("renewal_or_extend").options

		for action in options.split("\n"):
			if action and action not in YEAR_SCOPED_ACTIONS:
				with self.subTest(action=action):
					self.assertNotIn(action, depends_on)

	def test_the_multiplied_fields_are_the_three_annual_ones(self):
		self.assertEqual(
			PER_YEAR_COST_FIELDS,
			("work_permit_amount", "medical_insurance_amount", "residency_stamp_amount"),
		)


class TestADurationWithNoMasterRowOfItsOwn(FrappeTestCase):
	"""WI-002092: HR Settings holds one annual rate per renewal Action, and it may be filed
	under any duration. The duration on the Preparation row is what decides the cost."""

	def setUp(self):
		# Filed under "3 Years", which is what the reporter's data actually looks like.
		_master_rows([dict(ANNUAL, renewal_or_extend=RENEWAL, no_of_years="3 Years")])

	def test_every_duration_fetches_the_rate(self):
		"""The years used to have to match exactly, so a row asking for one year against a
		"3 Years" master row fetched nothing - and the form, having already cleared the four
		fee fields, left the operator looking at zeros."""
		for years, multiplier in (("1 Year", 1), ("2 Years", 2), ("3 Years", 3)):
			with self.subTest(years=years):
				costing = get_preparation_row_costing(RENEWAL, years)
				self.assertTrue(costing, f"nothing fetched for {years}")
				for field in PER_YEAR_COST_FIELDS:
					self.assertEqual(costing[field], ANNUAL[field] * multiplier, field)

	def test_the_exact_duration_still_wins_when_it_is_configured(self):
		"""The fallback must not override a rate someone filed under a specific duration."""
		_master_rows([
			dict(ANNUAL, renewal_or_extend=RENEWAL, no_of_years="3 Years"),
			dict(ANNUAL, renewal_or_extend=RENEWAL, no_of_years="1 Year", work_permit_amount=7),
		])

		self.assertEqual(get_preparation_row_costing(RENEWAL, "1 Year")["work_permit_amount"], 7)

	def test_an_action_with_no_row_at_all_still_fetches_nothing(self):
		"""The form says so out loud rather than leaving four zeros unexplained."""
		self.assertFalse(get_preparation_row_costing("Renewal (Kuwaiti)", "1 Year"))
