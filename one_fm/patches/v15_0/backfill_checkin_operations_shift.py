"""Fill Operations Shift on the open check-ins.

The field is a fetch_from of employee.shift, which Frappe refreshes whenever a check-in is
saved. Check-ins that are already open have not been saved since the field was added, so they
show nothing until somebody opens them. This fills them from the employee's current shift.

Open IN rows only (type IN, not checked out, employee set). Historic IN rows and OUT rows are
left alone on purpose: they would show today's shift, not the shift they had at the time.

One UPDATE joined to Employee, no loop. Nothing is touched when the employee has no shift.
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
		.where(checkin.type == "IN")
		.where(checkin.checked_out == 0)
		.where(checkin.employee.isnotnull())
		.where(checkin.employee != "")
		.where(employee.shift.isnotnull())
		.where(employee.shift != "")
	).run()
