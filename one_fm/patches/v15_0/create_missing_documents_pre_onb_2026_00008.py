import frappe

from one_fm.grd.doctype.preparation.preparation import (
	create_missing_documents,
	rows_missing_documents,
)

PREPARATION = "PRE-ONB-2026-00008"


def execute():
	"""Open the GRD documents PRE-ONB-2026-00008 never got (HD-1898774).

	The batch submitted 27 Overseas rows on 2026-10-25. Each row opens six documents at
	about four seconds, the whole set runs inside the submit request, and the web server
	killed the request at 120 seconds part-way through row 24. Every creator commits as it
	goes, so the batch survived three rows short:

	    rows 1-23   complete
	    row 24      HR-EMP-04603, everything but its PCC Attestation
	    rows 25-27  HR-EMP-04604, HR-EMP-04605, HR-EMP-04626 - nothing at all

	Nothing was logged: the worker was killed, so the per-row `try` never ran and the
	operator saw a clean submit.

	create_missing_documents opens only what is missing - a row that already has its
	document is skipped, cancelled documents included - so this is safe to re-run and
	cannot duplicate the 23 complete rows.
	"""
	if not frappe.db.exists("Preparation", {"name": PREPARATION, "docstatus": 1}):
		print(f"{PREPARATION} is not a submitted Preparation on this site - nothing to do")
		return

	gaps = rows_missing_documents(PREPARATION)
	if not gaps:
		print(f"{PREPARATION} has every document already")
		return

	print(f"{PREPARATION}: opening documents for {len(gaps)} row(s)")
	for gap in gaps:
		print("  {0} {1}: {2}".format(gap["employee"], gap["employee_name"], ", ".join(gap["missing"])))

	failures = create_missing_documents(PREPARATION)

	remaining = rows_missing_documents(PREPARATION)
	if failures or remaining:
		# Not raised: a row that cannot have its documents opened - an employee who has
		# since been given a relieving date, say - is for the GRD team to resolve, and
		# failing the patch would block the rest of the migration over it.
		print(f"{PREPARATION}: {len(remaining)} row(s) still missing documents, see the Error Log")
	else:
		print(f"{PREPARATION}: every row now has its documents")
