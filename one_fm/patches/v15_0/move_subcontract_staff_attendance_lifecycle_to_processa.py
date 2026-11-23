import frappe

from one_fm.grd.processa import retire_workflow


def execute():
	retire_workflow(
		"Subcontract Staff Attendance",
		"Subcontract Staff Attendance",
		(
			"Subcontract Staff Attendance - Subcontractor",
			"Subcontract Staff Attendance - Operations Supervisor",
			"Subcontract Staff Attendance - Operations Manager",
			"Subcontract Staff Attendance - Project Manager",
			"Subcontract Staff Attendance - Finance Manager",
		),
	)
	# Task action of the map's Accounts User billing step.
	if not frappe.db.exists("Workflow Action Master", "Create Purchase Invoice"):
		frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": "Create Purchase Invoice"}).insert()
