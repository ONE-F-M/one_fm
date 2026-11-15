import frappe

PMR = "Project Manpower Request"
NAME = "PR01135"


def execute():
	"""Reopen PR01135: unlink the wrong employee and pull it out of Completed
	back to In Process.

	HR-EMP-04552 (Andrew Mkhomo) was linked as the employee who fulfilled this
	request, which closed it. He is deployed at AUM, not at the requested site
	Chery Alghanim - Al Rai, so the vacancy was never actually filled - the
	Closure Details employee link only filters on ERF and Designation, and
	ERF-2024-00042 is shared by 438 Security Guard PMRs across every project.

	"Completed" is the only doc_status 1 state in the Project Manpower Request
	workflow, so docstatus 0 + In Process is a valid combination the workflow
	can drive forward again. Child rows are reset too - Frappe refuses to save
	a draft parent whose child rows are still submitted.

	Qty fields are recomputed the way ProjectManpowerRequest.calculate_remaining_qty()
	would, and the difference is pushed back onto the ERF headcount so the ERF
	stays in step the way update_erf_headcount() keeps it.
	"""
	pmr = frappe.db.get_value(
		PMR, {"name": NAME, "docstatus": 1, "workflow_state": "Completed"},
		["name", "count", "historically_joined_qty", "erf", "qty_added_to_erf"],
		as_dict=True,
	)
	if not pmr:
		return

	frappe.db.delete("PMR Fulfilled Employee", {"parent": NAME, "parenttype": PMR})

	fulfilled = sum(
		(row.qty or 0)
		for row in frappe.get_all(
			"PMR Fulfillment Action",
			filters={"parent": NAME, "parenttype": PMR},
			fields=["qty"],
		)
	)
	remaining_qty = max(0, (pmr.count or 0) - fulfilled)
	number_to_hire = max(0, remaining_qty - (pmr.historically_joined_qty or 0))

	frappe.db.set_value(
		PMR, NAME,
		{
			"docstatus": 0,
			"workflow_state": "In Process",
			"remaining_qty": remaining_qty,
			"number_to_hire": number_to_hire,
		},
		update_modified=False,
	)

	for df in frappe.get_meta(PMR).get_table_fields():
		frappe.db.set_value(
			df.options, {"parent": NAME, "parenttype": PMR}, "docstatus", 0, update_modified=False
		)

	# In Process is an active state, so the PMR's contribution to the ERF is its
	# number_to_hire; while Completed it was contributing qty_added_to_erf.
	delta = number_to_hire - (pmr.qty_added_to_erf or 0)
	if pmr.erf and delta:
		required = frappe.db.get_value("ERF", pmr.erf, "number_of_candidates_required") or 0
		frappe.db.set_value("ERF", pmr.erf, "number_of_candidates_required", required + delta)
		frappe.db.set_value(PMR, NAME, "qty_added_to_erf", number_to_hire, update_modified=False)
