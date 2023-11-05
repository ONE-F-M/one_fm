import frappe

def execute():
	country_list = frappe.get_list("Country", pluck="name")
	job_applicant = frappe.get_list("Job Applicant", filters=[["one_fm_place_of_birth", "!=", ""]],fields=["name", "one_fm_place_of_birth"])
	for j in job_applicant:
		if j.one_fm_place_of_birth not in country_list:
			frappe.db.set_value('Job Applicant', j.name, 'one_fm_place_of_birth', None)
	frappe.db.commit()