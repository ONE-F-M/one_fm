import frappe

def execute():
	frappe.reload_doc("one_fm", "doctype", "action_user")
	frappe.reload_doc("one_fm", "doctype", "onefm_general_setting")

	settings = frappe.get_single("ONEFM General Setting")
	
	emails = [
		"a.magar@one-fm.com",
		"abdullah@one-fm.com",
		"t.anwar@one-fm.com",
		"m.wahid@one-fm.com",
		"saoud@one-fm.com",
		"m.alsubaie@one-fm.com"
	]

	# Find users by their email
	users = frappe.get_all("User", filters={"email": ["in", emails]}, pluck="name")

	existing_users = [row.user for row in settings.get("notify_contract_expiry_users", [])]
	
	added_any = False
	for user in set(users):
		if user not in existing_users:
			settings.append("notify_contract_expiry_users", {"user": user})
			added_any = True
			
	if added_any:
		settings.save(ignore_permissions=True)
