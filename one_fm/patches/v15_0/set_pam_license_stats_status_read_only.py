import frappe

from one_fm.grd.doctype.pam_license_details.pam_license_details import recount_license

# WI-002135: the Status on a sector row is derived from the violation now, so the field is
# read-only and every existing licence is restated once.
def execute():
	frappe.reload_doc("grd", "doctype", "pam_license_stats")

	for license in frappe.get_all("PAM License Details", pluck="name"):
		recount_license(license)
