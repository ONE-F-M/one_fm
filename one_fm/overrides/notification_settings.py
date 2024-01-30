import frappe

def has_permission_(doc, ptype="read", user=None):
	# - Administrator can access everything.
	# - System managers can access everything except admin.
	# - Everyone else can only access their document.
	user = user or frappe.session.user

	if user == "Administrator":
		return True

	if "System Manager" in frappe.get_roles(user) or "HR User" in frappe.get_roles(user):#Grant HR User Access
		return doc.name != "Administrator"

	return doc.name == user