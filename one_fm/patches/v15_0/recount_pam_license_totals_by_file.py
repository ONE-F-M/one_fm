"""WI-002768: restate every licence's headcount now that it is counted off the PAM file link.

The figure was counted off pam_file_number, a read-only copy fetched from pam_file that
only refreshes when the employee is saved. It counts off the link itself now, so every
figure already stored was worked out the old way and has to be restated - a licence would
otherwise keep its old number until somebody happened to open and save it.
"""

import frappe

from one_fm.grd.doctype.pam_license_details.pam_license_details import recount_license_total


def execute():
	for license_name in frappe.get_all("PAM License Details", pluck="name"):
		recount_license_total(license_name)
