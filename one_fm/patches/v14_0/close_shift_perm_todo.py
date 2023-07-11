import frappe

def execute():
	query = """
		update
			`tabTodo` as t,
			`tabShift Permission` as sp
		set
			t.status = 'Closed'
		where
            t.status = 'Open'
            AND t.reference_type = 'Shift Permission'
            AND t.reference_name = sp.name 
            AND sp.workflow_state IN ('Approved','Rejected')
	"""
	frappe.db.sql(query)