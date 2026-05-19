import frappe

def test_permissions():
	frappe.set_user("k.wanyama@one-fm.com")
	
	try:
		doc = frappe.new_doc("Employee Resignation")
		doc.resignation_initiation_date = "2026-05-15"
		
		# add child table row
		d = doc.append("employees", {})
		d.employee = "HR-EMP-03333"
		
		doc.insert(ignore_permissions=False)
		print("Successfully inserted document!")
	except Exception as e:
		print("Exception type:", type(e).__name__)
		print("Exception:", str(e))
		print("Frappe errors:", frappe.local.message_log)

