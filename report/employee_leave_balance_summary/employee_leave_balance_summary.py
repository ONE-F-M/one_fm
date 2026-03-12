import frappe

def execute(filters=None):
	company = filters.get("company")

	head = [
		{"fieldname": "employee_id", "label": "Employee ID", "fieldtype": "Data", "width": 120},
		{"fieldname": "employee_name", "label": "Employee Name", "fieldtype": "Data", "width": 200},
		{"fieldname": "available_sick_leave", "label": "Available Sick Leave Days", "fieldtype": "Float", "width": 150}
	]

	data = []

	employees = frappe.db.sql("""
		SELECT
			name,
			employee_name
		FROM
			`tabEmployee`
		WHERE
			company = %(company)s
	""", {"company": company}, as_dict=True)

	for employee in employees:
		sick_leave_balance = frappe.db.sql("""
			SELECT
				SUM(leave_days)
			FROM
				`tabLeave Ledger`
			WHERE
				employee = %(employee)s
				AND leave_type = 'Sick Leave'
		""", {"employee": employee.name}, as_dict=True)[0]["SUM(leave_days)"] or 0

		data.append({
			"employee_id": employee.name,
			"employee_name": employee.employee_name,
			"available_sick_leave": sick_leave_balance
		})

	return head, data