import frappe


def execute():
	"""Delete the disabled HD Ticket Client Script whose only job was a Jira ticket button."""
	name = "HD Ticket"
	script = frappe.db.get_value("Client Script", name, "script") or ""
	if "create_jira_ticket" in script:
		frappe.delete_doc("Client Script", name)
