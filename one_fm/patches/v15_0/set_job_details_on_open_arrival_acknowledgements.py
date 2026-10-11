"""Fill designation, project and the Transportation visa on acknowledgements still waiting for the department."""

import frappe


def execute():
	for name in frappe.get_all("Arrival Acknowledgement", filters={"status": "Not Acknowledged"}, pluck="name"):
		acknowledgement = frappe.get_doc("Arrival Acknowledgement", name)
		acknowledgement.set_candidate_job_details()
		acknowledgement.db_set(
			{
				"designation": acknowledgement.designation,
				"project": acknowledgement.project,
				"visa_copy": acknowledgement.visa_copy,
			},
			update_modified=False,
		)
