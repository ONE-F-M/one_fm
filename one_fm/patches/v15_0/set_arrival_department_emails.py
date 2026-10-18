"""Fill Hiring Settings with the onboarding mailbox that receives arrival emails."""

import frappe

ARRIVAL_DEPARTMENT_EMAILS = (("Onboarding", "hr@one-fm.com"),)


def execute():
	hiring_settings = frappe.get_single("Hiring Settings")
	existing = {d.department for d in hiring_settings.arrival_department_emails}
	for department, email in ARRIVAL_DEPARTMENT_EMAILS:
		if department not in existing:
			hiring_settings.append("arrival_department_emails", {"department": department, "email": email})
	hiring_settings.save()
