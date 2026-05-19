import frappe
from frappe.utils import add_years, nowdate, add_months

def execute():
	frappe.flags.in_test = True
	
	# 1. Create a Company if it doesn't exist
	company_name = "Dummy Company Inc"
	if not frappe.db.exists("Company", company_name):
		comp = frappe.get_doc({
			"doctype": "Company",
			"company_name": company_name,
			"default_currency": "KWD"
		})
		comp.create_default_warehouses = lambda: None
		comp.insert(ignore_permissions=True)
		
	# Monkey-patch Employee to ignore validation hooks temporarily
	from erpnext.setup.doctype.employee.employee import Employee
	Employee.validate = lambda self: None
	Employee.before_insert = lambda self: None
	Employee.after_insert = lambda self: None

	# 2. Create Users
	users = {
		"employee@dummy.com": ["Employee"],
		"supervisor@dummy.com": ["Employee"],
		"offboarding@dummy.com": ["Offboarding Officer", "HR User"],
		"opsmanager@dummy.com": ["Operations Manager"]
	}
	
	if not frappe.db.exists("Employment Type", "Full Time"):
		frappe.get_doc({"doctype": "Employment Type", "employee_type_name": "Full Time"}).insert(ignore_permissions=True)

	
	for email, roles in users.items():
		if not frappe.db.exists("User", email):
			user = frappe.get_doc({
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0].capitalize(),
				"send_welcome_email": 0
			})
			user.insert(ignore_permissions=True)
			for role in roles:
				user.add_roles(role)

	# 3. Create Supervisor Employee
	if not frappe.db.exists("Employee", "EMP-SUPERVISOR"):
		sup = frappe.get_doc({
			"doctype": "Employee",
			"employee": "EMP-SUPERVISOR",
			"first_name": "Supervisor",
			"user_id": "supervisor@dummy.com",
			"company": company_name,
			"status": "Active",
			"date_of_joining": add_years(nowdate(), -2),
			"date_of_birth": add_years(nowdate(), -30),
			"gender": "Male",
			"residency_expiry_date": add_years(nowdate(), 1),
			"passport_expiry_date": add_years(nowdate(), 1),
			"one_fm_nationality": "Kuwaiti",
			"employment_type": "Full Time"
		})
		sup.flags.ignore_validate = True
		sup.flags.ignore_mandatory = True
		sup.flags.ignore_links = True
		sup.db_insert()

	# 4. Create Submitting Employee
	if not frappe.db.exists("Employee", "EMP-TESTER"):
		emp = frappe.get_doc({
			"doctype": "Employee",
			"employee": "EMP-TESTER",
			"first_name": "Tester",
			"user_id": "employee@dummy.com",
			"company": company_name,
			"status": "Active",
			"date_of_joining": add_years(nowdate(), -1),
			"date_of_birth": add_years(nowdate(), -25),
			"gender": "Female",
			"reports_to": "EMP-SUPERVISOR",
			"residency_expiry_date": add_years(nowdate(), 1),
			"passport_expiry_date": add_years(nowdate(), 1),
			"one_fm_nationality": "Kuwaiti",
			"employment_type": "Full Time"
		})
		emp.flags.ignore_validate = True
		emp.flags.ignore_mandatory = True
		emp.flags.ignore_links = True
		emp.db_insert()

	print("✅ Dummy Users & Employees created successfully!")
	print("To test locally:")
	print("1. Log in as employee@dummy.com to submit.")
	print("2. Log in as supervisor@dummy.com to approve.")
	print("3. Log in as offboarding@dummy.com to verify FYI notifications.")
