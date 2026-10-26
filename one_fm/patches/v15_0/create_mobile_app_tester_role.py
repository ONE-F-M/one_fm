import frappe


def execute():
	"""Create the role that unlocks the mobile app's crash-reporting checks."""
	if not frappe.db.exists("Role", "Mobile App Tester"):
		frappe.get_doc({"doctype": "Role", "role_name": "Mobile App Tester", "desk_access": 0}).insert()
