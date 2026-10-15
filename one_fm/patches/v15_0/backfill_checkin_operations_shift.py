"""Fill Operations Shift on existing check-ins and check-outs.

The field is a fetch_from of employee.shift, which Frappe refreshes whenever a record is
saved. Records saved before the field existed show nothing until somebody opens them, so
this fills every IN and OUT row that has an employee from the employee's current shift.
The process owner chose this over leaving historic rows blank, knowing they get today's
shift rather than the one they had at the time.

One UPDATE joined to Employee, no loop. Rows that already hold a shift are left alone, and
nothing is touched when the employee has no shift.
"""

import frappe


def execute():
	if not frappe.db.has_column("Accommodation Checkin Checkout", "operations_shift"):
		# The column arrives with the DocType on migrate. Nothing to fill in yet.
		return

	checkin = frappe.qb.DocType("Accommodation Checkin Checkout")
	employee = frappe.qb.DocType("Employee")

	(
		frappe.qb.update(checkin)
		.join(employee)
		.on(checkin.employee == employee.name)
		.set(checkin.operations_shift, employee.shift)
		.where((checkin.operations_shift.isnull()) | (checkin.operations_shift == ""))
		.where(checkin.employee.isnotnull())
		.where(checkin.employee != "")
		.where(employee.shift.isnotnull())
		.where(employee.shift != "")
	).run()
