import frappe
from frappe.utils import getdate, now


def execute():
	"""
	Patch to extend the end date of Leave Allocation HR-LAL-2025-02083
	from 31-Jul-2026 to 23-Aug-2026.

	Scope (confirmed):
	  - Single allocation HR-LAL-2025-02083 only.
	  - Leave counts stay unchanged (only the date window is extended).
	  - Expiry handling ignored (allocation is active, to_date is in the future).

	When a Leave Allocation is submitted, its to_date is copied onto the
	Leave Ledger Entries it creates (the new-leaves credit entry and, if any,
	the carry-forward credit entry). Extending the allocation therefore also
	requires shifting those ledger entries so the balance remains valid for
	the full extended period.

	We only touch credit entries (is_expired = 0) whose to_date matches the
	OLD allocation to_date, so a carry-forward entry that may have been capped
	at an earlier expiry date is left untouched, and any expiry entry is
	deliberately skipped.
	"""

	allocation_name = "HR-LAL-2025-02083"
	old_to_date = getdate("2026-07-31")
	new_to_date = getdate("2026-08-23")

	allocation = frappe.db.get_value(
		"Leave Allocation",
		allocation_name,
		["from_date", "to_date", "docstatus"],
		as_dict=True,
	)

	if not allocation:
		frappe.logger().info(f"[Extend Leave Allocation] {allocation_name} not found. Skipping.")
		return

	if allocation.docstatus != 1:
		frappe.logger().info(
			f"[Extend Leave Allocation] {allocation_name} is not submitted "
			f"(docstatus={allocation.docstatus}). Skipping."
		)
		return

	current_to_date = getdate(allocation.to_date)

	# Idempotency: already extended.
	if current_to_date == new_to_date:
		frappe.logger().info(
			f"[Extend Leave Allocation] {allocation_name} already has to_date={new_to_date}. Skipping."
		)
		return

	# Guard: only proceed if the record is in the expected starting state.
	if current_to_date != old_to_date:
		frappe.logger().info(
			f"[Extend Leave Allocation] {allocation_name} has unexpected to_date={current_to_date} "
			f"(expected {old_to_date}). Skipping to avoid corrupting data."
		)
		return

	# New end date must not precede the allocation start date.
	if new_to_date <= getdate(allocation.from_date):
		frappe.logger().info(
			f"[Extend Leave Allocation] {allocation_name} new to_date {new_to_date} is not after "
			f"from_date {allocation.from_date}. Skipping."
		)
		return

	# 1) Extend the Leave Allocation end date.
	frappe.db.set_value(
		"Leave Allocation",
		allocation_name,
		{"to_date": new_to_date, "modified": now()},
		update_modified=False,
	)

	# 2) Shift matching credit ledger entries to the new end date.
	updated = frappe.db.sql(
		"""
		UPDATE `tabLeave Ledger Entry`
		SET to_date = %(new_to_date)s, modified = %(modified)s
		WHERE transaction_type = 'Leave Allocation'
			AND transaction_name = %(allocation)s
			AND docstatus = 1
			AND is_expired = 0
			AND to_date = %(old_to_date)s
		""",
		{
			"new_to_date": new_to_date,
			"old_to_date": old_to_date,
			"allocation": allocation_name,
			"modified": now(),
		},
	)

	frappe.db.commit()

	frappe.logger().info(
		f"[Extend Leave Allocation] {allocation_name}: to_date {old_to_date} → {new_to_date}; "
		f"leave ledger entries updated (rows affected: {frappe.db._cursor.rowcount})."
	)
