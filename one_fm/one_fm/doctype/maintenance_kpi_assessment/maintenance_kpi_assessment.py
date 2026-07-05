# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
	add_days,
	add_months,
	cint,
	flt,
	get_first_day,
	get_last_day,
	getdate,
	today,
)

from one_fm.one_fm.doctype.maintenance_kpi_master.maintenance_kpi_master import (
	KPI_VARIABLES,
	normalize_kpi_condition,
)

# Month labels in the order the Assessment's "Month" Select stores them
# (index + 1 == calendar month number).
MONTHS = [
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December",
]

# Statuses used on each Monthly KPI Assessment Item row.
STATUS_COMPLIED = "Complied"
STATUS_FAILED = "Failed"

# A Maintenance Work Order is "final" for a period once it is submitted and Completed.
COMPLETED_STATUS = "Completed"
PREVENTIVE_TYPE = "Preventive Maintenance"


class MaintenanceKPIAssessment(Document):
	def get_period_range(self):
		"""Return the (start_date, end_date_exclusive) for this assessment's Month/Year.

		completion_time on a Work Order is a Datetime, so the upper bound is the
		first day of the *next* month and the filter uses "<" to keep it inclusive
		of the whole last day.
		"""
		if not (self.month and self.year):
			return None, None

		month_number = MONTHS.index(self.month) + 1
		start = getdate(f"{cint(self.year)}-{month_number:02d}-01")
		end_exclusive = add_days(get_last_day(start), 1)
		return start, end_exclusive

	def build_kpi_rows(self):
		"""Generate one Monthly KPI Assessment Item per metric in the linked Master.

		Pre-fills KPI Name, KPI Code Key, KPI Category and the maximum Points
		Weight as read-only reference data (AC2). Existing rows are cleared first so
		the routine is safe to re-run.
		"""
		self.monthly_kpi_assessment = []

		if not self.maintenance_kpi_master:
			return

		master = frappe.get_doc("Maintenance KPI Master", self.maintenance_kpi_master)
		for kpi in master.kpi_information:
			self.append(
				"monthly_kpi_assessment",
				{
					"kpi_name": kpi.kpi_name,
					"kpi_code_key": kpi.kpi_code_key,
					"kpi_category": kpi.kpi_category,
					"points_weight": flt(kpi.points_weight),
				},
			)

	def calculate_scores(self):
		"""Grade every KPI row against the past month's completed Work Orders (AC3).

		For each row the linked Master rule (e.g. "Response Timeframe Percentage
		>= 98%") is evaluated: the referenced metric is computed from operational
		data, written to Actual Value, and the rule decides the Status. A
		"Complied" row earns its full Points Weight; a "Failed" row earns 0.

		Metrics with no source data yet (Helpdesk, Management Reporting, Asset
		Breakdowns, First-Time Fix, MTBF) are left at Actual Value 0 with a blank
		status and logged, rather than being wrongly marked Failed.
		"""
		start, end = self.get_period_range()
		if not (self.maintenance_kpi_master and self.project and start and end):
			return

		# Map each KPI Code Key to its "Complied" rule text on the Master.
		conditions_by_key = {
			kpi.kpi_code_key: kpi.conditions
			for kpi in frappe.get_all(
				"KPI Target Item",
				filters={"parent": self.maintenance_kpi_master},
				fields=["kpi_code_key", "conditions"],
			)
		}

		for row in self.monthly_kpi_assessment:
			condition = (conditions_by_key.get(row.kpi_code_key) or "").strip()
			if not condition:
				continue

			metric_id = identify_metric(condition)
			if metric_id not in METRIC_CALCULATORS:
				# Approved metric, but no operational source data wired up yet.
				frappe.log_error(
					title=_("Maintenance KPI Assessment: unsupported metric"),
					message=_(
						"KPI {0} ({1}) uses metric \"{2}\", which the calculation "
						"engine cannot compute yet. Left unscored."
					).format(row.kpi_code_key, self.name, metric_id or condition),
				)
				continue

			actual_value = flt(METRIC_CALCULATORS[metric_id](self.project, start, end))
			row.actual_value = actual_value

			normalized = normalize_kpi_condition(condition)
			try:
				complied = bool(
					frappe.safe_eval(normalized, eval_locals={metric_id: actual_value})
				)
			except Exception:
				# The Master validates rules on save, so this is defensive only.
				frappe.log_error(
					title=_("Maintenance KPI Assessment: rule evaluation failed"),
					message=_("KPI {0} ({1}): rule \"{2}\" could not be evaluated.").format(
						row.kpi_code_key, self.name, condition
					),
				)
				continue

			row.status = STATUS_COMPLIED if complied else STATUS_FAILED
			row.points_achieved = flt(row.points_weight) if complied else 0.0


def identify_metric(condition):
	"""Return the KPI metric identifier referenced by a rule, or None.

	The rule is normalized to identifier form (the same transform the engine's
	comparison uses) and the first approved identifier found is returned.
	"""
	normalized = normalize_kpi_condition(condition)
	for identifier in KPI_VARIABLES:
		if identifier in normalized:
			return identifier
	return None


# --- Metric calculators -----------------------------------------------------
# Each returns the finished value for the metric over [start, end) for a project.
# Register a metric here (keyed by its KPI_VARIABLES identifier) once its source
# data exists; unregistered metrics are skipped by calculate_scores().


