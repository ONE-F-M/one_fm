import frappe

MAINTENANCE = "Maintenance"


def execute():
	"""Add the Maintenance ticket type (WI-001805).

	Every rule in M5-M8 keys off Ticket Type == "Maintenance": which SLA fields the
	form shows, whether the native helpdesk SLA is suppressed, and whether a Work
	Order can be raised. None of it can be reached until the type exists.
	"""
	if frappe.db.exists("HD Ticket Type", MAINTENANCE):
		return

	frappe.get_doc(
		{
			"doctype": "HD Ticket Type",
			"name": MAINTENANCE,
			"description": "Reactive facility maintenance reported by a client or logged "
			"by the Helpdesk team. Carries the maintenance SLA rather than the native "
			"IT support SLA.",
		}
	).insert(ignore_permissions=True)
