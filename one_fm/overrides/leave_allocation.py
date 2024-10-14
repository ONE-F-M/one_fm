import frappe

from hrms.hr.doctype.leave_allocation.leave_allocation import (
    LeaveAllocation
)
from frappe import _,  bold


class LeaveAllocationOverride(LeaveAllocation):
	# overide default class

	def validate(self):
		super().validate()
		self.validate_maternity_leave()
		
	def validate_maternity_leave(self):
		gender = frappe.db.get_value("Employee", self.employee, "gender")
		
		if self.leave_type == "Maternity Leave" and gender == "Male":
			frappe.throw(
				_("Leave Type: {0} cannot be assign to male Employee {1}.").format(
					bold(self.leave_type ),
					bold(self.employee),
				),
				title=_("Wrong Leave Type Assignment"),
			)
