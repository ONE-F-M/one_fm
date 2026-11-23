import frappe

from one_fm.grd.processa import retire_workflow


def execute():
	retire_workflow(
		"Purchase Order",
		"Purchase Order",
		(
			"Purchase Order Purchase Manager Action",
			"Purchase Order Finance Manager Action",
			"Purchase Order Approver Action",
		),
	)
	# The map's "Notify Purchase Order Approved" script sends this email now.
	if frappe.db.exists("Notification", "Purchase Order"):
		frappe.db.set_value("Notification", "Purchase Order", "enabled", 0)
