# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.pricing_proposal.pricing_proposal import (
	average_over_contract,
	calculate_total_chain,
	get_budget_configuration_for_date,
	get_margin_percentage,
	get_pifss_cost,
	get_reliever_ratio,
	get_wcf_insurance_cost,
)


class TestPricingProposal(FrappeTestCase):
	"""
	Dates are deliberately set in the distant past so that any Budget Configuration
	already present in the test site (effective from a real, recent date) never falls
	inside the window under test.
	"""

	# Every fixture below is dated in the 1990s; real configurations are dated 2026. The
	# controller's resolver and its unique-effective-from rule only started running when
	# custom was set to 0 (WI-001707), which exposed these tests to any 1990s row left
	# behind by an earlier test. Resetting the window makes each test own the resolver's
	# input outright, and never touches a real configuration.
	TEST_WINDOW_END = "2000-01-01"

	def setUp(self):
		self._reset_test_window()

	def _reset_test_window(self):
		for name in frappe.get_all(
			"Budget Configuration",
			filters={"effective_from": ["<", self.TEST_WINDOW_END]},
			pluck="name",
		):
			frappe.delete_doc("Budget Configuration", name, force=True, ignore_permissions=True)

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


class TestPricingFormulas(FrappeTestCase):
	"""
	WI-001711 formulas, exercised through the module-level helpers so each AC's worked
	example is asserted directly, without Budget Configuration or Item fixtures.
	"""

	def test_average_basic_salary_matches_the_worked_example(self):
		# AC: Basic 75, Increment 2%, Duration 5 -> 75 + (75 x 0.02 x 2.5) = 78.75
		self.assertEqual(average_over_contract(75, 2, 5), 78.75)

	def test_average_other_allowance_uses_the_same_growth(self):
		# AC: [Other] + ([Other] x [Inc %] x ([Duration]/2))
		self.assertEqual(average_over_contract(100, 2, 5), 105)

	def test_no_increment_leaves_the_amount_untouched(self):
		self.assertEqual(average_over_contract(75, 0, 5), 75)
		self.assertEqual(average_over_contract(75, 2, 0), 75)

	def test_wcf_insurance_is_a_rate_per_hundred(self):
		# AC: WCF Insurance Cost = Primary Salary x 0.66 / 100
		self.assertAlmostEqual(get_wcf_insurance_cost(78.75, 0.66), 78.75 * 0.66 / 100)

	def test_pifss_only_applies_to_kuwaiti_rows(self):
		# AC: only when Nationality = "Kuwaiti": (Primary + Primary/2) x 11.5%
		expected = (78.75 + 78.75 / 2) * 11.5 / 100
		self.assertAlmostEqual(get_pifss_cost(78.75, 11.5, "Kuwaiti"), expected)

		for nationality in ("Non-Kuwaiti", "Non-State", "", None):
			self.assertEqual(get_pifss_cost(78.75, 11.5, nationality), 0, msg=str(nationality))

	def test_reliever_ratio_is_factor_over_quantity(self):
		# AC: Reliever Ratio = Reliever Factor Percentage / Quantity
		self.assertEqual(get_reliever_ratio(10, 4), 2.5)

	def test_reliever_ratio_is_zero_without_quantity(self):
		# A row with no headcount carries no reliever cost, and dividing by it would raise.
		self.assertEqual(get_reliever_ratio(10, 0), 0)
		self.assertEqual(get_reliever_ratio(10, None), 0)

	def test_margin_percentage_guards_a_zero_selling_price(self):
		self.assertEqual(get_margin_percentage(50, 200), 25)
		self.assertEqual(get_margin_percentage(50, 0), 0)


class TestPricingProposalTotals(FrappeTestCase):
	"""
	The AC5 chain. Driven through calculate_total_chain so it runs without the Pricing
	Proposal doctype installed.
	"""

	def test_total_cost_adds_the_indirect_overhead(self):
		# AC: Total Cost (COST+OH) = Total Operation Cost + Indirect Overhead
		self.assertEqual(calculate_total_chain(1000, 200, 0).total_cost, 1200)

	def test_selling_price_applies_the_markup(self):
		# AC: Selling Price = Total Cost x (1 + Markup%)
		self.assertEqual(calculate_total_chain(1000, 200, 25).selling_price, 1500)

	def test_gross_margin_is_measured_against_operational_cost(self):
		# AC: Total Gross Margin = Selling Price - Total Operation Cost
		result = calculate_total_chain(1000, 200, 25)

		self.assertEqual(result.total_gross_margin, 500)
		self.assertAlmostEqual(result.gross_profit_margin, 500 / 1500 * 100)

	def test_net_profit_is_measured_against_total_cost(self):
		# AC: Net Profit Amount = Selling Price - Total Cost
		result = calculate_total_chain(1000, 200, 25)

		self.assertEqual(result.net_profit_amount, 300)
		self.assertAlmostEqual(result.net_profit_margin, 300 / 1500 * 100)

	def test_zero_markup_leaves_no_net_profit_but_recovers_overhead(self):
		result = calculate_total_chain(1000, 200, 0)

		self.assertEqual(result.selling_price, 1200)
		self.assertEqual(result.net_profit_amount, 0)
		self.assertEqual(result.net_profit_margin, 0)
		self.assertEqual(result.total_gross_margin, 200)

	def test_empty_proposal_does_not_raise(self):
		result = calculate_total_chain(None, None, None)

		self.assertEqual(result.total_cost, 0)
		self.assertEqual(result.gross_profit_margin, 0)
		self.assertEqual(result.net_profit_margin, 0)
