import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow

def execute():
	# Rename role Recruitment Team Leader to Recruitment Team Lead if it exists
	if frappe.db.exists("Role", "Recruitment Team Leader"):
		print("Renaming 'Recruitment Team Leader' role to 'Recruitment Team Lead'")
		frappe.db.sql("""
			UPDATE `tabRole`
			SET role_name = "Recruitment Team Lead",
				name = "Recruitment Team Lead"
			WHERE name = "Recruitment Team Leader"
		""")
		
		frappe.db.sql("""
			UPDATE `tabHas Role`
			SET role = "Recruitment Team Lead"
			WHERE role = "Recruitment Team Leader"
		""")
		
		frappe.db.sql("""
			UPDATE `tabCustom DocPerm`
			SET role = "Recruitment Team Lead"
			WHERE role = "Recruitment Team Leader"
		""")
	else:
		# Ensure Recruitment Team Lead exists
		if not frappe.db.exists("Role", "Recruitment Team Lead"):
			print("Creating 'Recruitment Team Lead' role")
			frappe.get_doc({
				"doctype": "Role",
				"role_name": "Recruitment Team Lead"
			}).insert(ignore_permissions=True)

	print("=== Patch: Restricting PMR In-Process transition to Recruitment Team Lead ===")
	workflow_data = get_workflow_json_file("project_manpower_request.json")
	create_workflow(workflow_data)
	print("Workflow reloaded successfully.")
