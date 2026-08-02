# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, formatdate, getdate


# WI-001711: the eight reliever components, each scaled from a primary counterpart by
# the reliever ratio. Reliever Indemnity is derived from Reliever Annual Leave instead
# (see calculate_reliever_costs), so it is not in this map.
RELIEVER_COMPONENTS = {
	"reliever_salary": "average_basic_salary",
	"reliever_residency": "residency_stamp_fee",
	"reliever_accommodation": "accommodation_allowance",
	"reliever_transportation": "transportation_allowance",
	"reliever_uniform": "uniform_cost",
	"reliever_wcf_insurance": "wcf_insurance_fee",
	"reliever_annual_leave": "annual_leave",
}

RELIEVER_FIELDS = list(RELIEVER_COMPONENTS) + ["reliever_indemnity"]


def average_over_contract(amount, increment_percent, contract_duration_years):
	"""
	Amount grown by the increment plan, averaged over the contract (WI-001711).

	    amount + (amount x increment% x duration/2)

	The AC's worked example: 75 + (75 x 0.02 x 2.5) = 78.75.
	"""
	return flt(amount) + (
		flt(amount) * (flt(increment_percent) / 100.0) * (flt(contract_duration_years) / 2.0)
	)


def get_reliever_ratio(reliever_factor_percentage, quantity):
	"""
	Reliever Factor Percentage / Quantity.

	Zero when there is no quantity - a row with no headcount carries no reliever cost, and
	dividing by it would raise.
	"""
	if not flt(quantity):
		return 0.0

	return flt(reliever_factor_percentage) / flt(quantity)


def get_wcf_insurance_cost(primary_salary, wcf_insurance_rate):
	"""Primary Salary x rate / 100. Applies to every row, whatever the nationality."""
	return flt(primary_salary) * flt(wcf_insurance_rate) / 100.0


def get_pifss_cost(primary_salary, pifss_rate, nationality):
	"""
	(Primary Salary + Primary Salary / 2) x rate%, and only for Kuwaiti rows.

	Matches the visibility rule from WI-001710, where PIFSS Rate is shown only when
	nationality is "Kuwaiti".
	"""
	if nationality != "Kuwaiti":
		return 0.0

	base = flt(primary_salary) + (flt(primary_salary) / 2.0)
	return base * flt(pifss_rate) / 100.0


def calculate_total_chain(total_operational_cost, overhead_cost, markup_percent):
	"""
	Cost, selling price and margins (WI-001711 AC5).

	    Total Cost      = Total Operation Cost + Indirect Overhead
	    Selling Price   = Total Cost x (1 + Markup%)
	    Gross Margin    = Selling Price - Total Operation Cost
	    Net Profit      = Selling Price - Total Cost

	"Indirect Overhead" is the proposal's own Overhead Cost. Both inputs are taken as
	given: the AC does not define how either is arrived at, so neither is recomputed.
	"""
	total_cost = flt(total_operational_cost) + flt(overhead_cost)
	selling_price = total_cost * (1 + (flt(markup_percent) / 100.0))
	gross_margin = selling_price - flt(total_operational_cost)
	net_profit = selling_price - total_cost

	return frappe._dict(
		total_cost=total_cost,
		selling_price=selling_price,
		total_gross_margin=gross_margin,
		gross_profit_margin=get_margin_percentage(gross_margin, selling_price),
		net_profit_amount=net_profit,
		net_profit_margin=get_margin_percentage(net_profit, selling_price),
	)


def get_margin_percentage(amount, selling_price):
	"""Margin as a percentage of the selling price; zero when nothing is being sold."""
	if not flt(selling_price):
		return 0.0

	return flt(amount) / flt(selling_price) * 100.0


