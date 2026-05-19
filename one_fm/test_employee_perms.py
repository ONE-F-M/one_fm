import frappe

def run_test():
	# Give k.wanyama a User Permission for his own profile
	frappe.get_doc({
		"doctype": "User Permission",
		"user": "k.wanyama@one-fm.com",
		"allow": "Employee",
		"for_value": "HR-EMP-03333"
	}).insert(ignore_permissions=True)

	frappe.set_user("k.wanyama@one-fm.com")

	try:
		doc = frappe.new_doc("Employee Resignation")
		doc.resignation_initiation_date = "2026-05-15"
		doc.relieving_date = "2026-06-15"
		doc.project_allocation = "ONE FM - Head Office"
		
		# We must use real values for designation so it doesn't fail LinkValidationError
		doc.department = "Operations - ONEFM"
		# Let's find a real designation
		doc.designation = frappe.db.get_value("Designation", "General Manager - ONEFM", "name") or "Administrator"
		
		d = doc.append("employees", {})
		d.employee = "HR-EMP-02059" # Someone else!
		
		doc.insert(ignore_permissions=False)
		print("Successfully inserted document as HR Manager!")
	except Exception as e:
		print("Exception type:", type(e).__name__)
		print("Exception:", str(e))
		print("Frappe logs:", getattr(frappe.local, "message_log", []))

	# cleanup
	frappe.set_user("Administrator")
	frappe.db.sql("DELETE FROM `tabUser Permission` WHERE user=\"k.wanyama@one-fm.com\"")
	frappe.db.commit()
