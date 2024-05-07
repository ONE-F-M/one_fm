# Copyright (c) 2024, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_first_day, get_last_day, cstr

class EmployeeIDMigrator(Document):
	@frappe.whitelist()
	def execute_migration(self, employees):
		for batch in batches(employees, 5):
			frappe.enqueue(rename_employee, batch=batch, queue="migration")

def rename_employee(batch):
	try:
		for employee in batch:
			if "employee_pk" not in employee:
				employee["employee_pk"] = generate_missing_id(employee)
	
			old_name = employee["employee"]
			new_name = employee["employee_pk"]
			
			frappe.rename_doc("Employee", old_name, new_name)
		frappe.db.commit()

	except Exception:
		frappe.log_error(frappe.get_traceback())
		frappe.db.rollback()

def generate_missing_id(employee):
	# Generate Employee ID for employees with missing employment number.
	try:
		employee_doc = frappe.get_doc("Employee", employee["employee"])
		count = len(frappe.db.sql(f"""
			SELECT name FROM tabEmployee
			WHERE date_of_joining BETWEEN '{get_first_day(employee_doc.date_of_joining)}' AND '{get_last_day(employee_doc.date_of_joining)}'""",
			as_dict=1))
		
		if count == 0:
			count = count + 1

		joining_year = cstr(employee_doc.date_of_joining.year)[-2:].zfill(2)
		joining_month = cstr(employee_doc.date_of_joining.month).zfill(2)
		serial_number = cstr(count).zfill(3)

		while frappe.db.get_list("Employee", {"employee_number": ["LIKE", f"{joining_year}{joining_month}{serial_number}%"]}):
			count = count + 1
			serial_number = cstr(count).zfill(3)

		return f"{joining_year}{joining_month}{serial_number}".upper()
	
	except Exception:
		print(frappe.get_traceback())
		frappe.throw(frappe.get_traceback())



# Generator function to create batches for 5 employees
def batches(employees, batch_size=5):
    total = len(employees)
    for idx in range(0, total, batch_size):
        yield employees[idx:min(idx + batch_size, total)]