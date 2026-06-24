import frappe
from frappe.utils import flt, now
from one_fm.api.doc_methods.leave_application_calculation import custom_get_number_of_leave_days


def execute():
	"""
	Patch to fix total_leave_days for HR-LAP-2026-00801.

	The validate_balance_leaves override (commit db192e80d, 2026-06-17) was
	calling the original hrms get_number_of_leave_days instead of
	custom_get_number_of_leave_days, so Fridays were not excluded for this
	shift worker's Annual Leave.

	Result: total_leave_days was 36 instead of 30 (6 Fridays in the period).
	"""

	leave_name = "HR-LAP-2026-00801"

	leave = frappe.db.get_value("Leave Application", leave_name, [
		"employee", "from_date", "to_date", "half_day", "half_day_date",
		"total_leave_days", "docstatus"
	], as_dict=True)

	if not leave:
		frappe.logger().info(f"[Fix Leave Days] {leave_name} not found. Skipping.")
		return

	if leave.docstatus != 1:
		frappe.logger().info(f"[Fix Leave Days] {leave_name} is not submitted. Skipping.")
		return

	correct_total = flt(custom_get_number_of_leave_days(
		employee=leave.employee,
		leave_type="Annual Leave",
		from_date=leave.from_date,
		to_date=leave.to_date,
		half_day=leave.half_day,
		half_day_date=leave.half_day_date,
	))

	old_total = flt(leave.total_leave_days)

	if correct_total == old_total:
		frappe.logger().info(
			f"[Fix Leave Days] {leave_name} already has correct total_leave_days={old_total}. Skipping."
		)
		return

	# Update Leave Application
	frappe.db.set_value("Leave Application", leave_name, {
		"total_leave_days": correct_total,
		"modified": now(),
	})

	# Update Leave Ledger Entry (leaves stored as negative)
	frappe.db.sql("""
		UPDATE `tabLeave Ledger Entry`
		SET leaves = %s, modified = %s
		WHERE transaction_type = 'Leave Application'
			AND transaction_name = %s
			AND docstatus = 1
	""", (-correct_total, now(), leave_name))

	frappe.db.commit()

	frappe.logger().info(
		f"[Fix Leave Days] Updated {leave_name}: "
		f"total_leave_days {old_total} → {correct_total}, "
		f"ledger entry leaves {-old_total} → {-correct_total}"
	)

