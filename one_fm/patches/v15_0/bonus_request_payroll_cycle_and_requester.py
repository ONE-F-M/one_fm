import frappe
from frappe.utils import add_months, getdate

MONTHS = (
	"January", "February", "March", "April", "May", "June",
	"July", "August", "September", "October", "November", "December",
)


def execute():
	create_payroll_cycles()
	link_requests_to_payroll_cycles()
	requested_by_to_employee()


def create_payroll_cycles():
	"""One cycle per month from September 2026 to the end of next year."""
	day = getdate("2026-09-01")
	last = getdate(f"{getdate().year + 1}-12-01")
	while day <= last:
		name = f"{MONTHS[day.month - 1]} {day.year}"
		if not frappe.db.exists("Payroll Cycle", name):
			frappe.get_doc({"doctype": "Payroll Cycle", "month": MONTHS[day.month - 1], "year": str(day.year)}).insert(
				ignore_permissions=True
			)
		day = add_months(day, 1)


def link_requests_to_payroll_cycles():
	"""Give each existing request the cycle named after its effective month."""
	for row in frappe.get_all(
		"Bonus Request",
		filters={"payroll_cycle": ["is", "not set"], "effective_month": ["is", "set"], "effective_year": ["is", "set"]},
		fields=["name", "effective_month", "effective_year"],
	):
		cycle = f"{row.effective_month} {row.effective_year}"
		if frappe.db.exists("Payroll Cycle", cycle):
			frappe.db.set_value("Bonus Request", row.name, "payroll_cycle", cycle, update_modified=False)


def requested_by_to_employee():
	"""Requested By held the requester's User; it now holds their Employee.

	The User moves to Requested By User, which assigns the Bonus Lifecycle's first task. A
	request with no requester takes its creator. A value that is already an Employee is
	left alone, so the patch can run twice.
	"""
	for row in frappe.get_all(
		"Bonus Request", fields=["name", "owner", "requested_by", "requested_by_user"]
	):
		if row.requested_by and frappe.db.exists("Employee", row.requested_by):
			continue
		user = row.requested_by or row.requested_by_user or row.owner
		employee = frappe.db.get_value("Employee", {"user_id": user}, ["name", "employee_name"], as_dict=True)
		frappe.db.set_value(
			"Bonus Request",
			row.name,
			{
				"requested_by_user": row.requested_by_user or user,
				"requested_by": employee.name if employee else None,
				"full_name": employee.employee_name if employee else None,
			},
			update_modified=False,
		)
