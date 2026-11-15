# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Maintenance KPI Assessment processes run as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one. The other Maintenance KPI Assessment tests read the rules from here through
rules(), and install_scripts() puts these bodies on the site for the hooks to run.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

# The Processa engine commits when an instance starts or fails. A test module starts this in
# setUpModule, so its records still roll back.
NO_COMMIT = patch("frappe.db.commit")

SCRIPTS = {
	"Create Monthly KPI Assessments": """# Monthly, on the 1st: one Maintenance KPI Assessment per submitted, active Maintenance KPI
# Master whose effective window covers the month that just ended. Each is filled with the
# Master's contract, project and client, one row per KPI, and every row graded against the
# month's completed Work Orders. The Maintenance KPI Assessment Lifecycle map then submits it.
# A Master already assessed for the month is skipped, and one that fails is logged without
# stopping the rest.
from one_fm.one_fm.doctype.maintenance_kpi_master.maintenance_kpi_master import (
	KPI_VARIABLES,
	normalize_kpi_condition,
)

# The Assessment's Month options, in calendar order.
MONTHS = ["January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December"]
STATUS_COMPLIED = "Complied"
STATUS_FAILED = "Failed"
# A Work Order counts as done for a period once it is submitted and Completed.
COMPLETED_STATUS = "Completed"
PREVENTIVE_TYPE = "Preventive Maintenance"


# The assessed month as (first day, first day of the next month). completion_time is a
# Datetime, so the queries compare with "<" against the exclusive end.
def get_period_range(assessment):
	if not (assessment.month and assessment.year):
		return None, None
	start = frappe.utils.getdate(f"{frappe.utils.cint(assessment.year)}-{MONTHS.index(assessment.month) + 1:02d}-01")
	return start, frappe.utils.add_days(frappe.utils.get_last_day(start), 1)


# One row per KPI of the Master, with its name, code key, category and maximum points.
def build_kpi_rows(assessment):
	assessment.monthly_kpi_assessment = []
	if not assessment.maintenance_kpi_master:
		return
	master = frappe.get_doc("Maintenance KPI Master", assessment.maintenance_kpi_master)
	for kpi in master.kpi_information:
		assessment.append("monthly_kpi_assessment", {
			"kpi_name": kpi.kpi_name,
			"kpi_code_key": kpi.kpi_code_key,
			"kpi_category": kpi.kpi_category,
			"points_weight": frappe.utils.flt(kpi.points_weight),
		})


# The metric a rule names, as the identifier the rule is evaluated with, else None.
def identify_metric(condition):
	normalized = normalize_kpi_condition(condition)
	for identifier in KPI_VARIABLES:
		if identifier in normalized:
			return identifier
	return None


# Submitted, Completed Work Orders of the project completed in the period.
def get_completed_work_orders(project, start, end):
	return frappe.get_all(
		"Maintenance Work Order",
		filters=[
			["docstatus", "=", 1],
			["project", "=", project],
			["status", "=", COMPLETED_STATUS],
			["completion_time", ">=", start],
			["completion_time", "<", end],
		],
		fields=["name", "maintenance_type", "sla_response_status", "sla_resolution_status", "completion_time"],
	)


# The share of Work Orders that passed, among those with a Pass or Fail verdict.
def pass_percentage(work_orders, status_field):
	considered = [wo for wo in work_orders if wo.get(status_field) in ("Pass", "Fail")]
	if not considered:
		return 0.0
	return sum(1 for wo in considered if wo.get(status_field) == "Pass") / len(considered) * 100.0


def completed_before(work_orders, end_exclusive):
	return [wo for wo in work_orders if frappe.utils.getdate(wo.completion_time) < frappe.utils.getdate(end_exclusive)]


def calc_response_timeframe_percentage(project, start, end):
	return pass_percentage(completed_before(get_completed_work_orders(project, start, end), end), "sla_response_status")


def calc_resolution_timeframe_percentage(project, start, end):
	return pass_percentage(completed_before(get_completed_work_orders(project, start, end), end), "sla_resolution_status")


# Of the Preventive Work Orders due in the month (by planned deadline), the share submitted as
# Completed on or before their deadline. A Draft marked Completed, or a late one, does not count.
def calc_planned_maintenance_percentage(project, start, end):
	scheduled = frappe.get_all(
		"Maintenance Work Order",
		filters={"docstatus": ["<", 2], "project": project, "maintenance_type": PREVENTIVE_TYPE, "planned_deadline": [">=", start]},
		fields=["name", "docstatus", "status", "planned_deadline", "completion_time"],
	)
	scheduled = [wo for wo in scheduled if frappe.utils.getdate(wo.planned_deadline) < frappe.utils.getdate(end)]
	if not scheduled:
		return 0.0
	on_time = sum(
		1 for wo in scheduled
		if wo.docstatus == 1 and wo.status == COMPLETED_STATUS and wo.completion_time
		and frappe.utils.get_datetime(wo.completion_time) <= frappe.utils.get_datetime(wo.planned_deadline)
	)
	return on_time / len(scheduled) * 100.0


# The metrics with source data. Any other metric is left unscored and logged, never marked Failed.
METRIC_CALCULATORS = {
	"response_timeframe_percentage": calc_response_timeframe_percentage,
	"resolution_timeframe_percentage": calc_resolution_timeframe_percentage,
	"planned_maintenance_percentage": calc_planned_maintenance_percentage,
}


# Grades every row by its Master rule (for example "Response Timeframe Percentage >= 98%"):
# the metric goes to Actual Value, and a Complied row earns its full Points Weight, a Failed row 0.
def calculate_scores(assessment):
	start, end = get_period_range(assessment)
	if not (assessment.maintenance_kpi_master and assessment.project and start and end):
		return

	conditions_by_key = {
		kpi.kpi_code_key: kpi.conditions
		for kpi in frappe.get_all(
			"KPI Target Item", filters={"parent": assessment.maintenance_kpi_master}, fields=["kpi_code_key", "conditions"]
		)
	}

	for row in assessment.monthly_kpi_assessment:
		condition = (conditions_by_key.get(row.kpi_code_key) or "").strip()
		if not condition:
			continue

		metric_id = identify_metric(condition)
		if metric_id not in METRIC_CALCULATORS:
			frappe.log_error(
				title="Maintenance KPI Assessment: unsupported metric",
				message='KPI {0} ({1}) uses metric "{2}", which the calculation engine cannot compute yet. Left unscored.'.format(
					row.kpi_code_key, assessment.name, metric_id or condition
				),
			)
			continue

		actual_value = frappe.utils.flt(METRIC_CALCULATORS[metric_id](assessment.project, start, end))
		row.actual_value = actual_value
		try:
			complied = bool(frappe.safe_eval(normalize_kpi_condition(condition), eval_locals={metric_id: actual_value}))
		except Exception:
			# The Master validates its rules on save, so this is defensive only.
			frappe.log_error(
				title="Maintenance KPI Assessment: rule evaluation failed",
				message='KPI {0} ({1}): rule "{2}" could not be evaluated.'.format(row.kpi_code_key, assessment.name, condition),
			)
			continue

		row.status = STATUS_COMPLIED if complied else STATUS_FAILED
		row.points_achieved = frappe.utils.flt(row.points_weight) if complied else 0.0


def create_monthly_assessments():
	target = frappe.utils.add_months(frappe.utils.getdate(frappe.utils.today()), -1)
	month_start = frappe.utils.get_first_day(target)
	month_end = frappe.utils.get_last_day(target)
	month_label = MONTHS[frappe.utils.getdate(target).month - 1]
	year_label = str(frappe.utils.getdate(target).year)

	created = 0
	for master in frappe.get_all(
		"Maintenance KPI Master",
		filters={"docstatus": 1, "is_active": 1, "effective_from": ["<=", month_end], "effective_to": [">=", month_start]},
		fields=["name", "contract", "project", "client"],
	):
		if frappe.db.exists("Maintenance KPI Assessment", {
			"maintenance_kpi_master": master.name, "month": month_label, "year": year_label, "docstatus": ["<", 2],
		}):
			continue

		save_point = "kpi_" + frappe.generate_hash(length=8)
		frappe.db.savepoint(save_point)
		try:
			assessment = frappe.new_doc("Maintenance KPI Assessment")
			assessment.update({
				"contract": master.contract, "project": master.project, "client": master.client,
				"maintenance_kpi_master": master.name, "month": month_label, "year": year_label,
			})
			build_kpi_rows(assessment)
			calculate_scores(assessment)
			assessment.insert()
			frappe.db.release_savepoint(save_point)
			created += 1
		except Exception:
			frappe.db.rollback(save_point=save_point)
			frappe.log_error(
				title="Maintenance KPI Assessment: monthly spawn failed",
				message="Could not create assessment for Master {0} ({1} {2}). {3}".format(
					master.name, month_label, year_label, frappe.get_traceback()
				),
			)
	return created


if bpmn_id:
	result["assessments_created"] = create_monthly_assessments()
""",
	"Calculate KPI Penalty": """# The single penalty summary row of a Maintenance KPI Assessment: the sum of Points Achieved,
# and the deduction of the Master's penalty tier that score falls in. Never entered by hand:
# every save runs calculate_penalty, so the deduction cannot be tampered with. The Maintenance
# KPI Assessment Lifecycle map runs it once more just before the submit.

# Tiers are read highest Score Floor Threshold first, and the first floor the score meets gives
# the deduction. Below every floor, the lowest tier applies. No matrix means no penalty.
def get_applicable_deduction(assessment, total_achieved_points):
	if not assessment.maintenance_kpi_master:
		return 0.0
	tiers = frappe.get_all(
		"Penalty Tier Matrix",
		filters={"parent": assessment.maintenance_kpi_master, "parenttype": "Maintenance KPI Master", "parentfield": "penalty_information"},
		fields=["score_floor_threshold", "deduction_percentage"],
	)
	if not tiers:
		return 0.0
	tiers.sort(key=lambda tier: frappe.utils.flt(tier.score_floor_threshold), reverse=True)
	for tier in tiers:
		if frappe.utils.flt(total_achieved_points) >= frappe.utils.flt(tier.score_floor_threshold):
			return frappe.utils.flt(tier.deduction_percentage)
	return frappe.utils.flt(tiers[-1].deduction_percentage)


def calculate_penalty(assessment):
	total = sum(frappe.utils.flt(row.points_achieved) for row in assessment.monthly_kpi_assessment)
	assessment.monthly_penalty_assessment = []
	assessment.append("monthly_penalty_assessment", {
		"total_achieved_points": total,
		"applied_penalty_percentage": get_applicable_deduction(assessment, total),
	})


if bpmn_id and doc.get("doctype") == "Maintenance KPI Assessment":
	calculate_penalty(doc)
	doc.save()
	result["penalty_percentage"] = doc.monthly_penalty_assessment[0].applied_penalty_percentage
""",
}


