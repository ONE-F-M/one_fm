import frappe
from frappe.permissions import has_permission

def run_test():
	frappe.get_doc({
		"doctype": "User Permission",
		"user": "k.wanyama@one-fm.com",
		"allow": "Employee",
		"for_value": "HR-EMP-03333"
	}).insert(ignore_permissions=True)

	frappe.set_user("k.wanyama@one-fm.com")

	doc = frappe.new_doc("Employee Resignation")
	print("has write perm?", has_permission("Employee Resignation", "write", doc))

	doc.employee = "HR-EMP-03333"
	print("has write perm with employee?", has_permission("Employee Resignation", "write", doc))

	# cleanup
	frappe.set_user("Administrator")
	frappe.db.sql("DELETE FROM `tabUser Permission` WHERE user=\"k.wanyama@one-fm.com\"")
	frappe.db.commit()

