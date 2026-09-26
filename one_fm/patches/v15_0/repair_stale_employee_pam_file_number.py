"""WI-002768: bring each employee's PAM file number back in line with the licence it names.

``pam_file_number`` is read-only and fetched from ``pam_file``, and a fetch only runs when
the employee is saved. Move somebody to another licence without saving them again, or edit
a licence's civil ID, and the copy keeps the old number while the link names the new
licence - on this site six employees linked to T4 still carried a number no licence has.

The headcounts filter on the number, so an employee whose copy has drifted is counted on
no licence at all. That is how T4 read 550 against 551 employees under its residency.

The number is repaired from the link, and every licence the repair touches is recounted so
the stored figures follow.
"""

import frappe
from frappe.query_builder import DocType, functions as fn


def execute():
	Employee = DocType("Employee")

	licences = [
		licence
		for licence in frappe.get_all(
			"PAM License Details", fields=["name", "civil_id_number_for_licensing"]
		)
		if licence.civil_id_number_for_licensing
	]

	repaired = []
	for licence in licences:
		number = licence.civil_id_number_for_licensing

		# Read before writing: the licences to recount are the ones that actually had an
		# employee move, and afterwards there is no way to tell which those were. The same
		# predicate as the update below, IfNull and all - an employee whose number is NULL
		# has drifted too, and `!=` in SQL never matches a NULL.
		drifted = (
			frappe.qb.from_(Employee)
			.select(Employee.name)
			.where(Employee.pam_file == licence.name)
			.where(fn.IfNull(Employee.pam_file_number, "") != number)
		).run()
		if not drifted:
			continue

		(
			frappe.qb.update(Employee)
			.set(Employee.pam_file_number, number)
			.where(Employee.pam_file == licence.name)
			.where(fn.IfNull(Employee.pam_file_number, "") != number)
		).run()

		repaired.append(licence)

	if not repaired:
		return

	# The figures are derived from the number that just moved. Both of them: the licence
	# total and the sector rows beneath it read the same field, so leaving either behind
	# would have them disagree about who is on the licence.
	from one_fm.grd.doctype.pam_license_details.pam_license_details import (
		recount_license,
		recount_license_total,
	)

	for licence in repaired:
		recount_license_total(licence.civil_id_number_for_licensing)
		recount_license(licence.name)
