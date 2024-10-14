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
		leave_type = frappe.get_doc("Leave Type", self.leave_type)
		employee = frappe.get_doc("Employee", self.employee)
		
		if leave_type.name == "Maternity Leave" and employee.gender == "Male":
			frappe.throw(
				_("Leave Type: {0} cannot be assign to male Employee {1}.").format(
					bold(self.leave_type ),
					bold(self.employee),
				),
				title=_("Wrong Leave Type Assignment"),
			)
