import frappe

def execute():
	if 'leave_application' in frappe.db.get_table_columns("Additional Salary"):
		frappe.db.sql("alter table `tabAdditional Salary` drop column leave_application")

	if frappe.db.exists('Custom Field', {'name': 'Additional Salary-leave_application'}):
		frappe.delete_doc('Custom Field', 'Additional Salary-leave_application')
