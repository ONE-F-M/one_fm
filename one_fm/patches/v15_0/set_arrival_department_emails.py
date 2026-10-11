"""Fill Hiring Settings with the department mailboxes that receive arrival emails."""

import frappe

ARRIVAL_DEPARTMENT_EMAILS = (
	("Onboarding", "hr@one-fm.com"),
	("Transportation", "gs@one-fm.com"),
	("General Services", "gs@one-fm.com"),
	("Finance", "finance@one-fm.com"),
	("Warehouse", "procurement@one-fm.com"),
	("Operations", "operations@one-fm.com"),
)


def execute():
	hiring_settings = frappe.get_single("Hiring Settings")
	existing = {d.department for d in hiring_settings.arrival_department_emails}
	for department, email in ARRIVAL_DEPARTMENT_EMAILS:
		if department not in existing:
			hiring_settings.append("arrival_department_emails", {"department": department, "email": email, "use": 1})
	hiring_settings.save()
