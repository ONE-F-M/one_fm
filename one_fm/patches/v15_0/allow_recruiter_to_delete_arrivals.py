"""Recruiters delete an arrival they submitted by mistake.

add_onboarding_officer_arrival_deployment_permission put Custom DocPerm rows on
Arrival and Deployment with read/write only, and those rows replace the DocType's
own permissions, so nobody but Administrator could delete an arrival. This gives
delete back to the roles the DocType grants it to, Recruiter and Senior Recruiter
included. A role without a Custom DocPerm row is left alone, so it gains nothing
else. has_permission still stops recruiters deleting an arrival already marked
Arrived, Joined or Did Not Arrive.
"""

import frappe

DELETE_ROLES = ("System Manager", "HR Manager", "Recruitment Manager", "Recruiter", "Senior Recruiter")


def execute():
	for name in frappe.get_all(
		"Custom DocPerm",
		filters={"parent": "Arrival and Deployment", "role": ["in", DELETE_ROLES], "permlevel": 0},
		pluck="name",
	):
		frappe.db.set_value("Custom DocPerm", name, "delete", 1)

	frappe.clear_cache(doctype="Arrival and Deployment")
