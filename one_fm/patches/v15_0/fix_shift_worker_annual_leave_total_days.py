import frappe
from frappe.utils import flt, now
from one_fm.api.doc_methods.leave_application_calculation import custom_get_number_of_leave_days


def execute():
	"""
	Patch to fix total_leave_days for shift worker Annual Leave applications
	affected by the regression introduced on 2026-06-17 (commit db192e80d).

	The validate_balance_leaves override was calling the original hrms
	get_number_of_leave_days (which does not exclude Fridays for shift workers)
	instead of custom_get_number_of_leave_days.

	This patch:
	1. Finds all submitted Annual Leave applications for shift workers
	   created/modified on or after 2026-06-17
	2. Recalculates total_leave_days using custom_get_number_of_leave_days
	3. Updates the Leave Application and Leave Ledger Entry if the value differs
	"""

	# Find affected leave applications:
	# - Annual Leave
	# - Submitted (docstatus=1)
	# - Employee is a shift worker
	# - Modified on or after 2026-06-17 (date the regression was introduced)
	affected_leaves = frappe.db.sql("""
		SELECT
			la.name,
			la.employee,
			la.from_date,
			la.to_date,
			la.half_day,
			la.half_day_date,
			la.total_leave_days as old_total_leave_days,
			la.leave_balance
		FROM `tabLeave Application` la
		JOIN `tabEmployee` e ON la.employee = e.name
		WHERE la.leave_type = 'Annual Leave'
			AND la.docstatus = 1
			AND e.shift_working = 1
			AND la.modified >= '2026-06-17'
	""", as_dict=True)

	if not affected_leaves:
		frappe.logger().info(
			"[Fix Shift Worker Leave Days] No affected leave applications found."
		)
		return

	updated_count = 0

	for leave in affected_leaves:
		# Recalculate using the correct custom function
		correct_total = custom_get_number_of_leave_days(
			employee=leave.employee,
			leave_type="Annual Leave",
			from_date=leave.from_date,
			to_date=leave.to_date,
			half_day=leave.half_day,
			half_day_date=leave.half_day_date,
		)

		correct_total = flt(correct_total)
		old_total = flt(leave.old_total_leave_days)

		# Only update if the value actually differs
		if correct_total == old_total:
			continue

		# Update Leave Application
		frappe.db.set_value("Leave Application", leave.name, {
			"total_leave_days": correct_total,
			"modified": now(),
		})

		# Update corresponding Leave Ledger Entry (leaves are stored as negative)
		# The ledger entry stores: leaves = -total_leave_days
		frappe.db.sql("""
			UPDATE `tabLeave Ledger Entry`
			SET leaves = %s, modified = %s
			WHERE transaction_type = 'Leave Application'
				AND transaction_name = %s
				AND docstatus = 1
		""", (-correct_total, now(), leave.name))

		updated_count += 1

		frappe.logger().info(
			f"[Fix Shift Worker Leave Days] Updated {leave.name} "
			f"(Employee: {leave.employee}): "
			f"total_leave_days {old_total} → {correct_total}, "
			f"ledger entry leaves {-old_total} → {-correct_total}"
		)

	frappe.db.commit()

	frappe.logger().info(
		f"[Fix Shift Worker Leave Days] Patch complete. "
		f"Updated {updated_count} of {len(affected_leaves)} leave applications checked."
	)
