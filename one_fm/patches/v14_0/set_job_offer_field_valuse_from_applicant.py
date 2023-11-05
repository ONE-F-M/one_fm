import frappe

def execute():
	job_offers = frappe.get_list("Job Offer", {'docstatus': ['<', 2]})
	for job_offer in job_offers:
		doc = frappe.get_doc("Job Offer", job_offer.name)
		if doc.one_fm_erf:
			erf = frappe.get_doc("ERF", doc.one_fm_erf, "docstatus")
			if not erf.docstatus==2 and erf.salary_structure:
				if doc.docstatus == 0:
					doc.save(ignore_permissions=True)
				elif doc.docstatus == 1:
					job_applicant = frappe.get_doc('Job Applicant', doc.job_applicant)
					query = """
						Update
							`tabJob Offer`
						set
							agency='{0}', nationality='{1}', department='{2}'
						where
							name='{3}'
					"""
					frappe.db.sql(query.format(job_applicant.one_fm_agency or '', job_applicant.one_fm_nationality or '', job_applicant.department or '', doc.name))
					frappe.db.commit()
