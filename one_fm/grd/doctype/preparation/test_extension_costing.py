# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002179: one Extension Action, priced by the number of months on the row."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.preparation.preparation import (
	CATEGORIES,
	DURATION_SCALED_COST_FIELDS,
	EXTENSION_ACTION,
	duration_in,
	get_grd_renewal_extension_cost,
	get_preparation_row_costing,
)

MONTHLY = {
	"work_permit_amount": 20,
	"medical_insurance_amount": 12,
	"residency_stamp_amount": 8,
	"civil_id_amount": 5,
}

REMOVED_ACTIONS = ("Extend 1 month", "Extend 2 months", "Extend 3 months")


def _master_rows(rows):
	settings = frappe.get_doc("HR Settings")
	settings.set("renewal_extension_cost", [])
	for row in rows:
		settings.append("renewal_extension_cost", row)
	settings.flags.ignore_permissions = True
	settings.save()
	frappe.clear_cache(doctype="HR Settings")


def _options(doctype, fieldname):
	return frappe.get_meta(doctype).get_field(fieldname).options.split("\n")


class TestExtensionIsOneAction(FrappeTestCase):
	def test_both_action_fields_offer_extension(self):
		for doctype in ("GRD Renewal Extension Cost", "Preparation Record"):
			with self.subTest(doctype=doctype):
				self.assertIn(EXTENSION_ACTION, _options(doctype, "renewal_or_extend"))

	def test_neither_still_offers_a_per_month_action(self):
		for doctype in ("GRD Renewal Extension Cost", "Preparation Record"):
			options = _options(doctype, "renewal_or_extend")
			for action in REMOVED_ACTIONS:
				with self.subTest(doctype=doctype, action=action):
					self.assertNotIn(action, options)

	def test_the_row_offers_a_duration_in_months(self):
		field = frappe.get_meta("Preparation Record").get_field("no_of_months")
		self.assertEqual(field.label, "No. of Months")
		self.assertEqual(field.options.split("\n"), ["", "1 Month", "2 Months", "3 Months"])

	def test_the_months_are_shown_only_for_an_extension(self):
		"""AC2: the field appears on the row form when the Action is Extension."""
		field = frappe.get_meta("Preparation Record").get_field("no_of_months")
		self.assertEqual(field.depends_on, f'eval:doc.renewal_or_extend == "{EXTENSION_ACTION}"')

	def test_a_renewal_batch_may_carry_it(self):
		self.assertIn(EXTENSION_ACTION, CATEGORIES["Renewal"]["actions"])
		for action in REMOVED_ACTIONS:
			self.assertNotIn(action, CATEGORIES["Renewal"]["actions"])


class TestExtensionCosting(FrappeTestCase):
	"""AC3: the monthly rate multiplied by the months, with the civil ID left flat."""

	def setUp(self):
		_master_rows([dict(MONTHLY, renewal_or_extend=EXTENSION_ACTION)])

	def test_the_monthly_fees_are_multiplied_by_the_months(self):
		for months, multiplier in (("1 Month", 1), ("2 Months", 2), ("3 Months", 3)):
			with self.subTest(months=months):
				costing = get_preparation_row_costing(EXTENSION_ACTION, no_of_months=months)
				for field in DURATION_SCALED_COST_FIELDS:
					self.assertEqual(costing[field], MONTHLY[field] * multiplier, field)

	def test_the_civil_id_is_never_multiplied(self):
		"""One card is issued for the whole extension, whatever it costs."""
		for months in ("1 Month", "2 Months", "3 Months"):
			with self.subTest(months=months):
				costing = get_preparation_row_costing(EXTENSION_ACTION, no_of_months=months)
				self.assertEqual(costing["civil_id_amount"], MONTHLY["civil_id_amount"])

	def test_an_extension_with_no_duration_is_charged_one_month(self):
		"""Better the one-month rate than nothing at all - the row is still visibly wrong."""
		costing = get_preparation_row_costing(EXTENSION_ACTION)
		for field in DURATION_SCALED_COST_FIELDS:
			self.assertEqual(costing[field], MONTHLY[field], field)

	def test_a_stale_year_does_not_narrow_the_lookup(self):
		"""The years field is hidden for an extension but not cleared when the Action changes."""
		costing = get_preparation_row_costing(EXTENSION_ACTION, "3 Years", "2 Months")
		self.assertEqual(
			costing["work_permit_amount"], MONTHLY["work_permit_amount"] * 2
		)

	def test_the_master_table_still_reads_as_the_monthly_rate(self):
		"""The multiplication is the Preparation row's, not HR Settings'."""
		self.assertEqual(
			get_grd_renewal_extension_cost(EXTENSION_ACTION)["work_permit_amount"],
			MONTHLY["work_permit_amount"],
		)

	def test_one_master_row_serves_every_duration(self):
		"""The point of the story: a duration nobody configured a row for still costs right."""
		self.assertEqual(len(frappe.get_doc("HR Settings").renewal_extension_cost), 1)
		self.assertTrue(get_preparation_row_costing(EXTENSION_ACTION, no_of_months="3 Months"))


class TestDurationIn(FrappeTestCase):
	def test_it_reads_months_as_well_as_years(self):
		self.assertEqual(duration_in("1 Month"), 1)
		self.assertEqual(duration_in("2 Months"), 2)
		self.assertEqual(duration_in("3 Months"), 3)
