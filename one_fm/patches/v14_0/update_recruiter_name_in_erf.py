import frappe

def execute():
	frappe.reload_doctype('ERF')
	erfs = frappe.get_list("ERF", filters=[["docstatus", "!=", "2"]], fields=["name", "recruiter_assigned", "secondary_recruiter_assigned"])
	for erf in erfs:
		if erf.recruiter_assigned:
			recruiter_name = frappe.db.get_value('User', erf.recruiter_assigned, "full_name")
			frappe.db.set_value('ERF', erf.name, 'recruiter_assigned_name', recruiter_name)
		if erf.secondary_recruiter_assigned:
			recruiter_name = frappe.db.get_value('User', erf.secondary_recruiter_assigned, "full_name")
			frappe.db.set_value('ERF', erf.name, 'secondary_recruiter_assigned_name', recruiter_name)
	frappe.db.commit()
