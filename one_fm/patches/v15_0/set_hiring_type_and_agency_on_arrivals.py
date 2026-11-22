"""Fill the hiring type on every existing arrival, and the department and agency from the CCP on overseas arrivals."""

import frappe


def execute():
	for is_overseas, hiring_type in ((True, "Overseas"), (False, "Local")):
		frappe.db.set_value(
			"Arrival and Deployment",
			{"candidate_country_process": ["is", "set" if is_overseas else "not set"]},
			"hiring_type",
			hiring_type,
			update_modified=False,
		)

	for arrival in frappe.get_all(
		"Arrival and Deployment",
		filters={"candidate_country_process": ["is", "set"]},
		fields=["name", "candidate_country_process", "department"],
	):
		ccp = frappe.db.get_value(
			"Candidate Country Process",
			arrival.candidate_country_process,
			["department", "agency", "agency_name"],
			as_dict=True,
		)
		if not ccp:
			continue
		frappe.db.set_value(
			"Arrival and Deployment",
			arrival.name,
			{
				"department": ccp.department or arrival.department,
				"agency": ccp.agency,
				"agency_name": ccp.agency_name,
			},
			update_modified=False,
		)
