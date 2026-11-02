# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""Nationality Percentage by PAM.

For every PAM licence, how many of the employees under company residency are of each
nationality, and what share of that licence's headcount that is. The population is the
one count_license_employees uses (pam_file link + under_company_residency = 1, whatever
the employment status), so each licence's total reconciles with PAM License Details.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	grouped = get_grouped_data(filters)
	rows = build_rows(grouped)
	return get_columns(), rows, None, get_chart(rows), get_report_summary(rows)


def get_columns():
	return [
		{
			"label": _("PAM File"),
			"fieldname": "pam_file",
			"fieldtype": "Link",
			"options": "PAM License Details",
			"width": 220,
		},
		{
			"label": _("Nationality"),
			"fieldname": "nationality",
			"fieldtype": "Link",
			"options": "Nationality",
			"width": 160,
		},
		{
			"label": _("Employees"),
			"fieldname": "employee_count",
			"fieldtype": "Int",
			"width": 110,
		},
		{
			"label": _("Percentage"),
			"fieldname": "percentage",
			"fieldtype": "Percent",
			"width": 110,
		},
	]


def get_grouped_data(filters):
	"""Employees under company residency, counted per licence and nationality.

	Filters on the pam_file link, never on the copied pam_file_number.
	"""
	return frappe.get_list(
		"Employee",
		filters={
			"under_company_residency": 1,
			"pam_file": filters.get("pam_file") or ["is", "set"],
		},
		fields=["pam_file", "one_fm_nationality", "count(name) as employee_count"],
		group_by="pam_file, one_fm_nationality",
	)


def build_rows(grouped):
	"""Turn (pam_file, nationality, count) groups into report rows with percentages.

	A licence's total is the sum of its own rows, so its percentages add up to 100.
	A licence with no rows does not appear.
	"""
	counts = {}
	for entry in grouped or []:
		pam_file = entry.get("pam_file")
		count = cint(entry.get("employee_count"))
		if not pam_file or count <= 0:
			continue
		nationality = entry.get("one_fm_nationality") or _("Not Set")
		per_pam = counts.setdefault(pam_file, {})
		per_pam[nationality] = per_pam.get(nationality, 0) + count

	rows = []
	for pam_file in sorted(counts):
		total = sum(counts[pam_file].values())
		ordered = sorted(counts[pam_file].items(), key=lambda item: (-item[1], item[0]))
		for nationality, count in ordered:
			rows.append(
				{
					"pam_file": pam_file,
					"nationality": nationality,
					"employee_count": count,
					"percentage": flt(count * 100 / total, 2),
				}
			)
	return rows


def get_chart(rows):
	"""One PAM: a pie of employee counts. Several: a bar chart of percentages per PAM."""
	if not rows:
		return None

	pam_files = []
	for row in rows:
		if row["pam_file"] not in pam_files:
			pam_files.append(row["pam_file"])

	if len(pam_files) == 1:
		return {
			"data": {
				"labels": [row["nationality"] for row in rows],
				"datasets": [
					{"name": pam_files[0], "values": [row["employee_count"] for row in rows]}
				],
			},
			"type": "pie",
		}

	totals = {}
	for row in rows:
		totals[row["nationality"]] = totals.get(row["nationality"], 0) + row["employee_count"]
	labels = sorted(totals, key=lambda nationality: (-totals[nationality], nationality))

	datasets = []
	for pam_file in pam_files:
		shares = {row["nationality"]: row["percentage"] for row in rows if row["pam_file"] == pam_file}
		datasets.append({"name": pam_file, "values": [shares.get(label, 0) for label in labels]})

	return {"data": {"labels": labels, "datasets": datasets}, "type": "bar"}


def get_report_summary(rows):
	"""One card per PAM showing its total headcount."""
	totals = {}
	for row in rows:
		totals[row["pam_file"]] = totals.get(row["pam_file"], 0) + row["employee_count"]
	return [
		{"value": total, "label": pam_file, "datatype": "Int", "indicator": "Blue"}
		for pam_file, total in totals.items()
	]
