"""Attach the visa to open arrivals, and fill designation and the Transportation visa on acknowledgements still waiting."""

import frappe

from one_fm.one_fm.doctype.arrival_acknowledgement.arrival_acknowledgement import attach_file_copy


def execute():
	open_arrivals = frappe.get_all(
		"Arrival and Deployment",
		filters={
			"candidate_country_process": ["is", "set"],
			"visa_copy": ["is", "not set"],
			"status": ["not in", ["Joined", "Did Not Arrive"]],
		},
		pluck="name",
	)
	for name in open_arrivals:
		frappe.get_doc("Arrival and Deployment", name).attach_visa_copy()

	for name in frappe.get_all(
		"Arrival Acknowledgement", filters={"status": "Not Acknowledged"}, pluck="name"
	):
		acknowledgement = frappe.get_doc("Arrival Acknowledgement", name)
		acknowledgement.set_candidate_job_details()
		if acknowledgement.visa_copy and not attach_file_copy(
			acknowledgement.visa_copy, acknowledgement.doctype, acknowledgement.name, "visa_copy"
		):
			acknowledgement.visa_copy = None
		acknowledgement.db_set(
			{"designation": acknowledgement.designation, "visa_copy": acknowledgement.visa_copy},
			update_modified=False,
		)
