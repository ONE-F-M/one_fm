"""Recruiters action the Job Applicant map tasks, such as Issue Job Offer.

Processa completes a task only for a user who can write the BPMN Process Instance, and the
DocType gives that to System Manager, Process Owner and Employee only. add_permission copies
those rows into Custom DocPerm before adding Recruiter, so they keep their access.
"""

import frappe
from frappe.permissions import add_permission, update_permission_property

DOCTYPE = "BPMN Process Instance"
ROLE = "Recruiter"


def execute():
	if not frappe.db.exists("DocType", DOCTYPE):
		return

	if not frappe.db.exists(
		"Custom DocPerm", {"parent": DOCTYPE, "role": ROLE, "permlevel": 0, "if_owner": 0}
	):
		add_permission(DOCTYPE, ROLE, 0)
	update_permission_property(DOCTYPE, ROLE, 0, "write", 1)
	frappe.clear_cache(doctype=DOCTYPE)
