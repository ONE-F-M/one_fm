import frappe
from hrms.hr.doctype.employee_checkin.employee_checkin import EmployeeCheckin
from one_fm.api.v1.roster import get_current_shift

class EmployeeCheckinOverride(EmployeeCheckin):
	#overrode employee checkin method
	@frappe.whitelist()
	def fetch_shift(self):
		pass


	def after_insert(self):
		try:
			# update shift if not exists
			if not self.shift_assignment or not self.operations_shift:
				curr_shift = get_current_shift(self.employee)
				self.db_set('shift_assignment', curr_shift.name)
				self.db_set('operations_shift', curr_shift.shift)
				self.db_set('shift_type', curr_shift.shift_type)
		except Exception as e:
			pass

