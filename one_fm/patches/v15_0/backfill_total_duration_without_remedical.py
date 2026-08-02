import frappe


REMEDICAL_PROCESS_NAMES = ("Remedical appointment", "Remedical results")


def execute():
	"""
	Data migration: backfill total_duration_without_remedical for existing
	Agency Country Process records. The field was added after these records
	were last saved, so it defaulted to 0 until resaved -- this computes and
	stores the correct value directly instead of relying on that.
	"""
	frappe.reload_doctype("Agency Country Process")
	if not frappe.db.has_column("Agency Country Process", "total_duration_without_remedical"):
		return

	processes = frappe.get_all("Agency Country Process", pluck="name")

	updated = 0
	for process in processes:
		rows = frappe.get_all(
			"Agency Process Details",
			filters={"parent": process, "parenttype": "Agency Country Process"},
			fields=["process_name", "duration_in_days"],
		)
		total_without_remedical = sum(
			(row.duration_in_days or 0)
			for row in rows
			if row.process_name not in REMEDICAL_PROCESS_NAMES
		)
		frappe.db.set_value(
			"Agency Country Process", process,
			"total_duration_without_remedical", total_without_remedical,
			update_modified=False
		)
		updated += 1

	frappe.msgprint(f"Backfilled total_duration_without_remedical for {updated} Agency Country Process record(s).")
