"""Drop Penalty And Investigation, Penalty Code and Penalty Level, and everything on the
site that was built on them.

The doctypes and their controllers are gone from the app, so a migrate would otherwise
leave the DocType rows, the tables and every piece of config that names them behind:
a Workflow, four Assignment Rules, seven Dashboard Charts, a Number Card and a Report
all pointing at a doctype that no longer has a controller to load.

Order matters. The config records are removed before the doctypes because each of them
names the doctype in a Link field, and a Workflow left behind would still be handed to
the workflow loader on every form load of a doctype it no longer describes.

This deletes the penalty records themselves. That is the point of the removal, but it is
not reversible from here - restore from a backup if the doctypes are ever wanted back.
"""

import frappe

DOCTYPES = ("Penalty And Investigation", "Penalty Code", "Penalty Level")

WORKFLOWS = ("Penalty & Investigation",)

ASSIGNMENT_RULES = (
	"Penalty and Investigation-HR Administrator",
	"Penalty and Investigation-Legal Manager",
	"Penalty and Investigation-General Manager",
	"Penalty and Investigation-Payroll Officer",
)

DASHBOARD_CHARTS = (
	"All Penalties",
	"Penalties By Category",
	"Penalty Applied This Year",
	"Pending Investigations",
	"Severity Level Count",
	"Top Repeat Offenders",
	"Total Penalties",
)

DASHBOARD_CHART_SOURCES = ("Total Penalties", "Severity Count", "Penalty by Category")

NUMBER_CARDS = ("Number Of Penalties",)

REPORTS = ("One FM Penalty Report",)

# The Process Tasks that named the assignees of the four assignment rules (WI-001838).
PROCESS_TASK_FILTER = {"erp_document": "Penalty And Investigation"}


def execute():
	for name in WORKFLOWS:
		_delete("Workflow", name)

	for name in ASSIGNMENT_RULES:
		_delete("Assignment Rule", name)

	for name in DASHBOARD_CHARTS:
		_delete("Dashboard Chart", name)

	for name in DASHBOARD_CHART_SOURCES:
		_delete("Dashboard Chart Source", name)

	for name in NUMBER_CARDS:
		_delete("Number Card", name)

	for name in REPORTS:
		_delete("Report", name)

	for name in frappe.get_all("Process Task", filters=PROCESS_TASK_FILTER, pluck="name"):
		_delete("Process Task", name)

	for doctype in DOCTYPES:
		# Workflow Actions, Comments and Versions are keyed by doctype name rather than by
		# a Link, so nothing else removes them once the doctype is gone.
		frappe.db.delete("Workflow Action", {"reference_doctype": doctype})
		frappe.db.delete("Comment", {"reference_doctype": doctype})
		frappe.db.delete("Version", {"ref_doctype": doctype})
		frappe.db.delete("ToDo", {"reference_type": doctype})
		frappe.db.delete("Custom Field", {"dt": doctype})
		frappe.db.delete("Property Setter", {"doc_type": doctype})
		frappe.db.delete("Custom DocPerm", {"parent": doctype})

		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)

		# delete_doc removes the DocType row but never the table it described.
		frappe.db.sql_ddl(f"drop table if exists `tab{doctype}`")


def _delete(doctype, name):
	"""Delete a config record if the site still has it.

	force skips the link check: these records point at each other (the charts at the
	number card's doctype, the assignment rules at the process tasks) and would
	otherwise have to be removed in an order that no longer matters once they are all
	going.
	"""
	if frappe.db.exists(doctype, name):
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
