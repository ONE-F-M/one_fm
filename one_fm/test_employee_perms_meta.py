import frappe

def run_test():
	user_email = "k.wanyama@one-fm.com"
	frappe.set_user(user_email)
	
	try:
		doc = frappe.new_doc("Employee Resignation")
		doc.resignation_initiation_date = "2026-05-15"
		doc.relieving_date = "2026-06-15"
		
		# Let's populate the same fields that the frontend script would populate!
		emp_data = frappe.db.get_value("Employee", "HR-EMP-03333", 
			["project", "department", "designation", "site", "employment_type", "shift", "custom_operations_role_allocation", "employee_name", "reports_to"], 
			as_dict=True)
			
		doc.project_allocation = emp_data.project
		doc.department = emp_data.department
		doc.designation = emp_data.designation
		doc.site_allocation = emp_data.site
		doc.employment_type = emp_data.employment_type
		doc.shift_allocation = emp_data.shift
		doc.operations_role_allocation = emp_data.custom_operations_role_allocation
		
		# Assume site data fills operations manager
		if emp_data.site:
			site_data = frappe.db.get_value("Operations Site", emp_data.site, 
				["site_supervisor", "operations_manager"], as_dict=True)
			if site_data:
				doc.operations_manager = site_data.get("operations_manager")
		
		d = doc.append("employees", {})
		d.employee = "HR-EMP-03333"
		d.project_allocation = emp_data.project
		d.department = emp_data.department
		d.designation = emp_data.designation
		
		print(f"User is {frappe.session.user}")
		print(f"Role is {frappe.get_roles()}")
		
		# Let's see if operations_manager has ignore_user_permissions set in the meta!
		meta = frappe.get_meta("Employee Resignation")
		om_field = meta.get_field("operations_manager")
		print(f"operations_manager ignore_user_permissions is {om_field.ignore_user_permissions}")
		
		doc.insert(ignore_permissions=False)
		print("Successfully inserted document as Kevin for Kevin!")
	except Exception as e:
		print("Exception type:", type(e).__name__)
		print("Exception args:", e.args)
		print("Exception str:", str(e))
		print("Frappe logs:", getattr(frappe.local, "message_log", []))

	# cleanup
	frappe.set_user("Administrator")
