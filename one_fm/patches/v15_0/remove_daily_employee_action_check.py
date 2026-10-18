import frappe

METHOD = "one_fm.one_fm.doctype.employee_daily_action.employee_daily_action.run_employee_daily_action_check_notifications"


def execute():
	for name in frappe.get_all("Scheduled Job Type", filters={"method": METHOD}, pluck="name"):
		frappe.delete_doc("Scheduled Job Type", name, ignore_permissions=True, delete_permanently=1)
	for name in frappe.get_all("Process Task", filters={"method": METHOD}, pluck="name"):
		frappe.delete_doc("Process Task", name, ignore_permissions=True)
	if frappe.db.exists("Method", METHOD):
		frappe.delete_doc("Method", METHOD, ignore_permissions=True)
