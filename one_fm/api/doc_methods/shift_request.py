import frappe 
import pandas as pd

def shift_request_submit(self):
	for date in pd.date_range(start=self.from_date, end=self.to_date):
		if frappe.db.exists("Shift Assignment", {"employee":self.employee, "start_date":date}):
			frappe.set_value("Shift Assignment", {"employee":self.employee, "start_date":date}, "status" , "Inactive")
		assignment_doc = frappe.new_doc("Shift Assignment")
		assignment_doc.company = self.company
		assignment_doc.shift = self.operations_shift
		assignment_doc.site = self.operation_site
		assignment_doc.shift_type = self.shift_type
		assignment_doc.employee = self.employee
		assignment_doc.start_date = date
		assignment_doc.shift_request = self.name
		assignment_doc.insert()
		assignment_doc.submit()
		frappe.db.commit()

def fetch_approver(doc):
	if doc.employee:
		department = frappe.get_value("Employee", doc.employee, "department")
		shift_approver = frappe.get_value("Employee", doc.employee, "shift_request_approver")
		approvers = frappe.db.sql(
			"""select approver from `tabDepartment Approver` where parent= %s and parentfield = 'shift_request_approver'""",
			(department),
		)
		approvers = [approver[0] for approver in approvers]
		return approvers[0]