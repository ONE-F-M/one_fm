import frappe

def execute():
	assignment_rules = ["Pathfinder Log - Business Analyst", "Pathfinder Log - Process Owner"]
	for rule in assignment_rules:
		if frappe.db.exists("Assignment Rule", rule):
			frappe.delete_doc("Assignment Rule", rule, ignore_permissions=True)
