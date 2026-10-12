import frappe


def execute():
	# The Processa Client Interview Shortlist map drives every state change. An active
	# Frappe Workflow adds its own Actions menu items, and those move the record without
	# the process instance, so the two fall out of step.
	frappe.db.set_value("Workflow", "Client Interview Shortlist", "is_active", 0)
	frappe.cache.hdel("workflow", "Client Interview Shortlist")
