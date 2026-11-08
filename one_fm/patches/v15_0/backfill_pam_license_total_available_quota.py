"""Fill in Total Available Quota on every PAM License Details.

The column is new, so it is empty on every licence after migrate. A licence with no quota
rows (Opera File) would never be written by a recount triggered from an employee or visa,
so every licence is recounted here. recount_quota_rows writes the total even for a
licence with no rows, which gives it "0".
"""

import frappe

from one_fm.grd.doctype.pam_license_details.pam_license_details import recount_quota_rows


def execute():
	for name in frappe.get_all("PAM License Details", pluck="name"):
		recount_quota_rows(name)
