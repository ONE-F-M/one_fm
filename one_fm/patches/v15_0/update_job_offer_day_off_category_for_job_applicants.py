import frappe

def execute():
	"""
	Update the day_off_category to 'Monthly' for Job Offers linked to specific Job Applicants.
	Uses direct SQL update to skip validation and ORM controls.
	"""
	
	job_applicants = [
		'HR-APP-2026-01813', 'HR-APP-2026-01836', 'HR-APP-2026-01824', 'HR-APP-2026-01826',
		'HR-APP-2026-01827', 'HR-APP-2026-01828', 'HR-APP-2026-01829', 'HR-APP-2026-01830',
		'HR-APP-2026-01823', 'HR-APP-2026-01831', 'HR-APP-2026-01832', 'HR-APP-2026-01833',
		'HR-APP-2026-01834', 'HR-APP-2026-01835', 'HR-APP-2026-01820', 'HR-APP-2026-01837',
		'HR-APP-2026-01822', 'HR-APP-2026-01821', 'HR-APP-2026-01817', 'HR-APP-2026-01816',
		'HR-APP-2026-01814'
	]
	
	# Update day_off_category to 'Monthly' for Job Offers linked to the specified job applicants
	frappe.db.sql("""
		UPDATE `tabJob Offer`
		SET day_off_category = %s
		WHERE job_applicant IN ({})
	""".format(','.join(['%s'] * len(job_applicants))), ['Monthly'] + job_applicants)
	
	frappe.db.commit()
