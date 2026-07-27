import frappe
from frappe.utils import create_batch


def execute():
	"""Backfill subcontractor_name on Onboard Subcontract Employee from the linked
	Subcontract Staff Shortlist for records where it was never fetched."""

	# Records missing subcontractor_name but linked to a Subcontract Staff Shortlist
	records = frappe.get_all(
		"Onboard Subcontract Employee",
		filters={
			"subcontractor_name": ["is", "not set"],
			"subcontract_staff_shortlist": ["is", "set"],
		},
		fields=["name", "subcontract_staff_shortlist"],
	)

	if not records:
		return

	# Cache the subcontractor value per shortlist to avoid repeated lookups
	shortlist_names = list({r.subcontract_staff_shortlist for r in records})
	shortlists = frappe.get_all(
		"Subcontract Staff Shortlist",
		filters={"name": ["in", shortlist_names]},
		fields=["name", "subcontractor"],
	)
	subcontractor_map = {s.name: s.subcontractor for s in shortlists}

	for batch in create_batch(records, 100):
		for record in batch:
			subcontractor = subcontractor_map.get(record.subcontract_staff_shortlist)
			if subcontractor:
				frappe.db.set_value(
					"Onboard Subcontract Employee",
					record.name,
					"subcontractor_name",
					subcontractor,
					update_modified=False,
				)
		frappe.db.commit()
