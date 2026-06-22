import frappe


def execute():
	"""Close Job Openings linked to ERFs whose status is 'Closed'.

	Reuses the ERF controller's close_job_opening method so the closing
	logic stays in one place (sets publish=0 and status='Closed' on each
	linked Job Opening)."""
	erf_names = frappe.get_all(
		"ERF",
		filters={"status": "Closed"},
		pluck="name",
	)

	for erf_name in erf_names:
		erf = frappe.get_doc("ERF", erf_name)
		erf.close_job_opening()