class PricingProposal(Document):
	def validate(self):
		self.set_budget_configuration()
		self.calculate_service_item_costs()
		self.calculate_totals()

	def calculate_service_item_costs(self):
		"""Row-level costs for every Manpower Service Item (WI-001711)."""
		rates = self.get_budget_rates()

		for row in self.manpower_service_items or []:
			# Average salaries over the contract, grown by the increment plan.
			row.average_basic_salary = average_over_contract(
				row.basic_salary, row.increment_plan_percentage, self.contract_duration_years
			)
			row.average_other_allowance = average_over_contract(
				row.other_allowance, row.increment_plan_percentage, self.contract_duration_years
			)
			row.average_net_salary = flt(row.average_basic_salary) + flt(row.average_other_allowance)

			# "Primary Salary" in the AC is the average basic salary.
			primary_salary = row.average_basic_salary

			row.wcf_insurance_fee = get_wcf_insurance_cost(primary_salary, rates.wcf_insurance_fee)
			row.pifss_rate = get_pifss_cost(primary_salary, rates.pifss_rate, row.nationality)

			self.calculate_reliever_costs(row, rates.reliever_factor_percentage)

	def calculate_reliever_costs(self, row, reliever_factor_percentage):
		"""
		Scale each reliever component off its primary counterpart, then total them.

		Reliever Indemnity is Reliever Annual Leave / 2 rather than a scaled primary, so it
		is computed after the rest.
		"""
		ratio = get_reliever_ratio(reliever_factor_percentage, row.quantity)

		for reliever_field, primary_field in RELIEVER_COMPONENTS.items():
			row.set(reliever_field, flt(row.get(primary_field)) * ratio)

		row.reliever_indemnity = flt(row.reliever_annual_leave) / 2.0
		row.reliever_cost = sum(flt(row.get(field)) for field in RELIEVER_FIELDS)

	def calculate_totals(self):
		"""
		Cost, selling price and margins (WI-001711).

		Total Operational Cost and Overhead Cost are inputs here - the AC does not define
		how either is arrived at, so neither is overwritten. "Indirect Overhead" in the AC
		is this proposal's Overhead Cost.
		"""
		self.update(
			calculate_total_chain(
				self.total_operational_cost, self.overhead_cost, self.markup_percent
			)
		)

	def get_budget_rates(self):
		"""Rates from the resolved Budget Configuration; zeros when none is resolved yet."""
		if not self.budget_configuration:
			return frappe._dict(
				wcf_insurance_fee=0, pifss_rate=0, reliever_factor_percentage=0
			)

		return frappe.db.get_value(
			"Budget Configuration",
			self.budget_configuration,
			["wcf_insurance_fee", "pifss_rate", "reliever_factor_percentage"],
			as_dict=True,
		) or frappe._dict(wcf_insurance_fee=0, pifss_rate=0, reliever_factor_percentage=0)

	def set_budget_configuration(self):
		"""
		Resolve the Budget Configuration in force at the Date of Inception (WI-001713).

		Only drafts resolve it: validate runs again on submit (with docstatus already 1),
		so the configuration a submitted proposal was priced against stays frozen even if
		a newer configuration is added later.
		"""
		if self.docstatus == 0:
			self.budget_configuration = get_budget_configuration_for_date(self.date_of_inception)
			self.pull_budget_configuration_values()

		if not self.budget_configuration:
			frappe.throw(
				_("No Budget Configuration is effective on or before {0}. Create one before pricing this proposal.").format(
					frappe.bold(formatdate(self.date_of_inception))
					if self.date_of_inception
					else _("the Date of Inception")
				),
				title=_("Budget Configuration Not Found"),
			)


	def pull_budget_configuration_values(self):
		"""
		Copy the resolved configuration's values onto this proposal.

		overhead_cost_percent declares fetch_from budget_configuration.overhead_cost_percentage,
		but Frappe resolves fetch_from in _validate_links(), which runs *before* validate -
		so on the save that first sets budget_configuration the link is still empty and
		nothing is fetched. It would only appear on a later save. Reading it here keeps the
		percentage in step with the configuration from the first save onwards.
		"""
		self.overhead_cost_percent = (
			frappe.db.get_value(
				"Budget Configuration", self.budget_configuration, "overhead_cost_percentage"
			)
			if self.budget_configuration
			else None
		)


def get_budget_configuration_for_date(date_of_inception):
	"""
	Latest Budget Configuration effective on or before date_of_inception.

	No permission check here: this runs inside Pricing Proposal validation, where the
	user is not required to have read access to the Budget Configuration master.
	"""
	if not date_of_inception:
		return None

	return frappe.db.get_value(
		"Budget Configuration",
		{"effective_from": ["<=", getdate(date_of_inception)]},
		"name",
		order_by="effective_from desc",
	)


@frappe.whitelist()
def get_applicable_budget_configuration(date_of_inception: str | None = None) -> str | None:
	"""Resolver for the client script, which refreshes the field when the date changes."""
	frappe.has_permission("Budget Configuration", "read", throw=True)

	return get_budget_configuration_for_date(date_of_inception)
