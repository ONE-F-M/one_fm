# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002181: a standalone Visa Extension Action under the Onboarding category.

A one-month extension of an incoming candidate's entry visa. It is Onboarding rather than
Renewal - there is nothing to renew yet - and its whole output is a Residency: the candidate
has no work permit, no insurance and no civil ID for an extension to follow on from.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.preparation.preparation import (
	CATEGORIES,
	NEW_ACTION_DOCUMENTS,
	RESIDENCY_ONLY_ACTIONS,
	VISA_EXTENSION_ACTION,
	get_actions_for_category,
	get_preparation_row_costing,
)
from one_fm.grd.doctype.residency.residency import (
	ACTIONS_HANDLED_ON_SUBMIT,
	MOI_CATEGORY_BY_ACTION,
)

FEES = {
	"work_permit_amount": 0,
	"medical_insurance_amount": 0,
	"residency_stamp_amount": 18,
	"civil_id_amount": 2,
}


def _master_rows(rows):
	settings = frappe.get_doc("HR Settings")
	settings.set("renewal_extension_cost", [])
	for row in rows:
		settings.append("renewal_extension_cost", row)
	settings.flags.ignore_permissions = True
	settings.save()
	frappe.clear_cache(doctype="HR Settings")


def _options(doctype):
	return frappe.get_meta(doctype).get_field("renewal_or_extend").options.split("\n")


class TestTheActionIsOffered(FrappeTestCase):
	def test_hr_can_configure_a_master_fee_for_it(self):
		"""AC1: it is a selectable Action in the HR Costing table."""
		self.assertIn(VISA_EXTENSION_ACTION, _options("GRD Renewal Extension Cost"))

	def test_a_preparation_row_offers_it(self):
		self.assertIn(VISA_EXTENSION_ACTION, _options("Preparation Record"))

	def test_an_onboarding_batch_may_carry_it(self):
		"""AC2: it appears in the row Action dropdown of an Onboarding Preparation."""
		self.assertIn(VISA_EXTENSION_ACTION, get_actions_for_category("Onboarding"))

	def test_no_other_category_offers_it(self):
		"""An incoming candidate's visa is not something a renewal batch extends."""
		for category in CATEGORIES:
			if category == "Onboarding":
				continue
			with self.subTest(category=category):
				self.assertNotIn(VISA_EXTENSION_ACTION, get_actions_for_category(category))


class TestItsCosting(FrappeTestCase):
	"""AC3: the row takes its fees from the master entry, and its total from those."""

	def setUp(self):
		_master_rows([dict(FEES, renewal_or_extend=VISA_EXTENSION_ACTION)])

	def test_the_row_takes_the_master_fees(self):
		costing = get_preparation_row_costing(VISA_EXTENSION_ACTION)
		for field, amount in FEES.items():
			self.assertEqual(costing[field], amount, field)

	def test_nothing_is_multiplied(self):
		"""It is one month, always - neither the years nor the months scale it.

		Both fields are hidden for this Action but not cleared when the Action changes, so a
		stale duration left on the row must not touch the fees.
		"""
		costing = get_preparation_row_costing(VISA_EXTENSION_ACTION, "3 Years", "3 Months")
		for field, amount in FEES.items():
			self.assertEqual(costing[field], amount, field)

	def test_an_unconfigured_master_entry_returns_nothing(self):
		"""Rather than the previous Action's fees left sitting in the row."""
		_master_rows([{"renewal_or_extend": "Overseas", "work_permit_amount": 10}])
		self.assertFalse(get_preparation_row_costing(VISA_EXTENSION_ACTION))


class TestItOpensOnlyAResidency(FrappeTestCase):
	"""AC4: on submit it creates a Residency and nothing else."""

	def test_it_opens_a_residency_categorised_as_an_extension(self):
		self.assertEqual(MOI_CATEGORY_BY_ACTION[VISA_EXTENSION_ACTION][0], "Extend")

	def test_it_is_applied_for_the_day_the_preparation_is_submitted(self):
		"""There is no residency expiry to count back from. Left to the generic fallback,
		a blank expiry reads as today and dates the application a week in the past."""
		self.assertIsNone(MOI_CATEGORY_BY_ACTION[VISA_EXTENSION_ACTION][1])

	def test_it_goes_through_the_extend_branch_rather_than_the_dispatcher(self):
		"""The dispatcher opens a Work Permit for every Action it knows, unconditionally."""
		self.assertNotIn(VISA_EXTENSION_ACTION, ACTIONS_HANDLED_ON_SUBMIT)
		self.assertNotIn(VISA_EXTENSION_ACTION, NEW_ACTION_DOCUMENTS)

	def test_a_row_added_after_submit_opens_only_a_residency_too(self):
		"""The path a late row takes read "not one of the new Actions, so it is a renewal",
		which gave it a work permit, an insurance and a PACI that submitting the same row
		never would."""
		self.assertIn(VISA_EXTENSION_ACTION, RESIDENCY_ONLY_ACTIONS)

	def test_no_renewal_document_is_opened_for_it(self):
		"""The three submit-time creators each name the Actions they fire on."""
		from one_fm.grd.doctype.medical_insurance import medical_insurance
		from one_fm.grd.doctype.paci import paci
		from one_fm.grd.doctype.work_permit import work_permit

		for module in (work_permit, medical_insurance, paci):
			source = frappe.read_file(module.__file__.replace(".pyc", ".py"))
			self.assertNotIn(VISA_EXTENSION_ACTION, source, module.__name__)
