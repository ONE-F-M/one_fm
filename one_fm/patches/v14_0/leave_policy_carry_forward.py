import frappe

def execute():
	frappe.db.sql("""
		update
			`tabLeave Policy Assignment`
		set
			carry_forward = 1
        where
			carry_forward = 0
	""")

	frappe.db.sql("""
		update
			`tabLeave Allocation`
		set
			carry_forward = 1
		where
			leave_type = 'Annual Leave'
        AND carry_forward = 0
	""")
	frappe.db.commit()