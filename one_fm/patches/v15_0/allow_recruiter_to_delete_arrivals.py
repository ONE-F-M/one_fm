"""Recruiters delete an arrival they submitted by mistake.

add_onboarding_officer_arrival_deployment_permission put Custom DocPerm rows on
Arrival and Deployment with read/write only, and those rows replace the DocType's
own permissions, so nobody but Administrator could delete an arrival. This gives
delete back to the roles the DocType grants it to, Recruiter and Senior Recruiter
included. has_permission still stops them deleting an arrival already marked
Arrived, Joined or Did Not Arrive.
"""

import frappe

DELETE_ROLES = ("System Manager", "HR Manager", "Recruitment Manager", "Recruiter", "Senior Recruiter")


def execute():
	if not frappe.db.exists("Custom DocPerm", {"parent": "Arrival and Deployment"}):
		# No Custom DocPerm rows: the DocType's own permissions already grant delete
		return

	for role in DELETE_ROLES:
		name = frappe.db.get_value(
			"Custom DocPerm", {"parent": "Arrival and Deployment", "role": role, "permlevel": 0}
		)
		if name:
			frappe.db.set_value("Custom DocPerm", name, "delete", 1)
		else:
			frappe.get_doc(
				{
					"doctype": "Custom DocPerm",
					"parent": "Arrival and Deployment",
					"parenttype": "DocType",
					"parentfield": "permissions",
					"role": role,
					"permlevel": 0,
					"read": 1,
					"write": 1,
					"delete": 1,
				}
			).insert()

	frappe.clear_cache(doctype="Arrival and Deployment")
