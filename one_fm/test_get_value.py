import frappe

def run_test():
	user_email = "test.employee@one-fm.com"
	frappe.set_user(user_email)
	
	try:
		val = frappe.db.get_value("Department", "Operations - ONEFM", "name")
		print("Department value:", val)
	except Exception as e:
		print("Exception:", type(e).__name__)
