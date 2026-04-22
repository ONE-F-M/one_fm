import frappe
from frappe.utils import get_url_to_form


def execute():
	"""Copy hd_ticket values from Pathfinder Log to Comments before the field is dropped."""
	if not frappe.db.has_column("Pathfinder Log", "hd_ticket"):
		return

	logs_with_tickets = frappe.db.get_all(
		"Pathfinder Log",
		filters={"hd_ticket": ["is", "set"]},
		fields=["name", "hd_ticket"],
	)

	for log in logs_with_tickets:
		ticket_url = get_url_to_form("HD Ticket", log.hd_ticket)
		frappe.get_doc({
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "Pathfinder Log",
			"reference_name": log.name,
			"content": f"HD Ticket link migrated: <a href='{ticket_url}'>{log.hd_ticket}</a>",
		}).insert(ignore_permissions=True)

	if logs_with_tickets:
		frappe.db.commit()
