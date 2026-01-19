# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe

def execute():
	"""Add unique constraint to employee_id field to prevent duplicates at database level"""
	try:
		# Check if constraint already exists
		existing_constraint = frappe.db.sql("""
			SELECT CONSTRAINT_NAME 
			FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
			WHERE TABLE_SCHEMA = DATABASE()
			AND TABLE_NAME = 'tabEmployee' 
			AND CONSTRAINT_TYPE = 'UNIQUE' 
			AND CONSTRAINT_NAME = 'unique_employee_id'
		""")
		
		if not existing_constraint:
			# Add unique constraint
			frappe.db.sql("""
				ALTER TABLE `tabEmployee` 
				ADD CONSTRAINT unique_employee_id UNIQUE (employee_id)
			""")
			frappe.db.commit()
			print("Successfully added unique constraint on employee_id")
		else:
			print("Unique constraint already exists on employee_id")
			
	except Exception as e:
		frappe.log_error(
			message=str(e),
			title="Failed to add unique constraint on employee_id"
		)
		print(f"Error: {str(e)}")
		# Don't raise the error to allow migration to continue
