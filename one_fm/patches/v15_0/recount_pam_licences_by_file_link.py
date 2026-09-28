"""Restate every licence figure now that they are counted off the PAM file link.

The headcounts were counted off pam_file_number, a read-only copy fetched from pam_file
that only refreshes when the employee is saved. They count off the link itself now, so
every figure already stored was worked out the old way and has to be restated - a licence
would otherwise keep its old numbers until somebody happened to open and save it.

Both sets: the licence total and the sector rows beneath it. They read the same employees
and moved to the link together.
"""

import frappe

from one_fm.grd.doctype.pam_license_details.pam_license_details import (
	recount_license,
	recount_license_total,
)


def execute():
	for license_name in frappe.get_all("PAM License Details", pluck="name"):
		recount_license_total(license_name)
		recount_license(license_name)
