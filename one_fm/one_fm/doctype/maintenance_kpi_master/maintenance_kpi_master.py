# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, today

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
		self.set_service_level_agreement()
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

	def set_service_level_agreement(self):
		"""Keep the read-only Service Level Agreement in sync with the Client.

		Server-side guarantee for the SLA fetch/fallback story: even when the
		record is created via API or import (where the client script never runs),
		the read-only field is re-resolved from the Client so it is always
		authoritative. An ambiguous match leaves the field blank and warns the
		user (non-blocking) rather than interrupting the save.
		"""
		result = get_active_service_level_agreement(self.client)
		self.service_level_agreement = result.get("sla")

		if result.get("message"):
			frappe.msgprint(
				result["message"],
				title=_("Service Level Agreement"),
				indicator="orange",
			)

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


def _is_active_on(sla, on_date):
	"""Return True if the SLA is valid on on_date.

	Blank Start/End Dates are treated as open-ended, so an SLA with no dates is
	always active.
	"""
	start = getdate(sla.start_date) if sla.start_date else None
	end = getdate(sla.end_date) if sla.end_date else None

	if start and on_date < start:
		return False
	if end and on_date > end:
		return False
	return True


def get_active_service_level_agreement(client):
	"""Resolve the Maintenance Service Level Agreement that applies to a client.

	Returns {"sla": <name or None>, "message": <warning or None>}.

	Matching rules (Story: SLA Fetching and Fallback):
	1. Enabled, client-specific SLAs (entity_type "Customer", entity = client)
	   that are active today (today within Start/End Date, blank = open-ended):
	     - exactly one   -> use it
	     - more than one -> ambiguous: no SLA, warn the user to pick manually
	2. If there is no clean client-specific match, fall back to the enabled
	   Default Service Level Agreement that is active today:
	     - exactly one   -> use it
	     - more than one -> ambiguous: no SLA, warn the user to pick manually
	3. Otherwise no SLA is set.

	get_all is used so the resolution is identical whether it runs in the
	controller (server guarantee) or behind the permission-checked endpoint,
	regardless of the current user's row-level read permissions on SLA records.
	"""
	if not client:
		return {"sla": None, "message": None}

	on_date = getdate(today())

	client_slas = frappe.get_all(
		"Maintenance Service Level Agreement",
		filters={"enabled": 1, "entity_type": "Customer", "entity": client},
		fields=["name", "start_date", "end_date"],
	)
	active = [sla for sla in client_slas if _is_active_on(sla, on_date)]

	if len(active) == 1:
		return {"sla": active[0].name, "message": None}
	if len(active) > 1:
		return {
			"sla": None,
			"message": _(
				"Multiple active Service Level Agreements are assigned to {0}. "
				"Please select the correct one manually."
			).format(client),
		}

	# Fallback: the global Default Service Level Agreement.
	default_slas = frappe.get_all(
		"Maintenance Service Level Agreement",
		filters={"enabled": 1, "default_service_level_agreement": 1},
		fields=["name", "start_date", "end_date"],
	)
	active_defaults = [sla for sla in default_slas if _is_active_on(sla, on_date)]

	if len(active_defaults) == 1:
		return {"sla": active_defaults[0].name, "message": None}
	if len(active_defaults) > 1:
		return {
			"sla": None,
			"message": _(
				"Multiple active Default Service Level Agreements exist. "
				"Please select one manually."
			),
		}

	return {"sla": None, "message": None}


@frappe.whitelist()
def fetch_service_level_agreement(client: str):
	"""Endpoint for the KPI Master form to resolve the SLA live on Client change.

	Read permission on the SLA doctype is required; the actual matching mirrors
	the server-side controller logic so the form and the saved record agree.
	"""
	frappe.has_permission("Maintenance Service Level Agreement", "read", throw=True)
	return get_active_service_level_agreement(client)