def _get_completed_work_orders(project, start, end):
	"""Submitted, Completed Work Orders for a project whose completion falls in the month."""
	return frappe.get_all(
		"Maintenance Work Order",
		filters=[
			["docstatus", "=", 1],
			["project", "=", project],
			["status", "=", COMPLETED_STATUS],
			["completion_time", ">=", start],
			["completion_time", "<", end],
		],
		fields=[
			"name",
			"maintenance_type",
			"sla_response_status",
			"sla_resolution_status",
			"completion_time",
		],
	)


def _pass_percentage(work_orders, status_field):
	"""Percentage of Work Orders that Passed the given SLA status (Pass/Fail only)."""
	considered = [wo for wo in work_orders if wo.get(status_field) in ("Pass", "Fail")]
	if not considered:
		return 0.0
	passed = sum(1 for wo in considered if wo.get(status_field) == "Pass")
	return passed / len(considered) * 100.0


def calc_response_timeframe_percentage(project, start, end):
	"""% of completed Work Orders that met their response-time SLA target."""
	work_orders = _filter_by_period(_get_completed_work_orders(project, start, end), end)
	return _pass_percentage(work_orders, "sla_response_status")


def calc_resolution_timeframe_percentage(project, start, end):
	"""% of completed Work Orders that met their resolution-time SLA target."""
	work_orders = _filter_by_period(_get_completed_work_orders(project, start, end), end)
	return _pass_percentage(work_orders, "sla_resolution_status")


def calc_planned_maintenance_percentage(project, start, end):
	"""% of preventive Work Orders scheduled in the month that were Completed.

	Scoped by planned_deadline so the denominator is "what was due this month",
	regardless of whether each one was finished.
	"""
	scheduled = frappe.get_all(
		"Maintenance Work Order",
		filters={
			"docstatus": ["<", 2],
			"project": project,
			"maintenance_type": PREVENTIVE_TYPE,
			"planned_deadline": [">=", start],
		},
		fields=["name", "status", "planned_deadline"],
	)
	scheduled = [wo for wo in scheduled if getdate(wo.planned_deadline) < getdate(end)]
	if not scheduled:
		return 0.0
	completed = sum(1 for wo in scheduled if wo.status == COMPLETED_STATUS)
	return completed / len(scheduled) * 100.0


def _filter_by_period(work_orders, end_exclusive):
	"""Keep Work Orders whose completion_time is before the exclusive end bound."""
	return [
		wo for wo in work_orders if getdate(wo.completion_time) < getdate(end_exclusive)
	]


METRIC_CALCULATORS = {
	"response_timeframe_percentage": calc_response_timeframe_percentage,
	"resolution_timeframe_percentage": calc_resolution_timeframe_percentage,
	"planned_maintenance_percentage": calc_planned_maintenance_percentage,
}


@frappe.whitelist()
def rebuild_and_recalculate(assessment: str):
	"""Regenerate KPI rows from the Master and recalculate scores for a Draft.

	Lets a Maintenance Manager refresh a manually created (or late-data)
	assessment from the form. Restricted to Draft records; write permission is
	enforced on the document.
	"""
	doc = frappe.get_doc("Maintenance KPI Assessment", assessment)
	doc.check_permission("write")

	if doc.docstatus != 0:
		frappe.throw(_("Only a Draft assessment can be rebuilt and recalculated."))

	doc.build_kpi_rows()
	doc.calculate_scores()
	doc.save()
	return {"rows": len(doc.monthly_kpi_assessment)}


# --- Scheduled routine ------------------------------------------------------


def create_monthly_assessments():
	"""Monthly scheduler entry: spawn one Assessment per active KPI Master (AC1).

	Runs at the start of a billing month and assesses the month that just ended.
	For every submitted, active Maintenance KPI Master whose effective window
	covers the target month, it creates a Draft Maintenance KPI Assessment,
	auto-fills Contract/Project/Client/Master and Month/Year, generates the KPI
	rows from the Master, and calculates each score. Idempotent: a Master already
	assessed for the target period is skipped.
	"""
	target = add_months(getdate(today()), -1)
	month_start = get_first_day(target)
	month_end = get_last_day(target)
	month_label = MONTHS[getdate(target).month - 1]
	year_label = str(getdate(target).year)

	masters = frappe.get_all(
		"Maintenance KPI Master",
		filters={
			"docstatus": 1,
			"is_active": 1,
			# The Master's effective window must overlap the target month.
			"effective_from": ["<=", month_end],
			"effective_to": [">=", month_start],
		},
		fields=["name", "contract", "project", "client"],
	)

	created = 0
	for master in masters:
		exists = frappe.db.exists(
			"Maintenance KPI Assessment",
			{
				"maintenance_kpi_master": master.name,
				"month": month_label,
				"year": year_label,
				"docstatus": ["<", 2],
			},
		)
		if exists:
			continue

		try:
			assessment = frappe.new_doc("Maintenance KPI Assessment")
			assessment.contract = master.contract
			assessment.project = master.project
			assessment.client = master.client
			assessment.maintenance_kpi_master = master.name
			assessment.month = month_label
			assessment.year = year_label
			assessment.build_kpi_rows()
			assessment.calculate_scores()
			assessment.insert(ignore_permissions=True)
			created += 1
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(
				title=_("Maintenance KPI Assessment: monthly spawn failed"),
				message=_("Could not create assessment for Master {0} ({1} {2}).").format(
					master.name, month_label, year_label
				),
			)

	return created
