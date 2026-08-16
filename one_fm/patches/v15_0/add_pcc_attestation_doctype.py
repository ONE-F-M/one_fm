import frappe

# WI-002028: the GRD record for attesting an employee's Police Clearance Certificate.
#
# Reloaded explicitly rather than left to the schema sync so the patch can be re-run on its
# own, and so anything downstream in this release that links to the doctype - the workflow
# and assignment rules in WI-002029 - finds it already there.


def execute():
	frappe.reload_doc("grd", "doctype", "pcc_attestation")