class Rules:
	"""A script's functions and constants as attributes. The attributes are the script's own
	namespace, so patching one (patch.object(rules, "fn")) also changes what the other
	functions of the script call."""


def rules(script_name):
	"""The functions and constants a script defines, without taking its map step."""
	namespace = {"frappe": frappe, "doc": frappe._dict(), "task_data": {}, "result": {},
		"context_doctype": "", "context_docname": "", "bpmn_id": ""}
	exec(SCRIPTS[script_name], namespace)
	found = Rules()
	found.__dict__ = namespace
	return found


def run(script_name, doc=None, **task_data):
	"""Run a script the way the Processa engine does, as a map step, and return its result."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc or frappe._dict(),
		"task_data": task_data,
		"result": result,
		"context_doctype": doc.doctype if doc else "",
		"context_docname": doc.name if doc else "",
		"bpmn_id": "test",
	}
	namespace.update(task_data)
	exec(SCRIPTS[script_name], namespace)
	return result


def install_scripts():
	"""Put these bodies on the site, so the hooks under test run the reviewed scripts."""
	for name, body in SCRIPTS.items():
		if frappe.db.exists("Server Script", name):
			frappe.db.set_value("Server Script", name, {"script": body, "disabled": 0}, update_modified=False)
		else:
			frappe.get_doc({"doctype": "Server Script", "name": name, "script_type": "API",
				"api_method": frappe.scrub(name), "script": body}).db_insert()


class TestSiteScripts(FrappeTestCase):
	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is not None:
				self.assertEqual(saved.strip(), body.strip(), msg=name)
