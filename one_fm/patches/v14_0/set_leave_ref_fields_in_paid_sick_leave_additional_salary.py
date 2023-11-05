import frappe

def execute():
	additional_salaries = frappe.db.get_list("Additional Salary", {'leave_application':['is', 'set'], 'docstatus': ['<', 2]})
	for additional_salary in additional_salaries:
		doc = frappe.get_doc('Additional Salary', additional_salary.name)
		doc.ref_doctype = 'Leave Application'
		doc.ref_docname = doc.leave_application
		doc.flags.ignore_validate_update_after_submit = True
		doc.save(ignore_permissions = True)
