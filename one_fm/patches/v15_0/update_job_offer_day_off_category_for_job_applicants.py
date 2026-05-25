import frappe

def execute():
	"""
	Update the day_off_category to 'Monthly' for Job Offers linked to specific Job Applicants.
	Uses Query Builder to update records. Checks if data exists first.
	"""
	
	job_applicants = [
		'HR-APP-2026-01813', 'HR-APP-2026-01836', 'HR-APP-2026-01824', 'HR-APP-2026-01826',
		'HR-APP-2026-01827', 'HR-APP-2026-01828', 'HR-APP-2026-01829', 'HR-APP-2026-01830',
		'HR-APP-2026-01823', 'HR-APP-2026-01831', 'HR-APP-2026-01832', 'HR-APP-2026-01833',
		'HR-APP-2026-01834', 'HR-APP-2026-01835', 'HR-APP-2026-01820', 'HR-APP-2026-01837',
		'HR-APP-2026-01822', 'HR-APP-2026-01821', 'HR-APP-2026-01817', 'HR-APP-2026-01816',
		'HR-APP-2026-01814'
	]
	
	# Check if Job Offers exist for the specified job applicants
	JobOffer = frappe.qb.DocType("Job Offer")
	job_offers = (
		frappe.qb.from_(JobOffer)
		.select(JobOffer.name)
		.where(JobOffer.job_applicant.isin(job_applicants))
		.limit(1)
	).run()

	if not job_offers:
		return

	# Update day_off_category to 'Monthly' for all matching Job Offers
	(
		frappe.qb.update(JobOffer)
		.set(JobOffer.day_off_category, "Monthly")
		.where(JobOffer.job_applicant.isin(job_applicants))
	).run()
	
	frappe.db.commit()
