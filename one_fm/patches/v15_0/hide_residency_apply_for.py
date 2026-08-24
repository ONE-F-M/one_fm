import frappe

# WI-002105: Apply For is redundant on the form and the two exception blocks only show when
# their own checkbox is ticked. The reload picks up the visibility and mandatory rules; the
# sweep clears details left behind on records whose box is already unticked, which were
# invisible but still reaching the costing and the print format.


def execute():
	frappe.reload_doc("grd", "doctype", "residency")

	frappe.db.set_value(
		"Residency",
		{"damj_is_applicable": 0},
		{"original_civil_id": None, "upload_damj_letter": None, "upload_damj_letter_on": None},
		update_modified=False,
	)
	frappe.db.set_value(
		"Residency",
		{"residency_fine_to_be_added": 0},
		{
			"residency_fine_amount_kwd": 0,
			"upload_residency_fine_payment_receipt": None,
			"upload_residency_fine_payment_receipt_on": None,
		},
		update_modified=False,
	)
