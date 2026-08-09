import frappe


def execute():
	"""Configure reference_complete_status_value for the Agency Country Process
	Template/Process Detail rows that create a linked record (Job Offer Issuance,
	Visa Processing, and each department's Appointment step) -- without it,
	_auto_create_next_records() can never recognize these steps as complete, so
	nothing downstream of them (e.g. Medical appointment after Visa Processing)
	ever auto-creates, no matter what status the linked record actually reaches.

	Values match exactly what each linked doctype's own update_tracker_status()
	writes back onto the tracker row's status field once that stage is genuinely
	done, respecting each doctype's own appointment_status options (WAFID and
	Overseas Remedical only ever reach "Booked", never "Completed").
	"""
	completion_values = {
		"Job Offer Issuance": "Offer Accepted",
		"Visa Processing": "Visa issued",
		"Medical appointment": "Booked",
		"Remedical appointment": "Booked",
		"PCC Appointment": "Completed",
		"Visa stamping appointment": "Completed",
		"Arrival & Deployment": "Joined",
	}

	skipped = []
	for doctype in ("Agency Country Process Template", "Agency Country Process", "Candidate Country Process"):
		if not frappe.db.exists("DocType", doctype):
			continue
		parents = frappe.get_all(doctype, pluck="name")
		for parent in parents:
			doc = frappe.get_doc(doctype, parent)
			changed = False
			for row in doc.agency_process_details:
				target_value = completion_values.get(row.process_name)
				if not target_value:
					continue
				if row.reference_complete_status_value == target_value and row.reference_complete_status_field == "status":
					continue
				row.reference_complete_status_field = "status"
				row.reference_complete_status_value = target_value
				changed = True
			if not changed:
				continue
			try:
				doc.save()
			except Exception:
				# doc.save() validates every row in agency_process_details, not just
				# the ones this patch touched -- a single record with unrelated,
				# pre-existing bad data (e.g. a Dynamic Link field set without its
				# reference-type field) would otherwise abort the whole patch.
				frappe.db.rollback()
				skipped.append(f"{doctype} {parent}")
				frappe.log_error(
					title="configure_agency_process_completion_values: skipped a record",
					message=frappe.get_traceback(),
				)

	if skipped:
		frappe.log_error(
			title="configure_agency_process_completion_values: records skipped",
			message="\n".join(skipped),
		)
