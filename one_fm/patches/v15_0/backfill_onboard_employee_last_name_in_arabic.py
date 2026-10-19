import frappe
from frappe.query_builder import DocType
from frappe.utils import create_batch

ONBOARD_EMPLOYEE = "Onboard Employee"
ONBOARD_FIELD = "last_name_in_arabic"
EMPLOYEE_FIELD = "one_fm_last_name_in_arabic"


def execute():
	"""WI-003718: backfill Onboard Employee.last_name_in_arabic from the linked Employee.

	Only touches Onboard Employee rows where the link is set and resolves to an existing
	Employee, the Arabic last name is empty, and the Employee actually has one. Existing
	values are never overwritten. Written with ``frappe.db.set_value(update_modified=False)``
	so no lifecycle events fire and no other field (including ``modified``) changes.
	"""
	# The Employee field is a custom field; if either column is not on this site yet there
	# is nothing to copy and the join below would fail the whole migration.
	if not (
		frappe.db.has_column(ONBOARD_EMPLOYEE, ONBOARD_FIELD)
		and frappe.db.has_column("Employee", EMPLOYEE_FIELD)
	):
		return

	for name, arabic_last_name in get_rows_to_backfill():
		frappe.db.set_value(
			ONBOARD_EMPLOYEE,
			name,
			ONBOARD_FIELD,
			arabic_last_name,
			update_modified=False,
		)


def get_rows_to_backfill():
	"""One joined query - (onboard employee name, Arabic last name) pairs to write.

	The inner join drops rows whose ``employee`` is blank or points at an Employee that no
	longer exists.
	"""
	onboard = DocType(ONBOARD_EMPLOYEE)
	employee = DocType("Employee")

	rows = (
		frappe.qb.from_(onboard)
		.inner_join(employee)
		.on(onboard.employee == employee.name)
		.select(onboard.name, employee[EMPLOYEE_FIELD].as_("arabic_last_name"))
		.where(onboard.employee.isnotnull())
		.where(onboard.employee != "")
		.where(onboard[ONBOARD_FIELD].isnull() | (onboard[ONBOARD_FIELD] == ""))
		.where(employee[EMPLOYEE_FIELD].isnotnull())
		.where(employee[EMPLOYEE_FIELD] != "")
		.run(as_dict=True)
	)

	result = []
	for batch in create_batch(rows, 500):
		for row in batch:
			value = (row.arabic_last_name or "").strip()
			if value:
				result.append((row.name, value))
	return result
