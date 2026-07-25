# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.pricing_proposal.pricing_proposal import (
	get_budget_configuration_for_date,
)


class TestPricingProposal(FrappeTestCase):
	"""
	Dates are deliberately set in the distant past so that any Budget Configuration
	already present in the test site (effective from a real, recent date) never falls
	inside the window under test.
	"""

	def _make_config(self, effective_from, overhead_cost_percentage=10):
		return frappe.get_doc(
			{
				"doctype": "Budget Configuration",
				"effective_from": effective_from,
				"reliever_factor_percentage": 10,
				"overhead_cost_percentage": overhead_cost_percentage,
			}
		).insert(ignore_permissions=True)

	def _make_proposal(self, date_of_inception):
		proposal = frappe.get_doc(
			{"doctype": "Pricing Proposal", "date_of_inception": date_of_inception}
		)
		proposal.flags.ignore_permissions = True
		return proposal.insert(ignore_permissions=True)

	def test_picks_latest_configuration_effective_on_or_before_the_date(self):
		self._make_config("1990-01-01")
		latest = self._make_config("1995-01-01")
		self._make_config("1997-01-01")  # effective after the inception date

		self.assertEqual(get_budget_configuration_for_date("1996-01-01"), latest.name)

	def test_configuration_effective_on_the_date_itself_applies(self):
		config = self._make_config("1996-01-01")

		self.assertEqual(get_budget_configuration_for_date("1996-01-01"), config.name)

	def test_no_configuration_before_the_date_returns_none(self):
		self._make_config("1990-01-01")

		self.assertIsNone(get_budget_configuration_for_date("1980-01-01"))

	def test_missing_date_returns_none(self):
		self.assertIsNone(get_budget_configuration_for_date(None))

	def test_proposal_resolves_configuration_on_save(self):
		config = self._make_config("1995-01-01")
		proposal = self._make_proposal("1996-01-01")

		self.assertEqual(proposal.budget_configuration, config.name)
		# fetch_from keeps the overhead percentage in step with the resolved configuration
		self.assertEqual(proposal.overhead_cost_percent, config.overhead_cost_percentage)

	def test_proposal_without_applicable_configuration_is_blocked(self):
		self._make_config("1990-01-01")

		with self.assertRaises(frappe.ValidationError):
			self._make_proposal("1980-01-01")

	def test_configuration_is_frozen_on_submit(self):
		original = self._make_config("1995-01-01")
		proposal = self._make_proposal("1996-01-01")
		proposal.submit()

		# A configuration added later, but still effective before the inception date,
		# must not retroactively change what a submitted proposal was priced against.
		self._make_config("1995-06-01")
		proposal.validate()

		self.assertEqual(proposal.budget_configuration, original.name)
