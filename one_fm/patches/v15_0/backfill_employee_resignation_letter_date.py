import frappe


def execute():
	"""Backfill Employee.resignation_letter_date for already-submitted resignations.

	on_submit()/sync_status_to_employees() on Employee Resignation only ever wrote
	to the internal `resignation_date` custom field, never to `resignation_letter_date`
	(the field actually shown on the Employee form's Exit section) -- a plain
	fieldname mismatch, now fixed going forward. This backfills records that already
	went through the flow before the fix and are still missing the value.

	Only fills where resignation_letter_date is currently empty, so it never
	overwrites a value someone already entered manually.
	"""
	rows = frappe.db.sql(
		"""
		select eri.employee, er.resignation_initiation_date
		from `tabEmployee Resignation Item` eri
		inner join `tabEmployee Resignation` er on er.name = eri.parent
		inner join `tabEmployee` emp on emp.name = eri.employee
		where er.docstatus = 1
			and er.resignation_initiation_date is not null
			and (emp.resignation_letter_date is null or emp.resignation_letter_date = '')
		""",
		as_dict=True,
	)

	for row in rows:
		frappe.db.set_value(
			"Employee", row.employee, "resignation_letter_date",
			row.resignation_initiation_date, update_modified=False
		)
