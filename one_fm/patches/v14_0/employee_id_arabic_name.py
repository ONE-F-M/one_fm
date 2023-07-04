import frappe

def execute():
	frappe.db.sql('''
		update
			`tabEmployee ID` as e,
			`tabEmployee` as emp
		set
			e.employee_name_in_arabic = emp.employee_name_in_arabic
		where
			 e.employee = emp.name
	''')
    
	frappe.db.sql('''
		update
			`tabEmployee ID` as e,
			`tabDesignation` as d
		set
			e.designation_in_arabic = d.designation_in_arabic
		where
			 e.designation = d.name
	''')
	frappe.db.commit()