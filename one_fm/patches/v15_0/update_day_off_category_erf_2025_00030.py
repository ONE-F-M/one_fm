import frappe

def execute():
	"""
	Update day_off_category from Weekly to Monthly for ERF-2025-00030 
	and all Job Applicants linked to this ERF using SQL
	"""
	erf_name = "ERF-2025-00030"
	
	# Check if ERF exists
	if not frappe.db.exists("ERF", erf_name):
		return
	
	# Update ERF record day_off_category to Monthly
	frappe.db.sql("""
		UPDATE `tabERF`
		SET day_off_category = %s
		WHERE name = %s AND day_off_category = %s
	""", ("Monthly", erf_name, "Weekly"))
	
	# Update all Job Applicants linked to this ERF
	frappe.db.sql("""
		UPDATE `tabJob Applicant`
		SET day_off_category = %s
		WHERE one_fm_erf = %s AND day_off_category = %s
	""", ("Monthly", erf_name, "Weekly"))
