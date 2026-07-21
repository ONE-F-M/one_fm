import frappe


def execute():
	"""Backfill the new single-employee fields introduced when Employee Resignation,
	Employee Resignation Withdrawal, and Employee Resignation Date Adjustment dropped
	their "employees" child tables in favour of a single Employee.

	Only fills where the new field is currently empty, so it never overwrites a
	value some other code path (mobile API, formal_hearing.py, absence_case.js) may
	have already set on the singular field.

	For every doctype, only the FIRST row of the legacy "employees" child table is
	used -- these controllers already only ever acted on row 0 (set_allocations,
	set_supervisor, set_approver), so any additional rows on a historical
	multi-employee record were never functionally significant beyond the first.
	"""
	_backfill_employee_resignation()
	_backfill_employee_resignation_withdrawal()


def _backfill_employee_resignation():
	rows = frappe.db.sql(
		"""
		select er.name, eri.employee
		from `tabEmployee Resignation` er
		inner join `tabEmployee Resignation Item` eri
			on eri.parent = er.name and eri.idx = 1
		where er.employee is null or er.employee = ''
		""",
		as_dict=True,
	)
	for row in rows:
		if row.employee:
			frappe.db.set_value("Employee Resignation", row.name, "employee", row.employee, update_modified=False)


def _backfill_employee_resignation_withdrawal():
	rows = frappe.db.sql(
		"""
		select erw.name, erwi.employee, erwi.employee_name, erwi.reason, erwi.attachment
		from `tabEmployee Resignation Withdrawal` erw
		inner join `tabEmployee Resignation Withdrawal Item` erwi
			on erwi.parent = erw.name and erwi.idx = 1
		where erw.employee is null or erw.employee = ''
		""",
		as_dict=True,
	)
	for row in rows:
		update_data = {}
		if row.employee:
			update_data["employee"] = row.employee
		if row.reason:
			update_data["reason"] = row.reason
		if row.attachment:
			update_data["resignation_withdrawal_letter"] = row.attachment
		if update_data:
			frappe.db.set_value("Employee Resignation Withdrawal", row.name, update_data, update_modified=False)
