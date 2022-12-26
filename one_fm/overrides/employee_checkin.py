import frappe

from hrms.hr.doctype.employee_checkin.employee_checkin import EmployeeCheckin


class EmployeeCheckinOverride(EmployeeCheckin):

	@frappe.whitelist()
	def fetch_shift(self):
		pass

