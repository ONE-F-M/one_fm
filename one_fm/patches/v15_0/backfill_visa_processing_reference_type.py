import frappe


def execute():
	"""Backfill reference_type = "Visa Request" on Candidate Country Process
	Details rows that already carry a reference_name but were left without it.

	Visa Request.update_tracker_status() writes reference_name onto the
	"Visa Processing" tracker row via a raw frappe.db.set_value call, which
	bypasses Document validation and never set reference_type alongside it.
	Since reference_name is a Dynamic Link keyed off reference_type, any row
	with one and not the other fails get_invalid_links() ("Reference Type
	must be set first") the next time anything calls a full doc.save() on the
	parent Candidate Country Process -- exactly what broke
	configure_agency_process_completion_values on 2026-08-09.
	"""
	if not frappe.db.exists("DocType", "Candidate Country Process Details"):
		return

	ccpd = frappe.qb.DocType("Candidate Country Process Details")
	frappe.qb.update(ccpd).set(
		ccpd.reference_type, "Visa Request"
	).where(
		ccpd.process_name == "Visa Processing"
	).where(
		(ccpd.reference_name.isnotnull()) & (ccpd.reference_name != "")
	).where(
		(ccpd.reference_type.isnull()) | (ccpd.reference_type == "")
	).run()
