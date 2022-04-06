import frappe 

def shift_request_submit(self): 
	date_list = self.get_working_days(self.from_date, self.to_date)
	for date in date_list:
		assignment_doc = frappe.new_doc("Shift Assignment")
		assignment_doc.company = self.company
		assignment_doc.shift = self.operations_shift
		assignment_doc.shift_type = self.shift_type
		assignment_doc.employee = self.employee
		assignment_doc.start_date = date
		assignment_doc.shift_request = self.name
		assignment_doc.insert()
		assignment_doc.submit()
