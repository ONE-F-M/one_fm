import frappe

# HR-LAP-2026-01398 (Supriya Bhadange, Sick Leave, 2026-09-09) was approved at
# 08:19:11 - which created Leave Ledger Entry `eorarjh3s3` for -1 day - and was then
# cancelled through the list-view bulk workflow action. That cancel died in
# check_no_back_links_exist() with a LinkExistsError against the linked Attendance
# (HR-ATT-2026-500622), and Frappe rolled the transaction back, so on_cancel's
# delete_ledger_entry() never took effect. The document still ended up docstatus 2 /
# Cancelled - its `modified` is untouched at the approval timestamp and it carries no
# "Cancelled" workflow comment - so the -1 stayed in the ledger and the employee's Sick
# Leave balance reads 71 instead of 72. A replacement application (HR-LAP-2026-01401)
# was raised for the same day and holds its own -1, so this row is a pure duplicate.
#
# The row is deleted rather than cancelled: delete_ledger_entry() - the reversal that
# should have run - deletes too, and Leave Ledger Entry.on_cancel() throws
# "Only expired allocation can be cancelled" for anything that is not an expiry entry.
# frappe.db.delete is used for the same reason the framework does: get_doc().cancel()
# is not a legal route for this DocType.

LEAVE_APPLICATION = "HR-LAP-2026-01398"


def execute():
	entries = frappe.get_all(
		"Leave Ledger Entry",
		filters={
			"transaction_type": "Leave Application",
			"transaction_name": LEAVE_APPLICATION,
		},
		fields=["name", "employee", "leave_type", "leaves"],
	)
	if not entries:
		# Already cleaned up by hand, or the patch has run before.
		return

	for entry in entries:
		frappe.db.delete("Leave Ledger Entry", {"name": entry.name})
		print(
			f"one_fm: deleted orphan Leave Ledger Entry {entry.name} "
			f"({entry.leaves} {entry.leave_type} for {entry.employee}) "
			f"left behind by cancelled {LEAVE_APPLICATION}"
		)

	# No commit here: the patch runner commits.
