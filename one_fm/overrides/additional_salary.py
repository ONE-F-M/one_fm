from hrms.payroll.doctype.additional_salary.additional_salary import *



class AdditionalSalaryOverride(AdditionalSalary):

	def validate_dates(self):
		
		joining_relieve_date = frappe.db.get_values(
			"Employee", self.employee, ["date_of_joining", "relieving_date"], as_dict=1
		)
		print(joining_relieve_date)
		if len(joining_relieve_date):
			joining_relieve_date = joining_relieve_date[0]
			date_of_joining, relieving_date = joining_relieve_date.date_of_joining, joining_relieve_date.relieving_date
		else:
			date_of_joining = ''
			relieving_date = ''
			
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From Date can not be greater than To Date."))

		if date_of_joining:
			if self.payroll_date and getdate(self.payroll_date) < getdate(date_of_joining):
				frappe.throw(_("Payroll date can not be less than employee's joining date."))
			elif self.from_date and getdate(self.from_date) < getdate(date_of_joining):
				frappe.throw(_("From date can not be less than employee's joining date."))

		if relieving_date:
			if self.to_date and getdate(self.to_date) > getdate(relieving_date):
				frappe.throw(_("To date can not be greater than employee's relieving date."))
			if self.payroll_date and getdate(self.payroll_date) > getdate(relieving_date):
				frappe.throw(_("Payroll date can not be greater than employee's relieving date."))
