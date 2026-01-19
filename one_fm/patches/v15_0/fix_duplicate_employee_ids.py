# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute():
	"""Find and fix duplicate employee IDs"""
	
	print("Searching for duplicate employee IDs...")
	
	# Find duplicates
	duplicates = frappe.db.sql("""
		SELECT employee_id, COUNT(*) as count
		FROM `tabEmployee`
		WHERE employee_id IS NOT NULL AND employee_id != ''
		GROUP BY employee_id
		HAVING count > 1
	""", as_dict=1)
	
	if not duplicates:
		print("No duplicate employee IDs found")
		return
	
	print(f"Found {len(duplicates)} duplicate employee IDs")
	
	for dup in duplicates:
		employee_id = dup.employee_id
		print(f"\nProcessing duplicate ID: {employee_id}")
		
		# Get all employees with this ID
		employees = frappe.db.get_all(
			"Employee",
			filters={"employee_id": employee_id},
			fields=["name", "employee_name", "creation", "date_of_joining"],
			order_by="creation asc"
		)
		
		# Keep the first one (oldest), regenerate IDs for others
		for i, emp in enumerate(employees):
			if i == 0:
				print(f"  Keeping ID for: {emp.name} ({emp.employee_name})")
			else:
				print(f"  Regenerating ID for: {emp.name} ({emp.employee_name})")
				
				try:
					# Temporarily clear the employee_id
					frappe.db.set_value("Employee", emp.name, "employee_id", None, update_modified=False)
					frappe.db.commit()
					
					# Reload and regenerate
					doc = frappe.get_doc("Employee", emp.name)
					from one_fm.hiring.utils import generate_employee_id
					generate_employee_id(doc)
					
					print(f"    New ID: {doc.employee_id}")
				except Exception as e:
					frappe.log_error(
						message=f"Failed to regenerate ID for {emp.name}: {str(e)}",
						title="Duplicate Employee ID Fix Error"
					)
					print(f"    Error: {str(e)}")
	
	frappe.db.commit()
	print("\nDuplicate fix completed")
