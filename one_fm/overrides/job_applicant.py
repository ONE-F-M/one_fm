import frappe
from hrms.hr.doctype.job_applicant.job_applicant import *

class JobApplicantOverride(JobApplicant):

	def autoname(self):
		pass
