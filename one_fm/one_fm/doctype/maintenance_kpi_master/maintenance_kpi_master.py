# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate

# Prefix used for the auto-generated, calculation-engine-facing KPI Code Key.
KPI_CODE_PREFIX = "KPI-REQ-"

# Approved variables a manager may reference inside a KPI "Conditions" rule.
# Written as snake_case identifiers so the rule is a valid Python comparison
# that frappe.safe_eval can parse and evaluate.
# NOTE: extend this list as new measurable KPI variables are introduced.
APPROVED_KPI_VARIABLES = (
	"actual_response_minutes",
)


class MaintenanceKPIMaster(Document):
	def before_insert(self):
		# Client/Project are fetched from the Contract. They must be populated
		# before autoname runs, because the naming series embeds {client}.
		self.set_client_and_project()

	def validate(self):
		self.set_client_and_project()
		self.validate_date_range()
		self.validate_kpi_conditions()
		self.sort_penalty_tiers()
		self.validate_penalty_tiers()
		self.set_kpi_code_keys()
		self.validate_no_overlapping_master()

	def set_client_and_project(self):
		"""Keep Client and Project in sync with the linked Contract.

		These are read-only fetch fields, but we set them server-side so the
		values are guaranteed present for naming and the overlap check even if
		the client-side fetch has not run.
		"""
		if not self.contract:
			return

		client, project = frappe.db.get_value(
			"Contracts", self.contract, ["client", "project"]
		)
		self.client = client
		self.project = project

	def validate_date_range(self):
		"""Effective From must not be after Effective To."""
		if self.effective_from and self.effective_to:
			if getdate(self.effective_from) > getdate(self.effective_to):
				frappe.throw(_("Effective To cannot be before Effective From"))

	def validate_kpi_conditions(self):
		"""Confirm each KPI rule makes logical sense (AC1).

		A rule must be a valid comparison expression that references only the
		approved variables, so it cannot break the monthly calculation engine.
		Validation reuses frappe.safe_eval: the expression is parsed, safety-
		checked, and evaluated against a dummy context containing only the
		approved variables.
		"""
		if not self.kpi_information:
			return

		# Dummy numeric values so a comparison resolves to True/False.
		context = {variable: 1 for variable in APPROVED_KPI_VARIABLES}

		for row in self.kpi_information:
			if not row.conditions:
				continue

			condition = row.conditions.strip()

			try:
				result = frappe.safe_eval(condition, eval_locals=context)
			except NameError:
				frappe.throw(
					_(
						"Row {0}: The KPI rule uses an unapproved variable. "
						"Approved variables are: {1}."
					).format(row.idx, ", ".join(sorted(APPROVED_KPI_VARIABLES)))
				)
			except SyntaxError:
				frappe.throw(
					_(
						"Row {0}: The KPI rule \"{1}\" is not a valid expression. "
						"Use a comparison such as actual_response_minutes <= 45."
					).format(row.idx, condition)
				)
			except Exception:
				frappe.throw(
					_(
						"Row {0}: The KPI rule \"{1}\" could not be evaluated. "
						"Please correct it."
					).format(row.idx, condition)
				)

			# A valid rule must be a comparison (yields a boolean), not a bare
			# value or assignment.
			if not isinstance(result, bool):
				frappe.throw(
					_(
						"Row {0}: The KPI rule must be a comparison that yields "
						"true or false (e.g. actual_response_minutes <= 45)."
					).format(row.idx)
				)

	def sort_penalty_tiers(self):
		"""Auto-arrange penalty rows from highest to lowest Score Floor Threshold.

		Fixes messy manual entry so the tiers always read top-to-bottom in
		descending score order (Example 4, Case A).
		"""
		if not self.penalty_information:
			return

		self.penalty_information.sort(
			key=lambda row: flt(row.score_floor_threshold), reverse=True
		)

		# Re-sequence idx so the reordering persists and renders correctly.
		for position, row in enumerate(self.penalty_information, start=1):
			row.idx = position

	def validate_penalty_tiers(self):
		"""Confirm penalty logic after sorting (Example 4, Case B).

		Reading the descending table top-to-bottom:
		- a Score Floor Threshold must not be duplicated, and
		- the Deduction Percentage must strictly increase as the score floor drops
		  (a lower performance target can never carry a cheaper penalty).
		"""
		previous_floor = None
		previous_deduction = None

		for row in self.penalty_information:
			current_floor = flt(row.score_floor_threshold)
			current_deduction = flt(row.deduction_percentage)

			if previous_floor is not None:
				if current_floor == previous_floor:
					frappe.throw(
						_(
							"Row {0}: Score Floor Threshold {1} is duplicated. "
							"Each tier must have a unique score floor."
						).format(row.idx, current_floor)
					)

				# Rows are sorted descending, so this row's floor is the lower one.
				if current_deduction <= previous_deduction:
					frappe.throw(
						_(
							"Row {0}: Deduction Percentage must be greater than {1}% "
							"because a lower score floor ({2}) cannot carry a cheaper "
							"or equal penalty than the higher tier."
						).format(row.idx, previous_deduction, current_floor)
					)

			previous_floor = current_floor
			previous_deduction = current_deduction

	def set_kpi_code_keys(self):
		"""Lock each KPI rule to a unique, read-only KPI Code Key (Example 2).

		The monthly calculation engine reads this key to grade the right rule,
		so every row must carry a stable, globally-unique identifier.
		"""
		if not self.kpi_information:
			return

		# Collect keys already assigned system-wide plus any already on this doc.
		existing_keys = frappe.get_all(
			"KPI Target Item",
			filters={"kpi_code_key": ["like", f"{KPI_CODE_PREFIX}%"]},
			pluck="kpi_code_key",
		)
		used_keys = set(existing_keys) | {
			row.kpi_code_key for row in self.kpi_information if row.kpi_code_key
		}

		max_number = 0
		for key in used_keys:
			suffix = key.replace(KPI_CODE_PREFIX, "", 1)
			if suffix.isdigit():
				max_number = max(max_number, cint(suffix))

		for row in self.kpi_information:
			if not row.kpi_code_key:
				max_number += 1
				row.kpi_code_key = f"{KPI_CODE_PREFIX}{max_number:04d}"

	def validate_no_overlapping_master(self):
		"""Block double-booked evaluation plans (Example 3).

		A submitted + active Maintenance KPI Master for the same Client and
		Project must not share any calendar day with this record's date range.
		get_all is used deliberately: the conflict must be detected regardless of
		the current user's row-level read permissions on other records.
		"""
		if not (self.client and self.effective_from and self.effective_to):
			return

		conflicts = frappe.get_all(
			"Maintenance KPI Master",
			filters={
				"name": ["!=", self.name],
				"client": self.client,
				"project": self.project,
				"docstatus": 1,
				"is_active": 1,
				# Two ranges overlap when each starts on or before the other ends.
				"effective_from": ["<=", self.effective_to],
				"effective_to": [">=", self.effective_from],
			},
			limit=1,
		)

		if conflicts:
			frappe.throw(
				_(
					"Configuration Error: A Maintenance KPI Master is already "
					"active for this Client and Project during this date range."
				)
			)
