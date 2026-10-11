import frappe


def execute():
	"""Penalties are now numbered and costed at issuance and deducted without acceptance.

	- The Penalty Workflow only carried Accept/Reject, which no longer exist.
	- Penalties issued before this change were never costed, so they are kept out of the
	  monthly deduction.
	"""
	frappe.reload_doc("legal", "doctype", "penalty")

	if frappe.db.exists("Workflow", "Penalty"):
		frappe.db.set_value("Workflow", "Penalty", "is_active", 0)
		frappe.cache.hdel("workflow", "Penalty")

	Penalty = frappe.qb.DocType("Penalty")
	frappe.qb.update(Penalty).set(Penalty.deduction_not_applicable, 1).run()

	frappe.clear_cache(doctype="Penalty")
